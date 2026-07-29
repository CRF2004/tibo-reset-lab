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
    .routeMap {{ display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-top:14px; }}
    .routeMap div {{ padding:14px; border:1px solid var(--line); border-radius:16px; background:#f6ead9; }}
    .routeMap span {{ color:var(--muted); font:800 12px/1 system-ui,-apple-system,Segoe UI,sans-serif; }}
    .routeMap strong {{ display:block; margin-top:8px; }}
    footer {{ border-top:1px solid var(--line); padding:24px 20px; color:var(--muted); }}
    a {{ color:var(--blue); }}
    @media (max-width: 950px) {{ .topbar {{ align-items:flex-start; flex-direction:column; }} .heroCard,.chartCard {{ grid-column:1 / -1; }} .two,.facts,.metricRow,.evidenceGrid,.storyStrip,.labRibbon,.moveGrid,.watchList,.seasonBoard,.lessonIntro,.lessonGrid,.scoreExplainer,.caseGrid,.detectiveGrid,.routeMap {{ grid-template-columns:1fr; }} .dotRow {{ grid-template-columns:118px 1fr 48px; }} .predictionBox {{ grid-template-columns:1fr; }} .sliderValue {{ text-align:left; }} table {{ font-size:14px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <div class="topbar">
        <div class="brand">Tibo Reset Lab</div>
        <nav aria-label="页面导航">
          <a href="#current">当前实验</a>
          <a href="#learn">概率小课堂</a>
          <a href="#why">证据天平</a>
          <a href="#play">你的判断</a>
          <a href="#history">历史表现</a>
        </nav>
      </div>
      <p class="eyebrow">公开证据里的概率练习</p>
      <h1>下一次额度重置，会在什么时候出现？</h1>
      <p class="lead">这里把公开公告、背景事件、统计模型和 LLM 判断放在同一张桌面上。你看到的不只是一个数字，而是它为什么会变。</p>
    </div>
  </header>
  <main>
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

    <section class="labRibbon">
      <div class="alertCard">
        <span>6小时观察层</span>
        <strong>{esc(alert_level)}</strong>
        <p>{esc(alert_copy)} 这一层先作为公开展示，后续会用历史回测冻结阈值。</p>
      </div>
      <div class="panel">
        <h2>下一步会补什么</h2>
        <p class="note">产品路线里的第一阶段正在落地：解释概率、展示分歧、让读者先做一次自己的判断。</p>
        <div class="chips">
          <span class="chip">概率变动解释器</span>
          <span class="chip">Tibo Watch</span>
          <span class="chip">历史回放</span>
        </div>
      </div>
    </section>

    <section id="learn">
      <div class="lessonIntro">
        <div>
          <p class="eyebrow">概率小课堂</p>
          <h2>这个数字不是拍脑袋来的</h2>
        </div>
        <p class="note">我们的做法很朴素：先尊重历史频率，再看最近节奏、时间间隔和公开背景信号；最后用已经揭晓的结果检验模型有没有过度自信。</p>
      </div>
      <div class="lessonGrid">{lesson_html}</div>
    </section>

    <section id="why">
      <h2>证据天平</h2>
      <p class="note">这些卡片把模型输入翻译成人话：哪些信号把概率往上推，哪些信号让它慢下来。</p>
      <div class="evidenceGrid">{evidence_html}</div>
    </section>

    <section>
      <h2>为什么它会动？</h2>
      <p class="note">这是“Why did it move”的第一版：先把可直接从数据表读出的变化讲清楚，之后再接入特征消融。</p>
      <div class="moveGrid">{move_html}</div>
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

    <section>
      <h2>Tibo Watch 订阅草图</h2>
      <p class="note">不是所有新帖都值得打扰你。订阅层级会把“明确 reset”和“可能相关背景”分开。</p>
      <div class="watchList">
        <article class="watch"><strong>Only confirmed</strong><p class="note">只看明确 reset / usage limit 公告，适合只关心结果的人。</p></article>
        <article class="watch"><strong>Relevant posts</strong><p class="note">加入事故、里程碑、发布和额度讨论，适合想看概率为什么变化的人。</p></article>
        <article class="watch"><strong>Research feed</strong><p class="note">保留发现时间、来源、分类和通知延迟，适合核查数据的人。</p></article>
      </div>
    </section>

    <section>
      <div class="lessonIntro">
        <div>
          <p class="eyebrow">证据侦探</p>
          <h2>证据是怎么被放进数据集的？</h2>
        </div>
        <p class="note">预测可信，前提是事件定义清楚。我们把“看到帖子”“确认含义”“切分动作”“等待结果”拆成几步，避免把不同性质的 reset 混在一起。</p>
      </div>
      <div class="detectiveGrid">{detective_html}</div>
      <div class="routeMap">
        <div><span>1</span><strong>发现新帖</strong></div>
        <div><span>2</span><strong>回到原始来源</strong></div>
        <div><span>3</span><strong>分类 hard / banked / conditional</strong></div>
        <div><span>4</span><strong>锁定预测与结果</strong></div>
      </div>
    </section>

    <section>
      <h2>当前概率表</h2>
      <p class="note">证据截止时间说明预测者最多只能看到该时间以前的信息。</p>
      <div class="tableWrap"><table><thead><tr><th>预测者</th><th>未来24小时</th><th>未来7天</th><th>证据截止</th></tr></thead><tbody>{probability_rows}</tbody></table></div>
    </section>

    <section class="two" id="scores">
      <div>
        <h2>已经揭晓的预测</h2>
        <p class="note">结果为 1 表示 24 小时内发生。误差越小，说明当时的概率判断越贴近结果。</p>
        <div class="tableWrap"><table><thead><tr><th>预测者</th><th>签发时间</th><th>当时猜24h</th><th>结果</th><th>误差</th><th>类型</th></tr></thead><tbody>{score_rows_html}</tbody></table></div>
      </div>
      <div id="history">
        <h2>历史演练榜</h2>
        <p class="note">full 是完整历史窗口；limited 是少量回放点。先看样本量，再看误差。</p>
        <div class="tableWrap"><table><thead><tr><th>#</th><th>预测者</th><th>覆盖</th><th>N</th><th>平均误差</th><th>惩罚大错</th><th>相对基础模型</th></tr></thead><tbody>{leaderboard_rows}</tbody></table></div>
      </div>
    </section>

    <section class="caseFile">
      {autopsy_html}
    </section>

    <section class="panel">
      <h2>评分为什么有说服力？</h2>
      <p class="note">概率预测不能只看“猜中了没有”。一个报 55% 的人和一个报 99% 的人，即使都猜对了，承担的风险也不一样。</p>
      <div class="scoreExplainer">
        <div><strong>Brier：离结果有多远</strong>结果发生记为 1，没发生记为 0。预测 40% 后发生，误差就是 0.6 的平方。</div>
        <div><strong>Log Loss：惩罚过度自信</strong>如果把几乎不可能的事说成 99%，一旦错了会被重罚。</div>
        <div><strong>覆盖率：不能挑题</strong>样本量越多，越能看出一个预测者是不是真的稳定。</div>
      </div>
    </section>

    <section>
      <h2>赛季制竞猜会长什么样？</h2>
      <div class="seasonBoard">
        <article class="season"><span>玩家</span><strong>看校准</strong><p class="note">敢押高概率也要承担误差，长期稳定比蒙中一次更重要。</p></article>
        <article class="season"><span>LLM</span><strong>看分歧</strong><p class="note">同一份证据，不同模型会怎样权衡新公告和冷却期。</p></article>
        <article class="season"><span>Crowd</span><strong>看群体</strong><p class="note">匿名提交后再展示分布，减少被当前模型数字锚定。</p></article>
        <article class="season"><span>统计模型</span><strong>看基准</strong><p class="note">用简单、可复现的规则作为所有判断的参照系。</p></article>
      </div>
    </section>

    <section>
      <h2>历史故事模式</h2>
      <div class="storyStrip">
        <article class="story"><h3>回到当时</h3><p class="note">只看某个时间点以前的公开证据，再猜未来一天会不会出现 reset。</p></article>
        <article class="story"><h3>揭晓答案</h3><p class="note">窗口结束后展示公告、原因类型和各预测者当时的概率。</p></article>
        <article class="story"><h3>复盘判断</h3><p class="note">比较人、LLM、Crowd 和统计模型，看看谁更稳、谁更敢押。</p></article>
      </div>
    </section>

    <section class="two">
      <div class="panel">
        <h2>最近 reset 公告</h2>
        <ul class="timeline">{timeline_html}</ul>
      </div>
      <div class="panel">
        <h2>最近公开背景信号</h2>
        <ul class="timeline">{context_html}</ul>
      </div>
    </section>

    <section class="panel">
      <h2>怎么看这些指标？</h2>
      <div class="chips">
        <span class="chip">平均误差越小越好</span>
        <span class="chip">N 越大越可信</span>
        <span class="chip">24h 看短线</span>
        <span class="chip">7d 看趋势</span>
        <span class="chip">证据截止表示当时能看到什么</span>
      </div>
      <p class="note">每个数字都来自公开表格、冻结预测或评分记录；想深挖时可以直接打开仓库数据。</p>
    </section>
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
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(html_text, encoding="utf-8")
    # Keep the old path working.
    (OUT / "community.html").write_text(html_text, encoding="utf-8")
    print(f"Built {OUT / 'index.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
