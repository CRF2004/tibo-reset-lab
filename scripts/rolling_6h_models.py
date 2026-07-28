#!/usr/bin/env python3
"""Task 6: common-window 6-hour rolling baselines and context-lag ablations."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/person_period_6h.csv"
OUTPUT = ROOT / "data/processed/rolling_6h_forecasts.csv"
REPORT = ROOT / "reports/model_comparison_6h_v1.md"
PT = ZoneInfo("America/Los_Angeles")


@dataclass(frozen=True)
class Spec:
    continuous: tuple[int, ...]
    binary: tuple[int, ...]


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def base_gap(row: dict[str, str]) -> float:
    return math.log1p(float(row["hours_since_last_announcement"]) / 24)


def context_values(row: dict[str, str]) -> dict[str, float]:
    visible = float(row["official_context_visible"])
    age = float(row["hours_since_latest_context"]) if row["hours_since_latest_context"] else 72.0
    return {
        "visible": visible,
        "active": float(row["official_incident_active"]),
        "resolved": float(row["official_incident_resolved_48h"]),
        "strength": float(row["max_event_strength_72h"]),
        "attention": float(row["max_attention_state_72h"]),
        "age": age / 72,
        "age_0_6": float(visible and age <= 6),
        "age_6_24": float(visible and 6 < age <= 24),
        "age_24_48": float(visible and 24 < age <= 48),
        "age_48_72": float(visible and 48 < age <= 72),
    }


def feature(row: dict[str, str], model: str) -> tuple[list[float], Spec]:
    gap = base_gap(row)
    if model == "m1":
        return [gap], Spec((0,), ())
    if model == "m2":
        local = dt(row["window_start_utc"]).astimezone(PT)
        weekday, hour, month = local.weekday(), local.hour, local.month
        values = [
            gap,
            math.sin(2 * math.pi * hour / 24),
            math.cos(2 * math.pi * hour / 24),
            math.sin(2 * math.pi * weekday / 7),
            math.cos(2 * math.pi * weekday / 7),
            float(weekday >= 5),
            math.sin(2 * math.pi * month / 12),
            math.cos(2 * math.pi * month / 12),
            float(local >= datetime(2026, 6, 11, tzinfo=PT)),
        ]
        return values, Spec((0, 1, 2, 3, 4, 6, 7), (5, 8))

    c = context_values(row)
    groups = {
        "m3": ["visible", "active", "resolved", "strength", "attention", "age"],
        "m3_no_stage": ["visible", "strength", "attention", "age"],
        "m3_no_strength": ["visible", "active", "resolved", "attention", "age"],
        "m3_no_attention": ["visible", "active", "resolved", "strength", "age"],
        "m3_no_age": ["visible", "active", "resolved", "strength", "attention"],
        "m3_lag_bins": [
            "active", "strength", "attention",
            "age_0_6", "age_6_24", "age_24_48", "age_48_72",
        ],
    }
    names = groups[model]
    values = [gap] + [c[name] for name in names]
    continuous_names = {"strength", "attention", "age"}
    continuous = [0] + [
        index + 1 for index, name in enumerate(names) if name in continuous_names
    ]
    binary = [
        index + 1 for index, name in enumerate(names) if name not in continuous_names
    ]
    return values, Spec(tuple(continuous), tuple(binary))


def estimator(spec: Spec):
    operations = [("scale_continuous", StandardScaler(), list(spec.continuous))]
    if spec.binary:
        operations.append(("pass_binary", "passthrough", list(spec.binary)))
    return make_pipeline(
        ColumnTransformer(operations, remainder="drop"),
        LogisticRegression(C=0.25, solver="lbfgs", max_iter=1000),
    )


def metrics(rows: list[dict[str, str]], model: str) -> tuple[float, float, float, float]:
    y = np.array([int(row["label_6h"]) for row in rows])
    p = np.array([float(row[f"p_{model}"]) for row in rows])
    clipped = np.clip(p, 1e-15, 1 - 1e-15)
    brier = float(np.mean((p - y) ** 2))
    logloss = float(np.mean(-(y * np.log(clipped) + (1 - y) * np.log(1 - clipped))))
    return brier, logloss, float(average_precision_score(y, p)), float(np.mean(p))


def block_ci(
    rows: list[dict[str, str]], challenger: str, baseline: str, seed: int = 20260728
) -> tuple[float, float]:
    """Percentile CI for paired Brier difference, resampling contiguous 7-day blocks."""
    rng = np.random.default_rng(seed)
    blocks = [rows[start:start + 28] for start in range(0, len(rows), 28)]
    differences = []
    for _ in range(2000):
        sampled = [
            row for index in rng.integers(0, len(blocks), size=len(blocks))
            for row in blocks[index]
        ]
        diff = np.mean([
            (float(row[f"p_{challenger}"]) - int(row["label_6h"])) ** 2
            - (float(row[f"p_{baseline}"]) - int(row["label_6h"])) ** 2
            for row in sampled
        ])
        differences.append(float(diff))
    return tuple(np.quantile(differences, [0.025, 0.975]))  # type: ignore[return-value]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-cutoff",
        help="Only score windows ending by this UTC timestamp; defaults to current UTC.",
    )
    args = parser.parse_args()
    cutoff = dt(args.data_cutoff) if args.data_cutoff else datetime.now(timezone.utc)
    with INPUT.open(encoding="utf-8", newline="") as handle:
        periods = [
            row for row in csv.DictReader(handle)
            if dt(row["window_end_utc"]) <= cutoff
        ]
    models = [
        "m1", "m2", "m3", "m3_no_stage", "m3_no_strength",
        "m3_no_attention", "m3_no_age", "m3_lag_bins",
    ]
    output = []
    for index, current in enumerate(periods):
        if not current["hours_since_last_announcement"]:
            continue
        training = [
            row for row in periods[:index] if row["hours_since_last_announcement"]
        ]
        y = np.array([int(row["announcement_in_next_window"]) for row in training])
        # 30 days of prior 6h periods and at least two positives in each rolling fit.
        if len(training) < 120 or min(np.sum(y == 0), np.sum(y == 1)) < 2:
            continue
        result = {
            "issued_at_utc": current["window_start_utc"],
            "label_6h": current["announcement_in_next_window"],
            "training_rows": len(training),
            "p_m0": f"{(int(np.sum(y)) + 1) / (len(y) + 2):.8f}",
        }
        for model in models:
            train_features = [feature(row, model) for row in training]
            x = np.array([item[0] for item in train_features])
            x_now_values, spec = feature(current, model)
            fit = estimator(spec)
            fit.fit(x, y)
            result[f"p_{model}"] = f"{fit.predict_proba(np.array([x_now_values]))[0, 1]:.8f}"
        output.append(result)

    with OUTPUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    all_models = ["m0"] + models
    scores = {model: metrics(output, model) for model in all_models}
    main_rows = []
    labels = {
        "m0": "历史 6h 事件率",
        "m1": "log1p 距上次公告时间",
        "m2": "M1 + PT 小时/星期/月/制度",
        "m3": "M1 + 官方事故状态/强度/注意力/年龄",
    }
    for model in ("m0", "m1", "m2", "m3"):
        brier, logloss, ap, mean_p = scores[model]
        skill = 0 if model == "m0" else 1 - brier / scores["m0"][0]
        main_rows.append(
            f"| {model.upper()} | {labels[model]} | {brier:.6f} | {logloss:.6f} | "
            f"{ap:.6f} | {mean_p:.3%} | {skill:.3%} |"
        )
    ablation_rows = []
    for model in ("m3", "m3_no_stage", "m3_no_strength", "m3_no_attention", "m3_no_age", "m3_lag_bins"):
        brier, logloss, ap, _ = scores[model]
        ablation_rows.append(
            f"| {model} | {brier:.6f} | {logloss:.6f} | {ap:.6f} | "
            f"{1 - brier / scores['m1'][0]:.3%} |"
        )
    ci_m2 = block_ci(output, "m2", "m0")
    ci_m3_m1 = block_ci(output, "m3", "m1")
    ci_m3_m2 = block_ci(output, "m3", "m2")
    best = min(("m0", "m1", "m2", "m3"), key=lambda name: scores[name][0])
    best_ablation = min(
        ("m3", "m3_no_stage", "m3_no_strength", "m3_no_attention", "m3_no_age", "m3_lag_bins"),
        key=lambda name: scores[name][0],
    )
    REPORT.write_text(
        f"""# 任务 6：6 小时 M0–M3-lite 滚动比较与滞后消融

数据截止：{cutoff.isoformat().replace('+00:00', 'Z')}  
共同评分窗口：{output[0]['issued_at_utc']} 至 {output[-1]['issued_at_utc']}  
共同预测点：{len(output)}；正例：{sum(int(row['label_6h']) for row in output)}。  
训练：expanding window；最少 120 个既往有效时间片且正负类各至少 2 例。

## 原始比较表

| 模型 | 特征 | Brier | Log Loss | PR-AUC | 平均概率 | Brier Skill vs M0 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(main_rows)}

按 Brier 排名，主模型中最佳为 **{best.upper()}**。周区块 paired bootstrap 的
Brier 差值 95% 区间（负值代表前者更好）：

- M2 − M0：[{ci_m2[0]:.6f}, {ci_m2[1]:.6f}]
- M3-lite − M1：[{ci_m3_m1[0]:.6f}, {ci_m3_m1[1]:.6f}]
- M3-lite − M2：[{ci_m3_m2[0]:.6f}, {ci_m3_m2[1]:.6f}]

## 滞后与变量组消融

| 版本 | Brier | Log Loss | PR-AUC | Brier Skill vs M1 |
| --- | ---: | ---: | ---: | ---: |
{chr(10).join(ablation_rows)}

`m3_lag_bins` 将最新官方事故年龄拆为 0–6、6–24、24–48、48–72 小时；其他
`no_*` 版本每次删除一个预先定义的变量组。消融中最佳为 **{best_ablation}**。

## 结论结构

1. **观察**：以上表格给出共同窗口的原始得分与相对改善。
2. **解释**：6 小时粒度减少了“事故与公告落在同一天但先后顺序不明”的混合，
   但正例仍稀少，复杂事故特征容易受冷启动和个别周期影响。
3. **含义**：只有 Brier 与 Log Loss 同向改善、且 paired block 区间支持时，才应
   把事故特征视作稳定增量；PR-AUC 只作罕见事件排序的辅助指标。
4. **下一步**：保持当前最佳简单模型作为前瞻基线；滞后分箱结果属于历史探索，
   不应反向修改已经锁定的实时 M2，需在后续锁定预测中验证。

固定设置：L2 logistic，`C=0.25`；连续变量仅在各训练窗内标准化，二元变量直通。
bootstrap 使用连续 7 日（28 个时间片）区块、2000 次固定种子重采样。
""",
        encoding="utf-8",
    )
    print(f"Wrote {len(output)} common 6-hour predictions")
    print(f"Best main model: {best}, Brier={scores[best][0]:.6f}")
    print(f"Best context ablation: {best_ablation}, Brier={scores[best_ablation][0]:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
