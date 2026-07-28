#!/usr/bin/env python3
"""Build conservative Markdown and HTML views of the community tournament."""

from __future__ import annotations

import csv
import html
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
REPORT = ROOT / "reports/community_dashboard.md"
HTML = ROOT / "dashboard/community.html"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def table(headers: list[str], rows: list[list[object]]) -> str:
    if not rows:
        return "_暂无可报告记录。_"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join(["---"] * len(headers)) + "|"]
    out += ["| " + " | ".join(str(value) for value in row) + " |" for row in rows]
    return "\n".join(out)


def main() -> int:
    predictors = {row["predictor_id"]: row for row in read("tournament_predictors.csv")}
    forecasts = read("tournament_forecasts.csv")
    scores = read("tournament_scores.csv")
    score_by_id = {row["tournament_forecast_id"]: row for row in scores}
    eligible = [
        row for row in forecasts
        if row["schedule_class"] == "scheduled"
        and row["eligibility_status"] == "eligible"
        and row["tournament_forecast_id"] in score_by_id
    ]
    grouped: dict[tuple[str, str], list[tuple[float, float]]] = defaultdict(list)
    for forecast in eligible:
        score = score_by_id[forecast["tournament_forecast_id"]]
        grouped[(forecast["predictor_id"], forecast["horizon_hours"])].append(
            (float(score["brier"]), float(score["log_loss"]))
        )
    leaderboard = []
    for (predictor_id, horizon), values in grouped.items():
        leaderboard.append([
            predictors[predictor_id]["display_name"], horizon, len(values),
            f"{sum(v[0] for v in values) / len(values):.4f}",
            f"{sum(v[1] for v in values) / len(values):.4f}",
        ])
    leaderboard.sort(key=lambda row: (int(row[1]), float(row[3])))
    latest_by_predictor_horizon: dict[tuple[str, str], dict[str, str]] = {}
    for row in forecasts:
        key = (row["predictor_id"], row["horizon_hours"])
        if (
            key not in latest_by_predictor_horizon
            or row["issued_at_utc"] > latest_by_predictor_horizon[key]["issued_at_utc"]
        ):
            latest_by_predictor_horizon[key] = row
    latest = sorted(
        latest_by_predictor_horizon.values(),
        key=lambda row: (row["predictor_id"], int(row["horizon_hours"])),
    )
    latest_rows = [[
        predictors[row["predictor_id"]]["display_name"],
        row["horizon_hours"], f"{float(row['probability']):.1%}",
        row["schedule_class"], row["evidence_ids"][:48],
    ] for row in latest]
    predictor_rows = [[
        row["display_name"], row["predictor_class"], row["description"]
    ] for row in predictors.values()]
    scheduled_rounds = {row["round_id"] for row in eligible}
    positives = {
        score_by_id[row["tournament_forecast_id"]]["label"]
        for row in eligible if row["predictor_id"] == "P_RECENT30" and row["horizon_hours"] == "24"
    }
    notice = (
        "正式停止条件尚未满足：至少 180 个有效日级轮次且至少 20 个前瞻阳性。"
        "以下结果仅用于运行审计和描述，不宣称任何预测者优胜。"
    )
    md = f"""# 社区预测 Dashboard

生成时间：{datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")}

> {notice}

## 最新冻结概率

{table(["预测者", "窗口(h)", "概率", "轮次类型", "证据/来源"], latest_rows)}

## 正式前瞻表现

有效成熟轮次：{len(scheduled_rounds)}。24 小时阳性状态将在各轮次成熟后累计。

{table(["预测者", "窗口(h)", "N", "Brier", "Log Loss"], leaderboard)}

## 比较对象

{table(["预测者", "类别", "作用"], predictor_rows)}

## 解释边界

- 排名只使用按时冻结、已成熟的 scheduled 轮次；bootstrap 不进入正式比较。
- 玩家缺报保持缺失，不进行事后回填；Crowd 至少需要三名有效独立玩家。
- 同时报告 Brier、Log Loss、覆盖率和相对近期 30 天基线的 skill；样本不足时不作胜负推断。
- Audit 层独立核查公告是否实际应用，以及 hard/banked 行为是否与公告一致。
"""
    REPORT.write_text(md, encoding="utf-8")
    HTML.parent.mkdir(parents=True, exist_ok=True)
    body = html.escape(md)
    HTML.write_text(
        "<!doctype html><html lang='zh-CN'><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        "<title>社区预测 Dashboard</title><style>"
        "body{max-width:1100px;margin:40px auto;padding:0 20px;font:16px/1.6 system-ui;color:#172033}"
        "pre{white-space:pre-wrap;background:#f5f7fb;padding:24px;border-radius:12px}"
        "</style><body><pre>" + body + "</pre></body></html>\n",
        encoding="utf-8",
    )
    print(f"Built {REPORT.relative_to(ROOT)} and {HTML.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
