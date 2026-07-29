# Tibo Reset Lab

> 不只猜下一次 Codex 额度何时重置：公开概率、证据、理由和最终得分。

Tibo Reset Lab 是一个关于 Codex / ChatGPT Work 特殊额度重置公告的开放预测实验。
它持续整理官方公告、OpenAI Status 事故、产品发布与里程碑，在严格的时间顺序下比较
统计模型、LLM、独立玩家和群体判断。

本项目追踪公开的组织行动，不推断个人性格、私生活或未公开动机，也不是 OpenAI
官方服务。

<!-- LIVE_SNAPSHOT_START -->
## 当前预测快照

**状态：Bootstrap 演示** · 数据更新至 `2026-07-28T09:33:42Z` · 正式成熟预测 `0` 条

> **注意：** 尚无正式 scheduled 轮次。下表来自不同时间的 bootstrap，只展示系统如何工作，不能用于比较高低，也不进入排行榜。

| 预测者 | 未来24小时 | 未来7天 | 证据截止（UTC） |
| --- | ---: | ---: | --- |
| Global event rate | 12.4% | 60.4% | 2026-07-28T07:42:56Z |
| Calendar model | 34.4% | 86.0% | 2026-07-28T07:42:56Z |
| Theory model | 16.4% | 62.6% | 2026-07-28T07:42:56Z |
| DeepSeek V4 Pro | 40.0% | 95.0% | 2026-07-28T09:22:34Z |
| Qwen 3.5 397B | 15.0% | 55.0% | 2026-07-28T09:22:34Z |
| Kimi K2.5 | 8.0% | 35.0% | 2026-07-28T09:22:34Z |
| MiniMax M2.7 | 6.0% | 35.0% | 2026-07-28T09:22:34Z |
| Step 3.5 Flash | 20.0% | 70.0% | 2026-07-28T09:32:59Z |

### 当前已知事实

- 最近一次合格公告：[原始 X 帖](https://x.com/thsottiaux/status/2081940052154933696)，时间 `2026-07-28T03:09:23.666Z`；
- 类型：`hard_global`；原因：`launch_promotion`；
- 距该公告约 `6.4` 小时；
- [查看中文理由、证据与完整 Dashboard](reports/community_dashboard.md)。

概率不是官方消息，也不是“重置倒计时”。Bootstrap、迟交和未成熟结果不进入正式排名。

### 统计预测者历史演练排行榜

口径：v1.2 `cluster_first`，每日 17:00 UTC landmark，24小时窗口；每个预测点只用此前数据。
LLM、玩家和 Crowd 需要当时冻结的上下文提交，暂不纳入历史演练。

| 排名 | 预测者 | N | Brier | Log Loss | Skill vs global |
| ---: | --- | ---: | ---: | ---: | ---: |
| 1 | EWMA half-life 30d | 247 | 0.117336 | 0.391868 | 5.6% |
| 2 | Recent 30-day rate | 247 | 0.117437 | 0.390606 | 5.6% |
| 3 | Two-regime rate | 247 | 0.118392 | 0.398566 | 4.8% |
| 4 | Recent 60-day rate | 247 | 0.118566 | 0.403098 | 4.7% |
| 5 | Calendar model | 247 | 0.121546 | 0.420149 | 2.3% |
| 6 | Same-gap nearest 30 | 247 | 0.122434 | 0.412941 | 1.5% |
| 7 | Calendar model without regime | 247 | 0.123121 | 0.426222 | 1.0% |
| 8 | Global event rate | 247 | 0.124353 | 0.425184 | 0.0% |
| 9 | Discrete renewal hazard | 247 | 0.153615 | 0.489800 | -23.5% |

共同窗口 `2025-11-23T17:00:00Z` 至 `2026-07-27T17:00:00Z`；
正例率 `14.2%`。这是模型开发期历史演练，不替代未来 scheduled 排行榜。
<!-- LIVE_SNAPSHOT_END -->

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
| 主结果：独立决策 cluster | 40 个 |
| 拆分后的额度动作 | 42 个 |
| 官方事故上下文 | 已回填至 2025-09 |
| 历史模型比较 | 17:00 UTC / cluster-first 的 v1.2 历史演练已重建 |
| 前瞻设计 | v1 冻结；v1.1 强基线修订；v1.2 对齐时间与事件单位 |
| 实时比赛 | 数据结构、冻结、Crowd 与评分流程已建立 |
| 正式前瞻样本 | 尚未积累到停止条件 |

v1.2 历史演练中，EWMA half-life 30d 的 Brier Score 为 `0.117336`，略优于近期
30 天事件率的 `0.117437` 和 Calendar M2 的 `0.121546`。这些结果只覆盖可严格回放的
统计预测者；LLM、玩家和 Crowd 需要当时冻结的上下文提交，等待前瞻 scheduled 排名。
详细结果见 [strong_baselines_v1.md](reports/strong_baselines_v1.md)。

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

LLM 组目前包含五个独立席位：DeepSeek V4 Pro、Qwen 3.5 397B、Kimi K2.5、
MiniMax M2.7 和 Step 3.5 Flash。它们分别计分，不并入只包含人类玩家的 Crowd。
选型、失败路由和 bootstrap 记录见
[llm_tournament_v1.md](reports/llm_tournament_v1.md)。

## 数据与可审计性

核心数据位于：

- [`reset_announcements.csv`](data/processed/reset_announcements.csv)：公告级金标准；
- [`reset_actions.csv`](data/processed/reset_actions.csv)：拆分后的 hard/banked 等动作；
- [`announcement_cluster_overrides.csv`](data/processed/announcement_cluster_overrides.csv)：
  先于动作记录出现的 promise 与 action cluster 的显式映射；
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
一条公告包含多个动作时在 action 表拆分。v1.2 主结果按 action cluster 去重，只计算每个
cluster 的首次合格公开承诺；全部公告帖作为次要结果保留。

## 快速开始

环境需要 Python 3。依赖声明在 `requirements.txt`，提交会由 GitHub Actions 自动运行
数据验证、边界测试和 17:00 UTC landmark 构建测试。

```bash
git clone https://github.com/CRF2004/tibo-reset-lab.git
cd tibo-reset-lab
python3 -m pip install -r requirements.txt

# 检查核心数据表
python3 scripts/validate_data.py

# 重建日级/6 小时数据与历史模型结果
python3 scripts/build_person_period.py \
  --start 2025-09-17T17:00:00Z \
  --end YYYY-MM-DDT17:00:00Z \
  --event-unit cluster_first
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
- [时间锚点与事件单位修订 v1.2](preregistration_v1.2_amendment.md)
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

历史 expanding-window 结果是**模型开发结果**，不是完全未见数据上的独立验证。旧 v1
结果还使用了与正式签发不一致的时间锚点，因此不得直接作为 v1.2 的历史对照。真正的
证据只能来自共同 17:00 UTC landmark 下按时冻结、到期后评分的 scheduled 预测。

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
