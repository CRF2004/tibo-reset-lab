#!/usr/bin/env python3
"""Build a readable static public dashboard for GitHub Pages."""

from __future__ import annotations

import csv
import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
OUT = ROOT / "dashboard"


def read(name: str) -> list[dict[str, str]]:
    with (DATA / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def dt(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def pct(value: str | float | None) -> str:
    if value is None or value == "":
        return "—"
    return f"{float(value):.1%}"


def signed_pct(value: float) -> str:
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1%}"


def short_day(value: str) -> str:
    parsed = dt(value)
    return parsed.strftime("%m/%d")


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def score_probability_rows(rows: list[dict[str, str]]) -> tuple[int, float, float, float]:
    scored = [
        (int(row["label"]), min(max(float(row["probability"]), 1e-15), 1 - 1e-15))
        for row in rows
    ]
    n = len(scored)
    brier = sum((p - y) ** 2 for y, p in scored) / n
    log_loss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for y, p in scored) / n
    return n, brier, log_loss, sum(y for y, _ in scored) / n


def score_rows(rows: list[dict[str, str]], field: str) -> tuple[int, float, float, float]:
    scored = [
        (int(row["label_24h"]), min(max(float(row[field]), 1e-15), 1 - 1e-15))
        for row in rows
    ]
    n = len(scored)
    brier = sum((p - y) ** 2 for y, p in scored) / n
    log_loss = -sum(y * math.log(p) + (1 - y) * math.log(1 - p) for y, p in scored) / n
    return n, brier, log_loss, sum(y for y, _ in scored) / n


def main() -> int:
    predictors = {row["predictor_id"]: row for row in read("tournament_predictors.csv")}
    forecasts = [row for row in read("tournament_forecasts.csv") if row["eligibility_status"] == "eligible"]
    scores = read("tournament_scores.csv")
    announcements = [row for row in read("reset_announcements.csv") if row["adjudication_status"] == "accepted"]
    confirmations = read("reset_confirmations.csv")
    contexts = [row for row in read("context_events.csv") if row["prediction_eligible"] == "1"]
    actions = read("reset_actions.csv")
    historical = read("strong_daily_baseline_forecasts.csv")
    replay = read("historical_replay_forecasts.csv")

    latest_by_key: dict[tuple[str, str], dict[str, str]] = {}
    for row in forecasts:
        key = (row["predictor_id"], row["horizon_hours"])
        if key not in latest_by_key or row["issued_at_utc"] > latest_by_key[key]["issued_at_utc"]:
            latest_by_key[key] = row
    order = [
        "P_GLOBAL", "P_RECENT30", "P_RENEWAL", "P_CALENDAR", "P_THEORY",
        "P_LLM_DEEPSEEK_V4", "P_LLM_QWEN35_397B", "P_LLM_KIMI_K25",
        "P_LLM_MINIMAX_M27", "P_LLM_STEP35",
    ]
    rows = []
    for predictor_id in order:
        p24 = latest_by_key.get((predictor_id, "24"))
        p168 = latest_by_key.get((predictor_id, "168"))
        if not p24 and not p168:
            continue
        cutoff = max(row["evidence_cutoff_utc"] for row in (p24, p168) if row)
        rows.append({
            "name": predictors[predictor_id]["display_name"],
            "p24": float(p24["probability"]) if p24 else None,
            "p168": float(p168["probability"]) if p168 else None,
            "cutoff": cutoff,
            "kind": (p24 or p168)["schedule_class"],
        })

    latest_ann = max(announcements, key=lambda row: row["announced_at_utc"])
    data_at = max((row["cutoff"] for row in rows), default=datetime.now(timezone.utc).isoformat())
    latest_url = "https://x.com/thsottiaux/status/" + latest_ann["announcement_id"].removeprefix("ANN_X_")
    hours_since = max(0, (dt(data_at) - dt(latest_ann["announced_at_utc"])).total_seconds() / 3600)

    score_by_forecast = {row["tournament_forecast_id"]: row for row in scores}
    forecast_by_id = {row["tournament_forecast_id"]: row for row in forecasts}
    scored = []
    for score in scores:
        forecast = forecast_by_id.get(score["tournament_forecast_id"])
        if not forecast or forecast["horizon_hours"] != "24":
            continue
        scored.append({
            "name": predictors[forecast["predictor_id"]]["display_name"],
            "issued": forecast["issued_at_utc"],
            "prob": float(forecast["probability"]),
            "label": score["label"],
            "brier": float(score["brier"]),
            "kind": forecast["schedule_class"],
        })
    scored.sort(key=lambda row: row["issued"], reverse=True)
    autopsy = scored[0] if scored else None

    hist_fields = [
        ("p_rolling30", "Recent 30-day rate"),
        ("p_ewma_hl30", "EWMA half-life 30d"),
        ("p_regime_rate", "Two-regime rate"),
        ("p_rolling60", "Recent 60-day rate"),
        ("p_m2", "Calendar model"),
        ("p_global", "Global event rate"),
    ]
    leaderboard = []
    for field, name in hist_fields:
        n, brier, log_loss, prevalence = score_rows(historical, field)
        leaderboard.append({"name": name, "coverage": "full", "n": n, "brier": brier, "log_loss": log_loss, "prevalence": prevalence})
    replay_names = {
        "P_LLM_DEEPSEEK_V4": "DeepSeek V4 Pro",
        "P_LLM_QWEN35_397B": "Qwen 3.5 397B",
        "P_LLM_KIMI_K25": "Kimi K2.5",
        "P_LLM_MINIMAX_M27": "MiniMax M2.7",
        "P_LLM_STEP35": "Step 3.5 Flash",
    }
    for predictor_id, name in replay_names.items():
        selected = [row for row in replay if row["predictor_id"] == predictor_id and row["horizon_hours"] == "24"]
        if selected:
            n, brier, log_loss, prevalence = score_probability_rows(selected)
            leaderboard.append({"name": name, "coverage": "limited", "n": n, "brier": brier, "log_loss": log_loss, "prevalence": prevalence})
    global_brier = next(row["brier"] for row in leaderboard if row["name"] == "Global event rate")
    leaderboard.sort(key=lambda row: (row["coverage"] != "full", row["brier"]))
    best_full = next(row for row in leaderboard if row["coverage"] == "full")

    probabilities_json = json.dumps(
        [{"name": row["name"], "p24": row["p24"], "p168": row["p168"]} for row in rows],
        ensure_ascii=False,
    )
    predictor_dots = "\n".join(
        f"<div class='dotRow'><span>{esc(row['name'])}</span><div class='dotLine'><i style='left:{(row['p24'] or 0) * 100:.2f}%'></i></div><b>{pct(row['p24'])}</b></div>"
        for row in rows
    )

    probability_rows = "\n".join(
        f"<tr><td>{esc(row['name'])}</td><td>{pct(row['p24'])}</td><td>{pct(row['p168'])}</td><td>{esc(row['cutoff'])}</td></tr>"
        for row in rows
    )
    score_rows_html = "\n".join(
        f"<tr><td>{esc(row['name'])}</td><td>{esc(row['issued'])}</td><td>{pct(row['prob'])}</td><td>{esc(row['label'])}</td><td>{row['brier']:.4f}</td><td>{esc(row['kind'])}</td></tr>"
        for row in scored[:12]
    ) or "<tr><td colspan='6'>暂无成熟评分</td></tr>"
    if autopsy:
        autopsy_html = f"""
        <div class="caseStamp">最近复盘</div>
        <h2>{esc(autopsy['name'])} 的一次已揭晓预测</h2>
        <p class="note">这张卡把一次预测拆开看：当时给了多少概率，后来结果是什么，误差又意味着什么。</p>
        <div class="caseGrid">
          <div><span>签发时间</span><strong>{esc(autopsy['issued'])}</strong></div>
          <div><span>当时概率</span><strong>{pct(autopsy['prob'])}</strong></div>
          <div><span>结果</span><strong>{'发生' if autopsy['label'] == '1' else '未发生'}</strong></div>
          <div><span>Brier 误差</span><strong>{autopsy['brier']:.4f}</strong></div>
        </div>
        <p class="note">读法：如果预测偏低但事件发生，误差会变大；如果预测很高却没发生，误差也会变大。这个机制会奖励长期校准，而不是奖励单次喊得最响。</p>
        """
    else:
        autopsy_html = "<h2>预测复盘</h2><p class='note'>等第一批窗口成熟后，这里会展示事前概率、结果和误差。</p>"
    leaderboard_rows = "\n".join(
        f"<tr><td>{index}</td><td>{esc(row['name'])}</td><td>{esc(row['coverage'])}</td><td>{row['n']}</td><td>{row['brier']:.6f}</td><td>{row['log_loss']:.6f}</td><td>{(1 - row['brier'] / global_brier):.1%}</td></tr>"
        for index, row in enumerate(leaderboard, 1)
    )

    max_p = max((row["p24"] or 0 for row in rows), default=0)
    min_p = min((row["p24"] for row in rows if row["p24"] is not None), default=0)
    hero_p = max_p
    avg_p = sum(row["p24"] or 0 for row in rows) / len(rows) if rows else 0
    recent_hist = sorted(historical, key=lambda row: row["issued_at_utc"])
    previous_recent30 = float(recent_hist[-2]["p_rolling30"]) if len(recent_hist) >= 2 else 0.0
    current_recent30 = float(recent_hist[-1]["p_rolling30"]) if recent_hist else 0.0
    recent30_delta = current_recent30 - previous_recent30
    if hero_p >= 0.60:
        alert_level = "Alert"
        alert_copy = "多类信号已经很强，适合高频关注。"
    elif hero_p >= 0.30:
        alert_level = "Watch"
        alert_copy = "值得留意，但还不是压倒性信号。"
    else:
        alert_level = "Quiet"
        alert_copy = "短线仍偏冷，适合按普通节奏观察。"
    action_cluster_count = len({row["action_cluster_id"] for row in actions})
    sorted_ann = sorted(announcements, key=lambda row: row["announced_at_utc"], reverse=True)
    sorted_contexts = sorted(contexts, key=lambda row: row["first_public_at_utc"], reverse=True)
    llm_rows = [row for row in rows if row["name"] in {
        "DeepSeek V4 Pro", "Qwen 3.5 397B", "Kimi K2.5", "MiniMax M2.7", "Step 3.5 Flash"
    }]
    llm_cutoff = max((row["cutoff"] for row in llm_rows), default="")
    if llm_cutoff and dt(llm_cutoff) >= dt(latest_ann["announced_at_utc"]):
        llm_evidence = {
            "tone": "support",
            "label": "LLM 已更新",
            "text": f"五个 LLM 席位读到了 {llm_cutoff} 以前的公开证据，包括最新 reset 公告。",
        }
    else:
        llm_evidence = {
            "tone": "caution",
            "label": "LLM 待更新",
            "text": "LLM 席位还在等待下一轮刷新，当前统计模型先反映最新公告。",
        }
    evidence_items = [
        {
            "tone": "support",
            "label": "新公告刚落地",
            "text": f"最新 reset 公告在 {latest_ann['announced_at_utc']} 出现，近期频率模型会更敏感。",
        },
        {
            "tone": "support",
            "label": "最近节奏偏密",
            "text": "近 30 天模型给出最高 24h 概率，说明最近窗口比长期平均更活跃。",
        },
        {
            "tone": "caution",
            "label": "短期可能降温",
            "text": "刚完成一次 reset 后，再次发生通常需要新的事故、里程碑或发布信号。",
        },
        llm_evidence,
    ]
    evidence_html = "\n".join(
        f"<article class='evidence {item['tone']}'><span>{esc(item['label'])}</span><p>{esc(item['text'])}</p></article>"
        for item in evidence_items
    )
    move_items = [
        ("近 30 天基准", signed_pct(recent30_delta), "最近窗口的事件密度变化，是当前 24h 概率最直观的推力。"),
        ("刚刚 reset", "降温项", f"最新公告距证据截止约 {hours_since:.1f} 小时，短期内会让部分模型更谨慎。"),
        ("LLM 共识", f"{len(llm_rows)} 席", "多个 LLM 在同一份冻结证据上给出判断，用来观察分歧而不是投票定案。"),
    ]
    move_html = "\n".join(
        f"<article class='move'><span>{esc(label)}</span><strong>{esc(value)}</strong><p>{esc(text)}</p></article>"
        for label, value, text in move_items
    )
    lesson_items = [
        (
            "先看基准率",
            "不要从零开始猜",
            f"历史里已经有 {len(announcements)} 条合格公告。全局基准率先回答：长期平均来看，一天内发生的机会有多大？",
        ),
        (
            "再看最近窗口",
            "让新节奏说话",
            f"最近 30 天模型当前给出 {pct(current_recent30)}。它像天气预报里的“近况雷达”，能快速反映最近公告变密或变稀。",
        ),
        (
            "时间间隔模型",
            "刚发生过会影响下一次",
            f"最新公告距证据截止约 {hours_since:.1f} 小时。Renewal 类模型会问：历史上刚 reset 后，下一次通常隔多久？",
        ),
        (
            "日历与背景信号",
            "把节奏和事件放在一起",
            "Calendar / Theory 模型会参考星期、最近事故、发布、里程碑等公开背景，避免只盯着一条最新消息。",
        ),
        (
            "多模型不是投票",
            "看分歧比看平均更有用",
            f"当前有 {len(rows)} 个预测者。它们方法不同，所以分歧本身也是信息：一致时更稳，分散时说明证据还不够单向。",
        ),
        (
            "用结果反过来约束模型",
            "猜完必须算账",
            f"历史完整榜目前每个 full 模型有 {best_full['n']} 个回放点，最好 full 模型是 {best_full['name']}，平均误差 {best_full['brier']:.3f}。",
        ),
    ]
    lesson_html = "\n".join(
        f"<article class='lesson'><span>{esc(kicker)}</span><h3>{esc(title)}</h3><p>{esc(text)}</p></article>"
        for kicker, title, text in lesson_items
    )
    timeline_html = "\n".join(
        f"<li><time>{esc(row['announced_at_utc'])}</time><strong>{esc(row['reset_type'])}</strong><span>{esc(row['reason_type'])}</span></li>"
        for row in sorted_ann[:8]
    )
    context_html = "\n".join(
        f"<li><time>{esc(row['first_public_at_utc'])}</time><strong>{esc(row['event_type'])}</strong><span>{esc(row['scoring_rationale'][:110])}</span></li>"
        for row in sorted_contexts[:6]
    )
    detective_items = [
        ("官方公告", f"{len(announcements)} 条", "先确认来源是不是 Tibo / OpenAI 可追溯公开信息。"),
        ("实际到账", f"{sum(1 for row in confirmations if row['applied_successfully'] == '1')} 条成功线索", "把“宣布会 reset”和“用户看到额度变化”分开记录。"),
        ("事件切分", f"{action_cluster_count} 个独立事件", "一条公告可能包含 hard reset、banked credit 或条件性处理，需要拆成动作。"),
        ("背景信号", f"{len(contexts)} 条", "事故、发布、里程碑会进入公开背景，但不会直接改写结果标签。"),
    ]
    detective_html = "\n".join(
        f"<article class='detective'><span>{esc(label)}</span><strong>{esc(value)}</strong><p>{esc(text)}</p></article>"
        for label, value, text in detective_items
    )
    graph_events = []
    for row in sorted_contexts[:12]:
        if row["event_type"] == "product_incident":
            node_type = "incident"
            title = "事故信号"
        elif row["event_type"] == "milestone":
            node_type = "milestone"
            title = row["milestone_label"] or "里程碑"
        elif row["event_type"] == "product_launch_or_promotion":
            node_type = "launch"
            title = row["launch_label"] or "发布/额度更新"
        else:
            node_type = "context"
            title = row["event_type"]
        graph_events.append({
            "at": row["first_public_at_utc"],
            "type": node_type,
            "title": title,
            "text": row["scoring_rationale"][:82],
        })
    for row in sorted_ann[:12]:
        graph_events.append({
            "at": row["announced_at_utc"],
            "type": "reset",
            "title": row["reset_type"],
            "text": row["reason_type"],
        })
    graph_events.sort(key=lambda row: row["at"])
    route_chunks = [graph_events[index:index + 4] for index in range(0, len(graph_events), 4)]
    route_html = "\n".join(
        (
            f"<div class='routeRow {'reverse' if row_index % 2 else ''}'>"
            + "".join(
                f"<article class='routeNode {esc(item['type'])}'>"
                f"<span>{esc(short_day(item['at']))}</span><b>{esc(item['title'])}</b><p>{esc(item['text'])}</p></article>"
                for item in chunk
            )
            + "</div>"
        )
        for row_index, chunk in enumerate(route_chunks)
    )
    route_json = json.dumps(
        [
            {
                "date": short_day(row["at"]),
                "at": row["at"],
                "type": row["type"],
                "title": row["title"],
                "text": row["text"],
            }
            for row in graph_events
        ],
        ensure_ascii=False,
    )

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%232563eb'/%3E%3Cpath d='M14 39h9l6-16 8 24 6-14h7' fill='none' stroke='white' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
  <title>Tibo Reset Lab</title>
  <style>
    :root {{ color-scheme: light; --ink:#27211b; --muted:#746b60; --line:#e4d8c8; --bg:#fbf5ec; --paper:#fffdf8; --cream:#f4eadc; --blue:#315f7d; --green:#26735b; --amber:#b66a2d; --rose:#a64d56; --shadow:0 20px 60px rgba(80,52,24,.10); }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font:16px/1.62 ui-serif,Georgia,"Times New Roman",serif; color:var(--ink); background:var(--bg); }}
    body::before {{ content:""; position:fixed; inset:0; pointer-events:none; opacity:.55; background-image:linear-gradient(rgba(92,64,32,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(92,64,32,.035) 1px, transparent 1px); background-size:28px 28px; }}
    header {{ position:relative; padding:28px 20px 18px; }}
    .wrap {{ max-width:1120px; margin:0 auto; position:relative; }}
    .topbar {{ display:flex; justify-content:space-between; gap:16px; align-items:center; margin-bottom:24px; }}
    .brand {{ font:700 15px/1.2 system-ui,-apple-system,Segoe UI,sans-serif; letter-spacing:.08em; text-transform:uppercase; }}
    .eyebrow {{ color:var(--blue); font:700 13px/1.2 system-ui,-apple-system,Segoe UI,sans-serif; margin:0 0 12px; }}
    h1 {{ margin:0; max-width:850px; font-size:clamp(42px,7vw,84px); line-height:.96; letter-spacing:0; }}
    .lead {{ max-width:700px; margin:20px 0 0; color:var(--muted); font-size:20px; }}
    nav {{ display:flex; gap:8px; flex-wrap:wrap; }}
    nav a {{ color:var(--ink); background:rgba(255,255,255,.55); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:8px 12px; font:600 14px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    main {{ padding:8px 20px 64px; }}
    .siteLayout {{ max-width:1320px; margin:0 auto; display:grid; grid-template-columns:190px minmax(0,1fr); gap:22px; align-items:start; }}
    .sideNav {{ position:sticky; top:18px; display:flex; flex-direction:column; gap:8px; padding:14px; border:1px solid var(--line); border-radius:18px; background:rgba(255,253,248,.82); box-shadow:var(--shadow); }}
    .sideNav a {{ text-decoration:none; color:var(--ink); border-radius:12px; padding:9px 10px; font:700 14px/1.2 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .sideNav a:hover {{ background:#f6ead9; }}
    .contentFlow {{ min-width:0; }}
    .siteLayout section {{ margin:22px 0; }}
    section {{ margin:26px auto; max-width:1120px; }}
    h2 {{ margin:0 0 10px; font-size:28px; line-height:1.12; }}
    h3 {{ margin:0 0 10px; font-size:18px; }}
    .grid {{ display:grid; grid-template-columns:repeat(12,1fr); gap:16px; }}
    .panel {{ background:rgba(255,253,248,.88); border:1px solid var(--line); border-radius:18px; padding:22px; box-shadow:var(--shadow); }}
    .heroCard {{ grid-column:span 7; padding:28px; }}
    .chartCard {{ grid-column:span 5; }}
    .stat {{ font:800 clamp(68px,11vw,124px)/.9 system-ui,-apple-system,Segoe UI,sans-serif; margin:8px 0 12px; color:var(--blue); }}
    .subtle {{ color:var(--muted); }}
    .facts {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:22px; }}
    .fact {{ border:1px solid var(--line); border-radius:14px; padding:12px; background:var(--cream); }}
    .metricRow {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .metric {{ background:rgba(255,253,248,.8); border:1px solid var(--line); border-radius:16px; padding:16px; }}
    .metric strong {{ display:block; font:800 28px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; margin-top:5px; }}
    table {{ width:100%; border-collapse:collapse; background:var(--paper); border:1px solid var(--line); border-radius:14px; overflow:hidden; font-family:system-ui,-apple-system,Segoe UI,sans-serif; }}
    .tableWrap {{ overflow:auto; border-radius:14px; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ background:#f3eadf; font-weight:700; }}
    td:nth-child(n+2), th:nth-child(n+2) {{ text-align:right; }}
    .note {{ color:var(--muted); margin:8px 0 14px; }}
    .probTherm {{ margin:0 0 22px; padding:18px; border-radius:18px; background:#f6ead9; }}
    .thermTop {{ display:flex; justify-content:space-between; align-items:baseline; gap:12px; margin-bottom:12px; }}
    .thermTop span {{ color:var(--muted); }}
    .thermTop strong {{ font:800 42px/1 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); white-space:nowrap; }}
    .thermTrack {{ height:18px; border-radius:999px; background:#e5d5bf; overflow:hidden; }}
    .thermFill {{ height:100%; width:{hero_p * 100:.2f}%; border-radius:999px; background:var(--blue); }}
    .dotRows {{ display:flex; flex-direction:column; gap:12px; margin-top:14px; font-family:system-ui,-apple-system,Segoe UI,sans-serif; }}
    .dotRow {{ display:grid; grid-template-columns:150px 1fr 54px; align-items:center; gap:10px; font-size:14px; }}
    .dotLine {{ position:relative; height:2px; background:#dacbb8; }}
    .dotLine i {{ position:absolute; top:50%; width:14px; height:14px; border-radius:50%; background:var(--blue); transform:translate(-50%,-50%); box-shadow:0 0 0 4px #fff8ee; }}
    .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .chip {{ border:1px solid var(--line); background:var(--paper); border-radius:999px; padding:7px 11px; color:var(--muted); font-family:system-ui,-apple-system,Segoe UI,sans-serif; }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    .evidenceGrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .evidence {{ border:1px solid var(--line); border-radius:16px; padding:16px; background:var(--paper); min-height:150px; }}
    .evidence span {{ display:inline-block; font-weight:700; margin-bottom:8px; }}
    .evidence p {{ margin:0; color:var(--muted); }}
    .evidence.support {{ border-top:5px solid var(--green); }}
    .evidence.caution {{ border-top:5px solid var(--amber); }}
    .timeline {{ list-style:none; padding:0; margin:0; }}
    .timeline li {{ margin:0 0 12px 0; padding:13px 14px; border:1px solid var(--line); border-radius:14px; background:rgba(255,253,248,.78); }}
    .timeline time {{ display:block; color:var(--muted); font-size:13px; }}
    .timeline strong {{ margin-right:8px; }}
    .timeline span {{ color:var(--muted); }}
    .predictionBox {{ display:grid; grid-template-columns:1fr auto; gap:18px; align-items:center; }}
    input[type=range] {{ width:100%; accent-color:var(--blue); }}
    .sliderValue {{ font:800 42px/1 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); min-width:110px; text-align:right; }}
    .storyStrip {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
    .story {{ padding:18px; border:1px solid var(--line); border-radius:18px; background:rgba(255,253,248,.76); }}
    .readCard {{ margin-top:20px; padding:16px 18px; border-radius:16px; background:#f6ead9; color:#57493b; }}
    .labRibbon {{ display:grid; grid-template-columns:1.15fr .85fr; gap:16px; }}
    .alertCard {{ background:var(--ink); color:#fff8ee; border-radius:22px; padding:24px; box-shadow:var(--shadow); }}
    .alertCard span {{ display:inline-block; font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; letter-spacing:.08em; text-transform:uppercase; color:#f0c996; margin-bottom:14px; }}
    .alertCard strong {{ display:block; font:800 46px/1 system-ui,-apple-system,Segoe UI,sans-serif; margin-bottom:10px; }}
    .moveGrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
    .move {{ padding:16px; border:1px solid var(--line); border-radius:16px; background:var(--paper); }}
    .move span {{ color:var(--muted); font-family:system-ui,-apple-system,Segoe UI,sans-serif; font-size:13px; }}
    .move strong {{ display:block; margin:8px 0; font:800 26px/1 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); }}
    .watchList {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; }}
    .watch {{ border:1px solid var(--line); border-radius:16px; background:rgba(255,253,248,.78); padding:16px; }}
    .watch strong {{ display:block; margin-bottom:6px; }}
    .seasonBoard {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .season {{ padding:18px; border-radius:18px; border:1px solid var(--line); background:var(--paper); }}
    .season span {{ color:var(--muted); font-family:system-ui,-apple-system,Segoe UI,sans-serif; font-size:13px; }}
    .season strong {{ display:block; font:800 24px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; margin-top:8px; }}
    .lessonIntro {{ display:grid; grid-template-columns:.8fr 1.2fr; gap:18px; align-items:end; margin-bottom:14px; }}
    .lessonIntro strong {{ display:block; font:800 clamp(42px,8vw,86px)/.92 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); }}
    .lessonGrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
    .lesson {{ position:relative; padding:20px; border:1px solid var(--line); border-radius:20px; background:var(--paper); min-height:190px; }}
    .lesson::before {{ content:""; position:absolute; width:34px; height:4px; border-radius:999px; background:var(--blue); top:16px; right:18px; opacity:.8; }}
    .lesson span {{ color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .lesson p {{ color:var(--muted); margin:0; }}
    .scoreExplainer {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:14px; }}
    .scoreExplainer div {{ background:#f6ead9; border-radius:16px; padding:16px; }}
    .scoreExplainer strong {{ display:block; margin-bottom:6px; }}
    .caseFile {{ border:1px solid #d8c5ad; background:#2b241d; color:#fff8ee; border-radius:24px; padding:26px; box-shadow:var(--shadow); }}
    .caseFile .note {{ color:#e5d6c3; }}
    .caseStamp {{ display:inline-block; margin-bottom:12px; padding:6px 10px; border:1px solid #8f7658; border-radius:999px; color:#f0c996; font:800 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; letter-spacing:.08em; }}
    .caseGrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:18px 0; }}
    .caseGrid div {{ padding:14px; border-radius:16px; background:rgba(255,248,238,.10); }}
    .caseGrid span {{ display:block; color:#d9c6ad; font:700 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; margin-bottom:8px; }}
    .caseGrid strong {{ font:800 22px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .detectiveGrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }}
    .detective {{ padding:18px; border:1px solid var(--line); border-radius:18px; background:var(--paper); }}
    .detective span {{ color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .detective strong {{ display:block; margin:8px 0; font:800 24px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); }}
    .detective p {{ margin:0; color:var(--muted); }}
    .pageGrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }}
    .pageCard {{ min-height:190px; padding:22px; border:1px solid var(--line); border-radius:20px; background:var(--paper); box-shadow:var(--shadow); text-decoration:none; color:var(--ink); }}
    .pageCard span {{ color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .pageCard strong {{ display:block; margin:10px 0; font:800 24px/1.08 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .pageCard p {{ margin:0; color:var(--muted); }}
    .routeMap {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:14px; }}
    .routeMap div {{ padding:14px; border:1px solid var(--line); border-radius:16px; background:#f6ead9; }}
    .routeMap span {{ color:var(--muted); font:800 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .routeMap strong {{ display:block; margin-top:8px; }}
    .eventMap {{ padding:18px; border:1px solid var(--line); border-radius:24px; background:rgba(255,253,248,.72); box-shadow:var(--shadow); }}
    .routePath {{ display:flex; flex-direction:column; gap:28px; position:relative; }}
    .routeRow {{ display:grid; grid-template-columns:repeat(4,1fr); gap:18px; position:relative; }}
    .routeRow.reverse {{ direction:rtl; }}
    .routeRow.reverse .routeNode {{ direction:ltr; }}
    .routeRow::before {{ content:""; position:absolute; left:8%; right:8%; top:34px; height:8px; border-radius:999px; background:repeating-linear-gradient(90deg,#d8c3a6 0 18px,#c49d72 18px 28px); opacity:.64; }}
    .routeRow:not(:last-child)::after {{ content:""; position:absolute; width:52px; height:70px; border:8px solid #d8c3a6; border-left:0; border-bottom:0; border-radius:0 40px 0 0; right:3%; top:34px; opacity:.64; }}
    .routeRow.reverse:not(:last-child)::after {{ right:auto; left:3%; transform:scaleX(-1); }}
    .routeNode {{ position:relative; z-index:1; padding:54px 16px 16px; border:1px solid var(--line); border-radius:20px; background:rgba(255,253,248,.96); box-shadow:0 12px 34px rgba(80,52,24,.08); min-height:170px; }}
    .routeNode::before {{ content:""; position:absolute; top:20px; left:18px; width:24px; height:24px; border-radius:50%; border:5px solid #fff8ee; background:var(--blue); box-shadow:0 0 0 1px var(--line); }}
    .routeNode.reset::before {{ background:var(--green); }}
    .routeNode.incident::before {{ background:var(--rose); }}
    .routeNode.launch::before {{ background:var(--amber); }}
    .routeNode.milestone::before {{ background:var(--blue); }}
    .routeNode span {{ color:var(--muted); font:800 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .routeNode b {{ display:block; margin:7px 0; font:800 17px/1.15 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .routeNode p {{ margin:0; color:var(--muted); font-size:14px; }}
    footer {{ border-top:1px solid var(--line); padding:24px 20px; color:var(--muted); }}
    a {{ color:var(--blue); }}
    @media (max-width: 950px) {{ .topbar {{ align-items:flex-start; flex-direction:column; }} .siteLayout {{ display:block; }} .sideNav {{ position:relative; top:auto; flex-direction:row; overflow:auto; margin:0 auto 14px; max-width:1120px; }} .sideNav a {{ white-space:nowrap; }} .heroCard,.chartCard {{ grid-column:1 / -1; }} .two,.facts,.metricRow,.evidenceGrid,.storyStrip,.labRibbon,.moveGrid,.watchList,.seasonBoard,.lessonIntro,.lessonGrid,.scoreExplainer,.caseGrid,.detectiveGrid,.routeMap,.pageGrid {{ grid-template-columns:1fr; }} .routeRow,.routeRow.reverse {{ grid-template-columns:1fr; direction:ltr; }} .routeRow::before {{ left:30px; right:auto; top:12px; bottom:12px; width:8px; height:auto; background:repeating-linear-gradient(180deg,#d8c3a6 0 18px,#c49d72 18px 28px); }} .routeRow::after {{ display:none; }} .routeNode {{ min-height:auto; padding-left:62px; padding-top:18px; }} .routeNode::before {{ top:18px; left:18px; }} .dotRow {{ grid-template-columns:118px 1fr 48px; }} .predictionBox {{ grid-template-columns:1fr; }} .sliderValue {{ text-align:left; }} table {{ font-size:14px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topbar">
        <div class="brand">Tibo Reset Lab</div>
        <nav aria-label="页面导航">
          <a href="index.html">今日</a>
          <a href="map.html">事件地图</a>
          <a href="learn.html">概率小课堂</a>
          <a href="history.html">历史表现</a>
        </nav>
      </div>
      <p class="eyebrow">公开证据里的概率练习</p>
      <h1>下一次额度重置，会在什么时候出现？</h1>
      <p class="lead">这里把公开公告、背景事件、统计模型和 LLM 判断放在同一张桌面上。你看到的不只是一个数字，而是它为什么会变。</p>
    </div>
  </header>
  <main>
    <div class="siteLayout">
      <aside class="sideNav" aria-label="今日页目录">
        <a href="#current">现在几成</a>
        <a href="#why">为什么变化</a>
        <a href="#play">我来猜</a>
        <a href="#more">继续看</a>
      </aside>
      <div class="contentFlow">
    <section class="metricRow" aria-label="关键数字">
      <div class="metric"><span class="subtle">最高 24h 概率</span><strong>{pct(max_p)}</strong></div>
      <div class="metric"><span class="subtle">平均 24h 概率</span><strong>{pct(avg_p)}</strong></div>
      <div class="metric"><span class="subtle">历史公告</span><strong>{len(announcements)}</strong></div>
      <div class="metric"><span class="subtle">独立重置事件</span><strong>{action_cluster_count}</strong></div>
    </section>

    <section class="grid" id="current">
      <div class="panel heroCard">
        <h2>当前实验卡</h2>
        <div class="stat">{pct(hero_p)}</div>
        <p class="subtle">这是当前最高 24h 概率。所有预测者的区间是 {pct(min_p)} 到 {pct(max_p)}，证据更新至 <code>{esc(data_at)}</code>。</p>
        <div class="facts">
          <div class="fact"><strong>最新公告</strong><br><a href="{esc(latest_url)}">原始 X 帖</a></div>
          <div class="fact"><strong>公告时间</strong><br>{esc(latest_ann['announced_at_utc'])}</div>
          <div class="fact"><strong>距今约</strong><br>{hours_since:.1f} 小时</div>
        </div>
        <div class="readCard"><strong>怎么读：</strong>如果把最近相似情形重复 10 次，最高模型大约认为其中 4 次会在一天内再出现 reset 公告。</div>
      </div>
      <div class="panel chartCard">
        <div class="probTherm">
          <div class="thermTop"><span>最高 24h 概率</span><strong>{pct(hero_p)}</strong></div>
          <div class="thermTrack"><div class="thermFill"></div></div>
        </div>
        <h2>预测者分歧</h2>
        <p class="note">每个点是一位预测者的 24h 概率。点越靠右，越相信短期会再次出现公告。</p>
        <div class="dotRows">{predictor_dots}</div>
      </div>
    </section>

    <section id="why">
      <h2>证据天平</h2>
      <p class="note">这些卡片把模型输入翻译成人话：哪些信号把概率往上推，哪些信号让它慢下来。</p>
      <div class="evidenceGrid">{evidence_html}</div>
    </section>

    <section id="more">
      <div class="lessonIntro">
        <div>
          <p class="eyebrow">分页面浏览</p>
          <h2>把长页面拆成几条清晰路线</h2>
        </div>
        <p class="note">主页保留今天最重要的数字。想看事件节奏、概率原理或历史榜单，可以进入独立页面慢慢探索。</p>
      </div>
      <div class="pageGrid">
        <a class="pageCard" href="map.html"><span>事件地图</span><strong>OpenAI 相关事件路线</strong><p>用一条连续的动态路线串起事故、发布、里程碑和 reset 公告。</p></a>
        <a class="pageCard" href="learn.html"><span>科普</span><strong>概率为什么可信</strong><p>用通俗语言解释基准率、最近窗口、时间间隔和评分。</p></a>
        <a class="pageCard" href="history.html"><span>回放</span><strong>历史演练榜</strong><p>把统计模型、LLM、玩家和 Crowd 放到可比较的长期榜单里。</p></a>
      </div>
    </section>

    <section class="panel" id="play">
      <h2>你的判断是多少？</h2>
      <div class="predictionBox">
        <div>
          <p class="note">拖动滑块，给出你自己的 24h 概率。这个版本先在浏览器本地显示，后续会接入匿名提交和 Crowd 分布。</p>
          <input id="guess" type="range" min="0" max="100" value="{hero_p * 100:.0f}" aria-label="你的24小时概率">
          <div class="chips">
            <span class="chip">10%：很冷</span>
            <span class="chip">40%：值得看</span>
            <span class="chip">70%：强信号</span>
          </div>
        </div>
        <div class="sliderValue"><span id="guessValue">{hero_p * 100:.0f}</span>%</div>
      </div>
    </section>

    <section class="panel">
      <h2>主页只保留一个读法</h2>
      <div class="chips">
        <span class="chip">先看最高 24h 概率</span>
        <span class="chip">再看预测者分歧</span>
        <span class="chip">最后看证据天平</span>
      </div>
      <p class="note">如果想知道模型为什么可信，去“概率小课堂”；如果想看事件如何连接，去“事件地图”；如果想比较谁更准，去“历史表现”。</p>
    </section>
      </div>
    </div>
  </main>
  <footer><div class="wrap">数据来自仓库 CSV。查看 <a href="https://github.com/CRF2004/tibo-reset-lab/blob/main/README.md">README</a>、<a href="https://github.com/CRF2004/tibo-reset-lab/blob/main/reports/community_dashboard.md">Markdown Dashboard</a> 和 <a href="https://github.com/CRF2004/tibo-reset-lab/blob/main/PUBLIC_PRODUCT_IDEAS.md">产品路线</a>。</div></footer>
  <script>
    const data = {probabilities_json};
    const guess = document.getElementById('guess');
    const guessValue = document.getElementById('guessValue');
    guess.addEventListener('input', () => {{ guessValue.textContent = guess.value; }});
  </script>
</body>
</html>
"""
    page_css = """
    :root { color-scheme: light; --ink:#27211b; --muted:#746b60; --line:#e4d8c8; --bg:#fbf5ec; --paper:#fffdf8; --cream:#f4eadc; --blue:#315f7d; --green:#26735b; --amber:#b66a2d; --rose:#a64d56; --shadow:0 20px 60px rgba(80,52,24,.10); }
    * { box-sizing: border-box; }
    body { margin:0; font:16px/1.62 ui-serif,Georgia,"Times New Roman",serif; color:var(--ink); background:var(--bg); }
    body::before { content:""; position:fixed; inset:0; pointer-events:none; opacity:.55; background-image:linear-gradient(rgba(92,64,32,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(92,64,32,.035) 1px, transparent 1px); background-size:28px 28px; }
    .wrap { max-width:1120px; margin:0 auto; position:relative; }
    header { padding:28px 20px 18px; }
    main { padding:8px 20px 64px; }
    .topbar { display:flex; justify-content:space-between; gap:16px; align-items:center; margin-bottom:24px; }
    .brand { font:700 15px/1.2 system-ui,-apple-system,Segoe UI,sans-serif; letter-spacing:.08em; text-transform:uppercase; }
    nav { display:flex; gap:8px; flex-wrap:wrap; }
    nav a { color:var(--ink); background:rgba(255,255,255,.55); text-decoration:none; border:1px solid var(--line); border-radius:999px; padding:8px 12px; font:600 14px/1 system-ui,-apple-system,Segoe UI,sans-serif; }
    .eyebrow { color:var(--blue); font:700 13px/1.2 system-ui,-apple-system,Segoe UI,sans-serif; margin:0 0 12px; }
    h1 { margin:0; max-width:820px; font-size:clamp(42px,7vw,78px); line-height:.98; letter-spacing:0; }
    h2 { margin:0 0 10px; font-size:28px; line-height:1.12; }
    h3 { margin:0 0 10px; font-size:18px; }
    .lead { max-width:720px; margin:18px 0 0; color:var(--muted); font-size:20px; }
    section { margin:26px auto; max-width:1120px; }
    .panel { background:rgba(255,253,248,.88); border:1px solid var(--line); border-radius:18px; padding:22px; box-shadow:var(--shadow); }
    .note { color:var(--muted); margin:8px 0 14px; }
    .chips { display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }
    .chip { border:1px solid var(--line); background:var(--paper); border-radius:999px; padding:7px 11px; color:var(--muted); font-family:system-ui,-apple-system,Segoe UI,sans-serif; }
    .grid3 { display:grid; grid-template-columns:repeat(3,1fr); gap:14px; }
    .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    .lesson,.card { padding:20px; border:1px solid var(--line); border-radius:18px; background:var(--paper); box-shadow:0 12px 34px rgba(80,52,24,.08); }
    .lesson span,.card span { color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }
    .lesson p,.card p { color:var(--muted); margin:0; }
    .move,.detective { padding:18px; border:1px solid var(--line); border-radius:18px; background:var(--paper); box-shadow:0 12px 34px rgba(80,52,24,.08); }
    .move span,.detective span { color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }
    .move strong,.detective strong { display:block; margin:8px 0; font:800 24px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--blue); }
    .move p,.detective p { margin:0; color:var(--muted); }
    .timeline { list-style:none; padding:0; margin:0; }
    .timeline li { margin:0 0 12px 0; padding:13px 14px; border:1px solid var(--line); border-radius:14px; background:rgba(255,253,248,.78); }
    .timeline time { display:block; color:var(--muted); font-size:13px; }
    .timeline strong { margin-right:8px; }
    .timeline span { color:var(--muted); }
    .caseStamp { display:inline-block; margin-bottom:12px; padding:6px 10px; border:1px solid #d8c5ad; border-radius:999px; color:var(--amber); font:800 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; letter-spacing:.08em; }
    .caseGrid { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin:18px 0; }
    .caseGrid div { padding:14px; border-radius:16px; background:#f6ead9; }
    .caseGrid span { display:block; color:var(--muted); font:700 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; margin-bottom:8px; }
    .caseGrid strong { font:800 22px/1.1 system-ui,-apple-system,Segoe UI,sans-serif; }
    table { width:100%; border-collapse:collapse; background:var(--paper); border:1px solid var(--line); border-radius:14px; overflow:hidden; font-family:system-ui,-apple-system,Segoe UI,sans-serif; }
    .tableWrap { overflow:auto; border-radius:14px; }
    th,td { padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
    th { background:#f3eadf; font-weight:700; }
    td:nth-child(n+2), th:nth-child(n+2) { text-align:right; }
    footer { border-top:1px solid var(--line); padding:24px 20px; color:var(--muted); }
    a { color:var(--blue); }
    @media (max-width: 850px) { .topbar { align-items:flex-start; flex-direction:column; } .grid3,.grid2,.caseGrid { grid-template-columns:1fr; } table { font-size:14px; } }
    """
    nav_html = """
        <nav aria-label="页面导航">
          <a href="index.html">今日</a>
          <a href="map.html">事件地图</a>
          <a href="learn.html">概率小课堂</a>
          <a href="history.html">历史表现</a>
        </nav>
    """
    map_html = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>OpenAI 事件地图 · Tibo Reset Lab</title>
  <style>
    {page_css}
    #d3map {{ min-height:560px; border:1px solid var(--line); border-radius:24px; background:linear-gradient(180deg, rgba(255,253,248,.94), rgba(246,234,217,.78)); box-shadow:var(--shadow); overflow:hidden; }}
    .mapStage {{ display:grid; grid-template-columns:1fr 320px; gap:16px; align-items:start; }}
    .eventDetail {{ position:sticky; top:18px; min-height:300px; padding:22px; border:1px solid var(--line); border-radius:22px; background:var(--paper); box-shadow:var(--shadow); }}
    .eventDetail span {{ color:var(--amber); font:800 13px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .eventDetail strong {{ display:block; margin:10px 0; font:800 28px/1.08 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .eventDetail p {{ color:var(--muted); margin:0 0 12px; }}
    .eventDetail code {{ display:block; white-space:normal; color:var(--muted); font-size:13px; }}
    @media (max-width: 950px) {{ .mapStage {{ grid-template-columns:1fr; }} .eventDetail {{ position:relative; top:auto; }} #d3map {{ min-height:760px; }} }}
  </style>
</head>
<body>
  <header><div class="wrap"><div class="topbar"><div class="brand">Tibo Reset Lab</div>{nav_html}</div><p class="eyebrow">OpenAI 事件地图</p><h1>把所有信号连成一条会转弯的路线</h1><p class="lead">事故、里程碑、发布和 reset 公告会改变近期节奏。这里按公开时间把它们串起来，看清预测不是盯着单个点，而是在读一段走势。</p></div></header>
  <main>
    <section>
      <div class="mapStage">
        <div id="d3map" role="img" aria-label="按时间连接的 OpenAI 相关事件路线图"></div>
        <aside id="eventDetail" class="eventDetail" aria-live="polite"></aside>
      </div>
      <div class="chips">
        <span class="chip">按公开时间前进</span><span class="chip">红：事故</span><span class="chip">蓝：里程碑</span><span class="chip">橙：发布/额度更新</span><span class="chip">绿：reset 公告</span>
      </div>
    </section>
  </main>
  <footer><div class="wrap">数据来自仓库 CSV。返回 <a href="index.html">今日概览</a>。</div></footer>
  <script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
  <script>
    const events = {route_json};
    const colors = {{ incident:"#a64d56", reset:"#26735b", launch:"#b66a2d", milestone:"#315f7d", context:"#746b60" }};
    const labels = {{ incident:"事故", reset:"reset", launch:"发布", milestone:"里程碑", context:"背景" }};
    const wrap = document.getElementById("d3map");
    const detail = document.getElementById("eventDetail");
    let activeIndex = events.length - 1;

    function renderDetail(index) {{
      activeIndex = index;
      const event = events[index];
      detail.innerHTML = `
        <span>${{String(index + 1).padStart(2, "0")}} · ${{event.date}} · ${{labels[event.type] || "事件"}}</span>
        <strong>${{event.title}}</strong>
        <p>${{event.text}}</p>
        <code>${{event.at}}</code>
      `;
      d3.selectAll("g.event circle")
        .attr("stroke-width", d => d.index === activeIndex ? 9 : 6)
        .attr("stroke", d => d.index === activeIndex ? "#27211b" : "#fff8ee");
    }}

    function renderMap() {{
      const box = wrap.getBoundingClientRect();
      const width = Math.max(340, Math.round(box.width || 900));
      const mobile = width < 620;
      const cols = mobile ? 3 : 4;
      const left = mobile ? 48 : 84;
      const right = mobile ? 48 : 84;
      const rowH = mobile ? 142 : 172;
      const rows = Math.ceil(events.length / cols);
      const height = 116 + Math.max(1, rows - 1) * rowH;
      const step = cols === 1 ? 0 : (width - left - right) / (cols - 1);
      const points = events.map((event, index) => {{
        const row = Math.floor(index / cols);
        const col = index % cols;
        const visualCol = row % 2 === 0 ? col : cols - 1 - col;
        return {{ ...event, index, x:left + visualCol * step, y:64 + row * rowH }};
      }});
      const svg = d3.select(wrap).html("").append("svg")
        .attr("viewBox", `0 0 ${{width}} ${{height}}`)
        .attr("width", "100%")
        .attr("height", height);
      const line = d3.line().x(d => d.x).y(d => d.y).curve(d3.curveCatmullRom.alpha(.62));
      svg.append("path")
        .datum(points)
        .attr("d", line)
        .attr("fill", "none")
        .attr("stroke", "#c49d72")
        .attr("stroke-width", mobile ? 8 : 10)
        .attr("stroke-linecap", "round")
        .attr("opacity", .62);
      svg.append("path")
        .datum(points)
        .attr("d", line)
        .attr("fill", "none")
        .attr("stroke", "#fff8ee")
        .attr("stroke-width", mobile ? 2 : 3)
        .attr("stroke-linecap", "round")
        .attr("opacity", .9);
      const node = svg.selectAll("g.event").data(points).join("g")
        .attr("class", "event")
        .attr("transform", d => `translate(${{d.x}},${{d.y}})`)
        .attr("tabindex", 0)
        .attr("role", "button")
        .style("cursor", "pointer")
        .on("click", (event, d) => renderDetail(d.index))
        .on("keydown", (event, d) => {{ if (event.key === "Enter" || event.key === " ") renderDetail(d.index); }});
      node.append("circle").attr("r", mobile ? 19 : 23).attr("fill", d => colors[d.type] || colors.context).attr("stroke", d => d.index === activeIndex ? "#27211b" : "#fff8ee").attr("stroke-width", d => d.index === activeIndex ? 9 : 6);
      node.append("text").attr("y", 5).attr("text-anchor", "middle").attr("fill", "#fff8ee").attr("font-family", "system-ui,-apple-system,Segoe UI,sans-serif").attr("font-weight", 800).attr("font-size", mobile ? 11 : 12).text(d => d.index + 1);
      node.append("text").attr("x", mobile ? 0 : 0).attr("y", mobile ? 45 : 52).attr("text-anchor", "middle").attr("fill", "#746b60").attr("font-family", "system-ui,-apple-system,Segoe UI,sans-serif").attr("font-weight", 800).attr("font-size", 12).text(d => d.date);
      node.append("text").attr("x", 0).attr("y", mobile ? 64 : 73).attr("text-anchor", "middle").attr("fill", "#27211b").attr("font-family", "system-ui,-apple-system,Segoe UI,sans-serif").attr("font-weight", 800).attr("font-size", mobile ? 12 : 13).text(d => {{
        const title = d.title.length > 9 ? d.title.slice(0, 9) + "..." : d.title;
        return title;
      }});
    }}
    renderMap();
    renderDetail(activeIndex);
    addEventListener("resize", () => requestAnimationFrame(renderMap));
  </script>
</body>
</html>
"""
    learn_html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>概率小课堂 · Tibo Reset Lab</title><style>{page_css}</style></head>
<body><header><div class="wrap"><div class="topbar"><div class="brand">Tibo Reset Lab</div>{nav_html}</div><p class="eyebrow">概率小课堂</p><h1>用人话解释这套预测为什么能被检验</h1><p class="lead">好的概率预测不是“说中了”这么简单。它要先有历史参照，再用新证据修正，最后接受已经揭晓结果的评分。</p></div></header>
<main>
  <section class="grid3">{lesson_html}</section>
  <section><h2>为什么它会动？</h2><p class="note">这些变化来自数据表中能复核的事实。</p><div class="grid3">{move_html}</div></section>
  <section class="panel"><h2>评分怎么读</h2><p class="note">Brier 可以理解成“离结果有多远”，Log Loss 会惩罚非常自信但错得离谱的判断，覆盖率说明这个模型有没有经历足够多的历史窗口。</p><div class="grid3"><article class="card"><span>Brier</span><h3>平均误差越小越好</h3><p>发生记为 1，未发生记为 0。预测越贴近最后结果，分数越低。</p></article><article class="card"><span>Log Loss</span><h3>别轻易说绝对</h3><p>它会重罚过度自信的错误，让模型不敢靠喊极端概率取巧。</p></article><article class="card"><span>覆盖率</span><h3>样本越多越稳</h3><p>完整历史窗口比少量回放更有说服力，所以榜单会同时显示 N。</p></article></div></section>
  <section><h2>证据侦探</h2><div class="grid3">{detective_html}</div></section>
</main><footer><div class="wrap">返回 <a href="index.html">今日概览</a>。</div></footer></body></html>
"""
    history_html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>历史表现 · Tibo Reset Lab</title><style>{page_css}</style></head>
<body><header><div class="wrap"><div class="topbar"><div class="brand">Tibo Reset Lab</div>{nav_html}</div><p class="eyebrow">历史演练榜</p><h1>把统计模型、LLM、玩家和 Crowd 放到同一张表里</h1><p class="lead">历史回放只允许使用当时已经公开的证据。这样比较的不是事后解释能力，而是事前判断是否稳定。</p></div></header>
<main>
  <section class="grid2"><div><h2>历史演练榜</h2><p class="note">full 是完整历史窗口；limited 是少量回放点。先看样本量，再看平均误差。</p><div class="tableWrap"><table><thead><tr><th>#</th><th>预测者</th><th>覆盖</th><th>N</th><th>平均误差</th><th>惩罚大错</th><th>相对基础模型</th></tr></thead><tbody>{leaderboard_rows}</tbody></table></div></div><div><h2>已揭晓预测</h2><p class="note">结果为 1 表示 24 小时内发生。误差越小，说明当时概率越贴近结果。</p><div class="tableWrap"><table><thead><tr><th>预测者</th><th>签发时间</th><th>当时猜24h</th><th>结果</th><th>误差</th><th>类型</th></tr></thead><tbody>{score_rows_html}</tbody></table></div></div></section>
  <section class="panel">{autopsy_html}</section>
  <section class="grid2"><div class="panel"><h2>最近 reset 公告</h2><ul class="timeline">{timeline_html}</ul></div><div class="panel"><h2>最近公开背景信号</h2><ul class="timeline">{context_html}</ul></div></section>
</main><footer><div class="wrap">返回 <a href="index.html">今日概览</a>。</div></footer></body></html>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(html_text, encoding="utf-8")
    (OUT / "map.html").write_text(map_html, encoding="utf-8")
    (OUT / "learn.html").write_text(learn_html, encoding="utf-8")
    (OUT / "history.html").write_text(history_html, encoding="utf-8")
    # Keep the old path working.
    (OUT / "community.html").write_text(html_text, encoding="utf-8")
    print(f"Built {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
