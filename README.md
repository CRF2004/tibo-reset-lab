# Tibo Reset Lab

> 不只猜下一次 Codex 额度何时重置：公开概率、证据、理由和最终得分。

Tibo Reset Lab 是一个关于 Codex / ChatGPT Work 特殊额度重置公告的开放预测实验。
它持续整理官方公告、OpenAI Status 事故、产品发布与里程碑，在严格的时间顺序下比较
统计模型、LLM、独立玩家和群体判断。

本项目追踪公开的组织行动，不推断个人性格、私生活或未公开动机，也不是 OpenAI
官方服务。

## 它与普通 reset tracker 有什么不同？

普通 tracker 主要回答“上次什么时候重置”。本项目还尝试回答：

- **未来 6 小时、24 小时和 7 天发生重置的概率是多少？**
- **概率为什么变化？哪些证据支持，哪些证据反对？**
- **近期事件率、时间间隔、日历、事故信号、LLM 和人类，长期谁判断得更好？**
- **公告是否真的应用到账？hard reset 与 banked reset 是否一致？**
- **预测在发出前是否冻结，还是看完结果后才调整？**

计划中的公众体验还包括概率竞猜、Crowd 聚合、Tibo 发帖监测、中文提醒、提前 6 小时
预警和每次预测的事后复盘。产品构想见
[PUBLIC_PRODUCT_IDEAS.md](PUBLIC_PRODUCT_IDEAS.md)。

## 当前状态

| 项目 | 状态 |
| --- | --- |
| 历史官方公告 | 41 条 |
| 独立额度动作 | 42 个 |
| 官方事故上下文 | 已回填至 2025-09 |
| 历史模型比较 | M0–M3-lite 与强朴素基线已完成 |
| 前瞻设计 | v1 冻结，v1.1 在首个正式样本前修订 |
| 实时比赛 | 数据结构、冻结、Crowd 与评分流程已建立 |
| 正式前瞻样本 | 尚未积累到停止条件 |

历史回测中，近期 30 天事件率的 Brier Score 为 `0.119664`，优于 Calendar M2 的
`0.125443`。因此本项目不声称复杂模型已经胜出；这也是把强朴素基线放进正式比赛的
原因。详细结果见 [strong_baselines_v1.md](reports/strong_baselines_v1.md)。

正式比较至少需要同时达到：

- 180 个有效 scheduled 日级轮次；
- 20 个 24 小时前瞻阳性。

在此之前，Dashboard 只展示概率、证据、覆盖率和描述性表现，不宣布“最佳模型”。

## 预测者

| 预测者 | 作用 |
| --- | --- |
| Global event rate | 最弱参考基线 |
| Recent 30-day rate | 强朴素自适应基线 |
| Renewal M1 | 距上次公告的时间间隔规律 |
| Calendar M2 | 时间间隔、太平洋时间日历和冻结政策阶段 |
| Theory M3-lite | 预测时已经公开的官方事故、强度与注意力 |
| LLM forecaster | 阅读同一份冻结公开上下文并给出理由 |
| Independent player | 截止前提交的个人概率判断 |
| Crowd aggregate | 至少三名有效玩家的等权 logit pool |

所有预测都在结果发生前记录时间、证据截止点和 SHA-256。Bootstrap、迟交、无效签发
和事后补填不进入正式排名。

## 数据与可审计性

核心数据位于：

- [`reset_announcements.csv`](data/processed/reset_announcements.csv)：公告级金标准；
- [`reset_actions.csv`](data/processed/reset_actions.csv)：拆分后的 hard/banked 等动作；
- [`context_events.csv`](data/processed/context_events.csv)：事故、发布、里程碑和注意力；
- [`historical_x_posts_bilingual.csv`](annotation/evidence/historical_x_posts_bilingual.csv)：
  原帖与中文翻译；
- [`forward_forecasts_v1.csv`](data/processed/forward_forecasts_v1.csv)：冻结模型预测；
- [`tournament_forecasts.csv`](data/processed/tournament_forecasts.csv)：统一比赛预测；
- [`reset_confirmations.csv`](data/processed/reset_confirmations.csv)：公告是否实际应用的证据。

历史数据采用 **LLM 初标 + 人工核查接受**，不是两名独立人工标注者，因此当前不能
诚实报告 Cohen’s κ。完整边界和未来双人协议见
[EVENT_ADJUDICATION_PROTOCOL_V1.md](annotation/EVENT_ADJUDICATION_PROTOCOL_V1.md)。

第三方 feed 只用于发现候选；进入金标准前必须回到原始 X 帖或官方 OpenAI 来源核验。
一条公告包含多个动作时在 action 表拆分，但公告级预测只计一次事件。

## 快速开始

环境需要 Python 3，以及用于模型脚本的 `numpy` 和 `scikit-learn`。

```bash
git clone https://github.com/CRF2004/tibo-reset-lab.git
cd tibo-reset-lab

# 检查 23 张核心数据表
python3 scripts/validate_data.py

# 重建日级/6 小时数据与历史模型结果
python3 scripts/build_person_period.py \
  --start 2025-09-17T00:00:00Z \
  --end 2026-07-29T00:00:00Z
python3 scripts/build_daily_context_features.py
python3 scripts/build_6h_dataset.py
python3 scripts/rolling_6h_models.py --data-cutoff YYYY-MM-DDTHH:MM:SSZ
```

签发一次冻结预测：

```bash
python3 scripts/issue_task7_forecast.py \
  --issued-at YYYY-MM-DDT17:00:00Z \
  --schedule-class scheduled
python3 scripts/sync_tournament_models.py
python3 scripts/score_mature_forecasts.py
python3 scripts/score_tournament.py
python3 scripts/build_community_dashboard.py
```

每日自动化和完整命令见 [forecasts/README.md](forecasts/README.md)。Windows 计划任务安装
脚本位于 [`automation/install_windows_tasks.ps1`](automation/install_windows_tasks.ps1)。

## 研究入口

- [完整研究报告](研究报告.md)
- [冻结前瞻协议 v1](preregistration_v1_frozen.md)
- [首个正式样本前修订 v1.1](preregistration_v1.1_amendment.md)
- [论文草稿 PDF](output/pdf/tibo_forecasting_protocol_draft.pdf)
- [模型比较](reports/model_comparison_v1.md)
- [强基线分析](reports/strong_baselines_v1.md)
- [Bootstrap 敏感性](reports/bootstrap_sensitivity_v1.md)
- [统计功效分析](reports/power_analysis_v1.md)
- [社区预测协议](community/README.md)
- [玩家与审计教程](community/PLAYER_AND_AUDIT_GUIDE_V1.md)
- [当前静态 Dashboard](dashboard/community.html)

## 结果应该如何解读？

低绝对 Brier Score 不自动意味着模型优秀，因为事件在 6 小时尺度很少见。本项目同时
报告事件基准比例、Brier skill、Log Loss、校准、PR-AUC、覆盖率和强基线差异。

历史 expanding-window 结果是时间顺序正确的**模型开发结果**，不是完全未见数据上的
独立验证。真正的证据只能来自未来按时冻结、到期后评分的 scheduled 预测。

## 参与

当前仓库首先是研究与公众产品原型。可以通过 Issue：

- 提交遗漏的官方公告或原始来源；
- 提供可审计的到账/未到账证据；
- 指出中文翻译或事件分类问题；
- 建议可视化、竞猜或提醒渠道；
- 报告可复现性问题。

请勿提交账户 token、登录凭据、私聊记录或包含个人敏感信息的截图。

## 免责声明

这是独立研究项目，与 OpenAI 无隶属或背书关系。所有概率都是实验性估计，不保证额度
重置，也不应作为购买、工作排期或账户操作的唯一依据。
