#!/usr/bin/env python3
"""Replace only the generated live snapshot block in README.md."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
DATA = ROOT / "data/processed"
START = "<!-- LIVE_SNAPSHOT_START -->"
END = "<!-- LIVE_SNAPSHOT_END -->"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pct(value: str | None) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def main() -> int:
    predictors = {row["predictor_id"]: row for row in read("tournament_predictors.csv")}
    forecasts = [
        row for row in read("tournament_forecasts.csv")
        if row["eligibility_status"] == "eligible"
    ]
    announcements = [
        row for row in read("reset_announcements.csv")
        if row["adjudication_status"] == "accepted"
    ]
    scores = read("tournament_scores.csv")
    scheduled = [row for row in forecasts if row["schedule_class"] == "scheduled"]
    if scheduled:
        issue = max(row["issued_at_utc"] for row in scheduled)
        selected = [row for row in scheduled if row["issued_at_utc"] == issue]
        mode = "正式 scheduled 轮次"
        warning = ""
    else:
        latest: dict[tuple[str, str], dict[str, str]] = {}
        for row in forecasts:
            key = (row["predictor_id"], row["horizon_hours"])
            if key not in latest or row["issued_at_utc"] > latest[key]["issued_at_utc"]:
                latest[key] = row
        selected = list(latest.values())
        issue = max((row["issued_at_utc"] for row in selected), default="")
        mode = "Bootstrap 演示"
        warning = (
            "> **注意：** 尚无正式 scheduled 轮次。下表来自不同时间的 bootstrap，"
            "只展示系统如何工作，不能用于比较高低，也不进入排行榜。\n"
        )
    by_predictor: dict[str, dict[str, dict[str, str]]] = {}
    for row in selected:
        by_predictor.setdefault(row["predictor_id"], {})[row["horizon_hours"]] = row
    display_order = [
        "P_GLOBAL", "P_RECENT30", "P_RENEWAL", "P_CALENDAR", "P_THEORY",
        "P_LLM_DEEPSEEK_V4", "P_LLM_QWEN35_397B", "P_LLM_KIMI_K25",
        "P_LLM_MINIMAX_M27", "P_LLM_STEP35", "P_PLAYER", "P_CROWD",
    ]
    table_rows = []
    for predictor_id in display_order:
        horizons = by_predictor.get(predictor_id)
        if not horizons:
            continue
        cutoff = max(row["evidence_cutoff_utc"] for row in horizons.values())
        table_rows.append(
            f"| {predictors[predictor_id]['display_name']} | "
            f"{pct(horizons.get('24', {}).get('probability'))} | "
            f"{pct(horizons.get('168', {}).get('probability'))} | {cutoff} |"
        )
    latest_ann = max(announcements, key=lambda row: row["announced_at_utc"])
    post_id = latest_ann["announcement_id"].removeprefix("ANN_X_")
    latest_url = f"https://x.com/thsottiaux/status/{post_id}"
    latest_at = dt(latest_ann["announced_at_utc"])
    data_at = max(
        (row["submitted_at_utc"] for row in selected),
        default=datetime.now(timezone.utc).isoformat(),
    )
    mature_scheduled = {
        row["tournament_forecast_id"] for row in scores
        if any(
            forecast["tournament_forecast_id"] == row["tournament_forecast_id"]
            and forecast["schedule_class"] == "scheduled"
            for forecast in forecasts
        )
    }
    block = f"""{START}
## 当前预测快照

**状态：{mode}** · 数据更新至 `{data_at}` · 正式成熟预测 `{len(mature_scheduled)}` 条

{warning}
| 预测者 | 未来24小时 | 未来7天 | 证据截止（UTC） |
| --- | ---: | ---: | --- |
{chr(10).join(table_rows) if table_rows else "| 暂无有效预测 | — | — | — |"}

### 当前已知事实

- 最近一次合格公告：[原始 X 帖]({latest_url})，时间 `{latest_ann['announced_at_utc']}`；
- 类型：`{latest_ann['reset_type']}`；原因：`{latest_ann['reason_type']}`；
- 距该公告约 `{max(0, (dt(data_at) - latest_at).total_seconds() / 3600):.1f}` 小时；
- [查看中文理由、证据与完整 Dashboard](reports/community_dashboard.md)。

概率不是官方消息，也不是“重置倒计时”。Bootstrap、迟交和未成熟结果不进入正式排名。
{END}"""
    text = README.read_text(encoding="utf-8")
    if START not in text or END not in text:
        raise SystemExit("README live snapshot markers are missing")
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    README.write_text(before + block + after, encoding="utf-8")
    print(f"Updated README snapshot from {len(selected)} forecasts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
