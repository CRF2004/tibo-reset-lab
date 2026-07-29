#!/usr/bin/env python3
"""Expanding-window M1, M2, and prediction-safe M3-lite baselines."""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/person_period_daily.csv"
CONTEXT_INPUT = ROOT / "data/processed/daily_context_features.csv"
M0_INPUT = ROOT / "data/processed/m0_forecasts.csv"
OUTPUT = ROOT / "data/processed/rolling_baseline_forecasts.csv"
REPORT = ROOT / "reports/model_comparison_v1.md"
PT = ZoneInfo("America/Los_Angeles")


def parse(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def features(
    row: dict[str, str],
    model: str,
    context: dict[str, str] | None = None,
) -> list[float]:
    days = float(row["days_since_last_announcement"])
    values = [math.log1p(days)]
    if model == "M2":
        local = parse(row["window_start_utc"]).astimezone(PT)
        weekday = local.weekday()
        month = local.month
        values.extend([
            math.sin(2 * math.pi * weekday / 7),
            math.cos(2 * math.pi * weekday / 7),
            float(weekday >= 5),
            math.sin(2 * math.pi * month / 12),
            math.cos(2 * math.pi * month / 12),
            float(local >= datetime(2026, 6, 11, tzinfo=PT)),
        ])
    elif model == "M3":
        if context is None:
            raise ValueError("M3 requires prediction-safe context")
        age = (
            float(context["hours_since_latest_context"])
            if context["hours_since_latest_context"]
            else 72.0
        )
        values.extend([
            float(context["official_context_visible"]),
            float(context["official_incident_active"]),
            float(context["official_incident_resolved_48h"]),
            float(context["max_event_strength_72h"]),
            float(context["max_attention_state_72h"]),
            age / 72.0,
        ])
    return values


def loss(rows: list[dict[str, str]], probability_field: str) -> tuple[float, float]:
    values = []
    logs = []
    for row in rows:
        p = min(max(float(row[probability_field]), 1e-15), 1 - 1e-15)
        y = int(row["label_24h"])
        values.append((p - y) ** 2)
        logs.append(-(y * math.log(p) + (1 - y) * math.log(1 - p)))
    return float(np.mean(values)), float(np.mean(logs))


def transformer(model_name: str) -> ColumnTransformer:
    # Only continuous/cyclic variables are standardized. Binary indicators pass
    # through unchanged, matching the preregistered preprocessing rule.
    if model_name == "M1":
        continuous, binary = [0], []
    elif model_name == "M2":
        continuous, binary = [0, 1, 2, 4, 5], [3, 6]
    else:  # M3: log-gap, strength, attention, age are continuous/ordinal.
        continuous, binary = [0, 4, 5, 6], [1, 2, 3]
    operations = [("scale_continuous", StandardScaler(), continuous)]
    if binary:
        operations.append(("pass_binary", "passthrough", binary))
    return ColumnTransformer(operations, remainder="drop")


def main() -> int:
    with INPUT.open(encoding="utf-8", newline="") as handle:
        periods = list(csv.DictReader(handle))
    with M0_INPUT.open(encoding="utf-8", newline="") as handle:
        m0 = {row["issued_at_utc"]: row for row in csv.DictReader(handle)}
    with CONTEXT_INPUT.open(encoding="utf-8", newline="") as handle:
        contexts = {
            row["window_start_utc"]: row for row in csv.DictReader(handle)
        }

    output = []
    for index, current in enumerate(periods):
        # A renewal feature is undefined until the first observed announcement.
        if not current["days_since_last_announcement"]:
            continue
        training = [
            row for row in periods[:index]
            if row["days_since_last_announcement"]
        ]
        y = np.array([int(row["announcement_in_next_window"]) for row in training])
        # Fixed start rule: at least 30 prior valid periods and two examples per class.
        if len(training) < 30 or min(np.sum(y == 0), np.sum(y == 1)) < 2:
            continue

        result = {
            "issued_at_utc": current["window_start_utc"],
            "label_24h": current["announcement_in_next_window"],
            "p_m0": m0[current["window_start_utc"]]["p_24h"],
            "training_rows": len(training),
        }
        for model_name in ("M1", "M2", "M3"):
            x = np.array([
                features(
                    row,
                    model_name,
                    contexts[row["window_start_utc"]] if model_name == "M3" else None,
                )
                for row in training
            ])
            x_now = np.array([
                features(
                    current,
                    model_name,
                    contexts[current["window_start_utc"]]
                    if model_name == "M3" else None,
                )
            ])
            # Hyperparameters are fixed before comparison; scaling is fit only in-window.
            estimator = make_pipeline(
                transformer(model_name),
                LogisticRegression(C=0.25, solver="lbfgs", max_iter=1000),
            )
            estimator.fit(x, y)
            result[f"p_{model_name.lower()}"] = (
                f"{estimator.predict_proba(x_now)[0, 1]:.8f}"
            )
        output.append(result)

    fields = list(output[0])
    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(output)

    scores = {}
    for name in ("m0", "m1", "m2", "m3"):
        scores[name] = loss(output, f"p_{name}")
    skill_m1 = 1 - scores["m1"][0] / scores["m0"][0]
    skill_m2 = 1 - scores["m2"][0] / scores["m0"][0]
    skill_m3 = 1 - scores["m3"][0] / scores["m0"][0]
    skill_m3_vs_m1 = 1 - scores["m3"][0] / scores["m1"][0]
    REPORT.write_text(
        f"""# M0–M3-lite 严格滚动比较 v1.2

共同评分窗口：{output[0]['issued_at_utc']} 至 {output[-1]['issued_at_utc']}  
共同预测点：{len(output)}  
训练方式：expanding window；每个预测点只使用此前数据。

| 模型 | 特征 | Brier | Log Loss | Brier Skill vs M0 |
| --- | --- | ---: | ---: | ---: |
| M0 | 历史日事件率 | {scores['m0'][0]:.6f} | {scores['m0'][1]:.6f} | 0 |
| M1 | `log1p(days_since_last)` | {scores['m1'][0]:.6f} | {scores['m1'][1]:.6f} | {skill_m1:.3%} |
| M2 | M1 + PT 星期/周末/月周期/制度 | {scores['m2'][0]:.6f} | {scores['m2'][1]:.6f} | {skill_m2:.3%} |
| M3-lite | M1 + 预测安全官方事故特征 | {scores['m3'][0]:.6f} | {scores['m3'][1]:.6f} | {skill_m3:.3%} |

固定设置：L2 logistic regression，`C=0.25`；连续特征只在各训练窗内标准化。
本结果是基线比较，不进行超参数搜索，也不构成因果证据。

M3-lite 相对 M1 的 Brier Skill Score：{skill_m3_vs_m1:.3%}。

M3-lite 只使用预测时点前可见的官方事故变量：72h 内是否存在官方情境、事故是否仍
在进行、是否在 48h 内解决、事件强度、组织注意力和情境年龄。不使用公告文本、
事后原因、里程碑或发布标签。
""",
        encoding="utf-8",
    )
    print(f"Wrote {len(output)} common rolling predictions")
    print(f"M0 Brier={scores['m0'][0]:.6f}")
    print(f"M1 Brier={scores['m1'][0]:.6f}, skill={skill_m1:.3%}")
    print(f"M2 Brier={scores['m2'][0]:.6f}, skill={skill_m2:.3%}")
    print(
        f"M3-lite Brier={scores['m3'][0]:.6f}, "
        f"skill_vs_M0={skill_m3:.3%}, skill_vs_M1={skill_m3_vs_m1:.3%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
