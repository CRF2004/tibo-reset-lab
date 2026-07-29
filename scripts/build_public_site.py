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

    probabilities_json = json.dumps(
        [{"name": row["name"], "p24": row["p24"], "p168": row["p168"]} for row in rows],
        ensure_ascii=False,
    )

    probability_rows = "\n".join(
        f"<tr><td>{esc(row['name'])}</td><td>{pct(row['p24'])}</td><td>{pct(row['p168'])}</td><td>{esc(row['cutoff'])}</td></tr>"
        for row in rows
    )
    score_rows_html = "\n".join(
        f"<tr><td>{esc(row['name'])}</td><td>{esc(row['issued'])}</td><td>{pct(row['prob'])}</td><td>{esc(row['label'])}</td><td>{row['brier']:.4f}</td><td>{esc(row['kind'])}</td></tr>"
        for row in scored[:12]
    ) or "<tr><td colspan='6'>暂无成熟评分</td></tr>"
    leaderboard_rows = "\n".join(
        f"<tr><td>{index}</td><td>{esc(row['name'])}</td><td>{esc(row['coverage'])}</td><td>{row['n']}</td><td>{row['brier']:.6f}</td><td>{row['log_loss']:.6f}</td><td>{(1 - row['brier'] / global_brier):.1%}</td></tr>"
        for index, row in enumerate(leaderboard, 1)
    )

    max_p = max((row["p24"] or 0 for row in rows), default=0)
    min_p = min((row["p24"] for row in rows if row["p24"] is not None), default=0)
    hero_p = max_p

    html_text = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Crect width='64' height='64' rx='12' fill='%232563eb'/%3E%3Cpath d='M14 39h9l6-16 8 24 6-14h7' fill='none' stroke='white' stroke-width='5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E">
  <title>Tibo Reset Lab</title>
  <style>
    :root {{ color-scheme: light; --ink:#18212f; --muted:#5d6675; --line:#d9dee8; --bg:#f7f8fb; --panel:#ffffff; --blue:#2563eb; --green:#15803d; --amber:#b45309; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font:16px/1.55 system-ui,-apple-system,Segoe UI,sans-serif; color:var(--ink); background:var(--bg); }}
    header {{ background:#111827; color:white; padding:36px 20px 30px; }}
    .wrap {{ max-width:1180px; margin:0 auto; }}
    .eyebrow {{ color:#b7c4d8; font-size:14px; margin:0 0 8px; }}
    h1 {{ margin:0; font-size:clamp(32px,5vw,58px); line-height:1.04; letter-spacing:0; }}
    .lead {{ max-width:780px; margin:16px 0 0; color:#d7deea; font-size:18px; }}
    main {{ padding:24px 20px 56px; }}
    section {{ margin:22px auto; max-width:1180px; }}
    h2 {{ margin:0 0 10px; font-size:24px; }}
    .grid {{ display:grid; grid-template-columns:repeat(12,1fr); gap:16px; }}
    .panel {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:18px; }}
    .heroCard {{ grid-column:span 5; }}
    .chartCard {{ grid-column:span 7; }}
    .stat {{ font-size:56px; line-height:1; font-weight:750; margin:10px 0; }}
    .subtle {{ color:var(--muted); }}
    .facts {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-top:14px; }}
    .fact {{ border-left:4px solid var(--blue); padding:10px 12px; background:#f8fbff; }}
    table {{ width:100%; border-collapse:collapse; background:white; border:1px solid var(--line); border-radius:8px; overflow:hidden; }}
    th,td {{ padding:10px 12px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ background:#eef2f7; font-weight:650; }}
    td:nth-child(n+2), th:nth-child(n+2) {{ text-align:right; }}
    .note {{ color:var(--muted); margin:8px 0 14px; }}
    .bars {{ display:flex; flex-direction:column; gap:10px; }}
    .bar {{ display:grid; grid-template-columns:160px 1fr 56px; align-items:center; gap:10px; }}
    .track {{ height:14px; background:#e5e7eb; border-radius:999px; overflow:hidden; }}
    .fill {{ height:100%; background:var(--blue); }}
    .chips {{ display:flex; flex-wrap:wrap; gap:8px; margin-top:12px; }}
    .chip {{ border:1px solid var(--line); background:white; border-radius:999px; padding:6px 10px; color:var(--muted); }}
    .two {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
    footer {{ border-top:1px solid var(--line); padding:24px 20px; color:var(--muted); }}
    a {{ color:var(--blue); }}
    @media (max-width: 850px) {{ .heroCard,.chartCard {{ grid-column:1 / -1; }} .two,.facts {{ grid-template-columns:1fr; }} .bar {{ grid-template-columns:120px 1fr 48px; }} table {{ font-size:14px; }} }}
  </style>
</head>
<body>
  <header>
    <div class="wrap">
      <p class="eyebrow">开放预测实验 · 不是官方倒计时</p>
      <h1>未来一天会不会再次重置额度？</h1>
      <p class="lead">我们只使用公开证据，让统计模型和 LLM 给出概率。等结果揭晓后，用同一规则计算误差。</p>
    </div>
  </header>
  <main>
    <section class="grid">
      <div class="panel heroCard">
        <h2>当前最高 24h 预测</h2>
        <div class="stat">{pct(hero_p)}</div>
        <p class="subtle">不同预测者的 24h 概率范围：{pct(min_p)} 到 {pct(max_p)}。数据更新至 <code>{esc(data_at)}</code>。</p>
        <div class="facts">
          <div class="fact"><strong>最新公告</strong><br><a href="{esc(latest_url)}">原始 X 帖</a></div>
          <div class="fact"><strong>公告时间</strong><br>{esc(latest_ann['announced_at_utc'])}</div>
          <div class="fact"><strong>距今约</strong><br>{hours_since:.1f} 小时</div>
        </div>
      </div>
      <div class="panel chartCard">
        <h2>预测者分歧</h2>
        <p class="note">40% 可以理解为“10 次类似情况里，预计约 4 次会发生”。</p>
        <div class="bars" id="bars"></div>
      </div>
    </section>

    <section>
      <h2>当前概率表</h2>
      <p class="note">证据截止时间说明预测者最多只能看到该时间以前的信息。</p>
      <table><thead><tr><th>预测者</th><th>未来24小时</th><th>未来7天</th><th>证据截止</th></tr></thead><tbody>{probability_rows}</tbody></table>
    </section>

    <section class="two">
      <div>
        <h2>已经揭晓的演示预测</h2>
        <p class="note">结果为 1 表示 24 小时内确实发生。误差越小越好；bootstrap 是演示评分，不算正式比赛。</p>
        <table><thead><tr><th>预测者</th><th>签发时间</th><th>当时猜24h</th><th>结果</th><th>误差</th><th>类型</th></tr></thead><tbody>{score_rows_html}</tbody></table>
      </div>
      <div>
        <h2>历史演练榜</h2>
        <p class="note">full 覆盖完整历史窗口；limited 只跑了少量回放点，不能和 full 直接比冠军。</p>
        <table><thead><tr><th>#</th><th>预测者</th><th>覆盖</th><th>N</th><th>平均误差</th><th>惩罚大错</th><th>相对基础模型</th></tr></thead><tbody>{leaderboard_rows}</tbody></table>
      </div>
    </section>

    <section class="panel">
      <h2>怎么看这些指标？</h2>
      <div class="chips">
        <span class="chip">平均误差越小越好</span>
        <span class="chip">N 越大越可信</span>
        <span class="chip">bootstrap 只是演示</span>
        <span class="chip">scheduled 才是正式预测</span>
        <span class="chip">概率不是官方消息</span>
      </div>
      <p class="note">这个项目不会读取你的账号额度，也不会预测任何人的私人行为。它只追踪公开公告，并把预测过程和评分公开。</p>
    </section>
  </main>
  <footer><div class="wrap">数据来自仓库 CSV。查看 <a href="../README.md">README</a>、<a href="../reports/community_dashboard.md">Markdown Dashboard</a> 和 <a href="../PUBLIC_PRODUCT_IDEAS.md">产品路线</a>。</div></footer>
  <script>
    const data = {probabilities_json};
    const bars = document.getElementById('bars');
    for (const row of data) {{
      const p = row.p24 ?? 0;
      const el = document.createElement('div');
      el.className = 'bar';
      el.innerHTML = `<div>${{row.name}}</div><div class="track"><div class="fill" style="width:${{Math.max(0, Math.min(100, p*100))}}%"></div></div><div>${{(p*100).toFixed(1)}}%</div>`;
      bars.appendChild(el);
    }}
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
