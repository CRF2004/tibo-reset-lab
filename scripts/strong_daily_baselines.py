#!/usr/bin/env python3
"""Compare M2 with stronger adaptive and nonparametric daily baselines."""

from __future__ import annotations

import csv
import math
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
PERIODS = ROOT / "data/processed/person_period_daily.csv"
COMMON = ROOT / "data/processed/rolling_baseline_forecasts.csv"
OUTPUT = ROOT / "data/processed/strong_daily_baseline_forecasts.csv"
REPORT = ROOT / "reports/strong_baselines_v1.md"
PT = ZoneInfo("America/Los_Angeles")
BOUNDARY = datetime(2026, 6, 11, tzinfo=PT)


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def beta_rate(rows: list[dict[str, str]]) -> float:
    return (sum(int(row["announcement_in_next_window"]) for row in rows) + 1) / (len(rows) + 2)


def m2_no_regime(row: dict[str, str]) -> list[float]:
    local = dt(row["window_start_utc"]).astimezone(PT)
    weekday, month = local.weekday(), local.month
    return [
        math.log1p(float(row["days_since_last_announcement"])),
        math.sin(2 * math.pi * weekday / 7),
        math.cos(2 * math.pi * weekday / 7),
        float(weekday >= 5),
        math.sin(2 * math.pi * month / 12),
        math.cos(2 * math.pi * month / 12),
    ]


def fit_no_regime(training: list[dict[str, str]], current: dict[str, str]) -> float:
    x = np.array([m2_no_regime(row) for row in training])
    y = np.array([int(row["announcement_in_next_window"]) for row in training])
    transform = ColumnTransformer([
        ("scale_continuous", StandardScaler(), [0, 1, 2, 4, 5]),
        ("pass_binary", "passthrough", [3]),
    ])
    model = make_pipeline(
        transform, LogisticRegression(C=0.25, solver="lbfgs", max_iter=1000)
    )
    model.fit(x, y)
    return float(model.predict_proba(np.array([m2_no_regime(current)]))[0, 1])


def scores(rows: list[dict[str, str]], field: str) -> tuple[float, float, float, float, float]:
    y = np.array([int(row["label_24h"]) for row in rows])
    p = np.array([float(row[field]) for row in rows])
    clipped = np.clip(p, 1e-8, 1 - 1e-8)
    brier = float(np.mean((p - y) ** 2))
    logloss = float(np.mean(-(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))))
    ap = float(average_precision_score(y, p))
    logits = np.log(clipped / (1 - clipped)).reshape(-1, 1)
    calibration = LogisticRegression(C=1e6, solver="lbfgs").fit(logits, y)
    return brier, logloss, ap, float(calibration.intercept_[0]), float(calibration.coef_[0, 0])


def main() -> int:
    with PERIODS.open(encoding="utf-8", newline="") as handle:
        periods = list(csv.DictReader(handle))
    with COMMON.open(encoding="utf-8", newline="") as handle:
        common = {row["issued_at_utc"]: row for row in csv.DictReader(handle)}
    output = []
    for index, current in enumerate(periods):
        key = current["window_start_utc"]
        if key not in common:
            continue
        training = [row for row in periods[:index] if row["days_since_last_announcement"]]
        gap = float(current["days_since_last_announcement"])
        local = dt(key).astimezone(PT)
        same_regime = [
            row for row in training
            if (dt(row["window_start_utc"]).astimezone(PT) >= BOUNDARY) == (local >= BOUNDARY)
        ]
        same_bin = [
            row for row in training
            if math.floor(float(row["days_since_last_announcement"])) == math.floor(gap)
        ]
        nearest = sorted(
            training,
            key=lambda row: abs(float(row["days_since_last_announcement"]) - gap),
        )[:30]
        weights = np.array([
            math.exp(-math.log(2) * (index - periods.index(row)) / 30) for row in training
        ])
        labels = np.array([int(row["announcement_in_next_window"]) for row in training])
        ewma30 = float((np.dot(weights, labels) + 1) / (np.sum(weights) + 2))
        result = {
            "issued_at_utc": key,
            "label_24h": common[key]["label_24h"],
            "event_base_rate": f"{np.mean(labels):.8f}",
            "p_global": common[key]["p_m0"],
            "p_rolling30": f"{beta_rate(training[-30:]):.8f}",
            "p_rolling60": f"{beta_rate(training[-60:]):.8f}",
            "p_ewma_hl30": f"{ewma30:.8f}",
            "p_regime_rate": f"{beta_rate(same_regime):.8f}",
            "p_km_renewal": f"{beta_rate(same_bin):.8f}",
            "p_same_gap30": f"{beta_rate(nearest):.8f}",
            "p_m2_no_regime": f"{fit_no_regime(training, current):.8f}",
            "p_m2": common[key]["p_m2"],
        }
        output.append(result)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    fields = [
        "p_global", "p_rolling30", "p_rolling60", "p_ewma_hl30",
        "p_regime_rate", "p_km_renewal", "p_same_gap30", "p_m2_no_regime", "p_m2",
    ]
    labels = {
        "p_global": "Global Beta rate", "p_rolling30": "Rolling 30d rate",
        "p_rolling60": "Rolling 60d rate", "p_ewma_hl30": "EWMA half-life 30d",
        "p_regime_rate": "Two-regime rate", "p_km_renewal": "Discrete KM/renewal hazard",
        "p_same_gap30": "30 nearest same-gap analogue", "p_m2_no_regime": "M2 without regime",
        "p_m2": "M2",
    }
    values = {field: scores(output, field) for field in fields}
    best = min(fields, key=lambda field: values[field][0])
    table = "\n".join(
        f"| {labels[field]} | {values[field][0]:.6f} | {values[field][1]:.6f} | "
        f"{values[field][2]:.6f} | {values[field][3]:.3f} | {values[field][4]:.3f} | "
        f"{1-values[field][0]/values['p_global'][0]:.3%} |"
        for field in fields
    )
    prevalence = sum(int(row["label_24h"]) for row in output) / len(output)
    REPORT.write_text(
        f"""# 强日级基线比较 v1

共同窗口：{len(output)} 点；正例率：{prevalence:.3%}。所有自适应基线只使用预测点
之前的数据。两阶段边界固定为 2026-06-11（banked reset 首次公开产品证据），但该
边界是在历史数据分析阶段确定，因此历史结果仍是模型开发证据。

| 模型 | Brier | Log Loss | PR-AUC | 校准截距 | 校准斜率 | Skill vs global |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
{table}

最低 Brier：**{labels[best]}**。`Discrete KM/renewal hazard` 用既往达到相同
整数 gap 的风险集估计离散 hazard，并做 Beta(1,1) 平滑；`same-gap` 使用 gap
距离最近的 30 个既往风险集观测。绝对 Brier 必须与 {prevalence:.3%} 的事件比例、
skill、校准和 PR-AUC 一起解释。
""",
        encoding="utf-8",
    )
    print(f"Strong baselines: best={labels[best]}, Brier={values[best][0]:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
