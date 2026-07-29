# Tibo Reset Lab

> 用公开证据估计：未来一天或一周内，Codex / ChatGPT Work 会不会再次出现特殊额度重置公告。

Tibo Reset Lab 是一个关于 Codex / ChatGPT Work 特殊额度重置公告的开放预测实验。
它持续整理公开公告、OpenAI Status 事故、产品发布和里程碑，然后让不同预测者给出
概率。等结果发生后，再按同一规则算误差。

本项目追踪公开的组织行动，不推断个人性格、私生活或未公开动机，也不是 OpenAI
官方服务。

<!-- LIVE_SNAPSHOT_START -->
## 现在各预测者怎么猜？

**状态：Bootstrap 演示** · 数据更新至 `2026-07-29T07:48:47Z` · 已完成的正式预测 `0` 条

> **注意：** 尚无正式定时轮次。下表来自不同时间的 bootstrap，只展示系统如何工作，不能用于比较高低，也不进入排行榜。

下面的百分比可以按字面理解：`40%` 约等于“10 次类似情况里，模型认为会发生 4 次”。
`证据截止` 表示预测者只能看到这个时间以前的信息。

| 预测者 | 未来24小时 | 未来7天 | 证据截止（UTC） |
| --- | ---: | ---: | --- |
| Global event rate | 12.0% | 59.2% | 2026-07-29T05:05:00Z |
| Recent 30-day rate | 40.6% | 95.5% | 2026-07-29T05:05:00Z |
| Renewal model | 22.5% | 69.6% | 2026-07-29T05:05:00Z |
| Calendar model | 34.5% | 84.1% | 2026-07-29T05:05:00Z |
| Theory model | 17.7% | 61.2% | 2026-07-29T05:05:00Z |
| DeepSeek V4 Pro | 25.0% | 97.0% | 2026-07-29T07:45:50Z |
| Qwen 3.5 397B | 35.0% | 80.0% | 2026-07-29T07:45:50Z |
| Kimi K2.5 | 8.0% | 35.0% | 2026-07-29T07:45:50Z |
| MiniMax M2.7 | 25.0% | 58.0% | 2026-07-29T07:45:50Z |
| Step 3.5 Flash | 28.0% | 72.0% | 2026-07-29T07:45:50Z |

### 已知事实

- 最近一次合格公告：[原始 X 帖](https://x.com/thsottiaux/status/2082317452755751098)，时间 `2026-07-29T04:09:02.000Z`；
- 类型：`hard_global`；原因：`launch_promotion`；
- 距该公告约 `3.7` 小时；
- [查看中文理由、证据与完整 Dashboard](reports/community_dashboard.md)。

概率不是官方消息，也不是“重置倒计时”。Bootstrap、迟交和未成熟结果不进入正式排名。

### 已经揭晓的演示预测

`标签=1` 表示签发后 24 小时内确实又出现了合格 reset 公告，`标签=0` 表示没有。
`误差` 越小越好：预测 40% 后真的发生，误差是 `(1 - 0.40)^2 = 0.36`。

| 预测者 | 签发时间 | 当时猜24h | 结果 | 误差 | 类型 |
| --- | --- | ---: | ---: | ---: | --- |
| Step 3.5 Flash | 2026-07-28T09:38:00Z | 20.0% | 1 | 0.6400 | bootstrap |
| Qwen 3.5 397B | 2026-07-28T09:30:00Z | 15.0% | 1 | 0.7225 | bootstrap |
| MiniMax M2.7 | 2026-07-28T09:30:00Z | 6.0% | 1 | 0.8836 | bootstrap |
| Kimi K2.5 | 2026-07-28T09:30:00Z | 8.0% | 1 | 0.8464 | bootstrap |
| DeepSeek V4 Pro | 2026-07-28T09:30:00Z | 40.0% | 1 | 0.3600 | bootstrap |
| LLM forecaster | 2026-07-28T08:46:00Z | 12.0% | 1 | 0.7744 | bootstrap |
| Theory model | 2026-07-28T07:42:56Z | 16.4% | 1 | 0.6991 | bootstrap |
| Global event rate | 2026-07-28T07:42:56Z | 12.4% | 1 | 0.7677 | bootstrap |
| Calendar model | 2026-07-28T07:42:56Z | 34.4% | 1 | 0.4306 | bootstrap |

该表来自 tournament 展示层；`bootstrap` 评分用于演示和审计，不进入 scheduled 主分析。

### 历史演练：以前这么猜会怎样？

这张表回答的是：“如果每天固定时间用同一套方法预测下一天，长期误差多大？”
`full` 表示覆盖完整历史窗口；`limited` 表示只跑了少量回放点，不能直接和 full 公平比较。
`N` 是评分次数。`平均误差` 越小越好。`相对基础模型` 为正，表示比最简单的长期平均率更准。

| 排名 | 预测者 | 覆盖 | N | 平均误差 | 惩罚大错 | 相对基础模型 |
| ---: | --- | --- | ---: | ---: | ---: | ---: |
| 1 | Recent 30-day rate | full | 248 | 0.118385 | 0.392663 | 6.8% |
| 2 | EWMA half-life 30d | full | 248 | 0.118941 | 0.395390 | 6.3% |
| 3 | Two-regime rate | full | 248 | 0.119744 | 0.401472 | 5.7% |
| 4 | Recent 60-day rate | full | 248 | 0.120119 | 0.406460 | 5.4% |
| 5 | Calendar model | full | 248 | 0.122875 | 0.422946 | 3.2% |
| 6 | Same-gap nearest 30 | full | 248 | 0.124602 | 0.418026 | 1.9% |
| 7 | Calendar model without regime | full | 248 | 0.124728 | 0.429669 | 1.8% |
| 8 | Global event rate | full | 248 | 0.126972 | 0.432011 | 0.0% |
| 9 | Discrete renewal hazard | full | 248 | 0.155710 | 0.494751 | -22.6% |
| 10 | Step 3.5 Flash | limited | 4 | 0.016425 | 0.136505 | 87.1% |
| 11 | MiniMax M2.7 | limited | 3 | 0.008133 | 0.091030 | 93.6% |
| 12 | Kimi K2.5 | limited | 2 | 0.006400 | 0.083382 | 95.0% |
| 13 | DeepSeek V4 Pro | limited | 2 | 0.014400 | 0.127833 | 88.7% |
| 14 | Qwen 3.5 397B | limited | 2 | 0.018450 | 0.145176 | 85.5% |

共同窗口 `2025-11-23T17:00:00Z` 至 `2026-07-28T17:00:00Z`；
实际发生率 `14.5%`。这是模型开发期历史演练，不替代未来正式排行榜。
暂无可评分 replay：Independent player, Crowd aggregate。
<!-- LIVE_SNAPSHOT_END -->

## 它和普通 reset tracker 有什么不同？

普通 tracker 主要回答“上次什么时候重置”。这个仓库多做一步：把“会不会很快再重置”
变成可以事后检验的概率预测。

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
| 历史官方公告 | 42 条 |
| 主结果：独立重置事件 | 41 个 |
| 拆分后的额度动作 | 43 个 |
| 官方事故上下文 | 已回填至 2025-09 |
| 历史模型比较 | 每天 17:00 UTC 预测下一天的历史演练已重建 |
| 前瞻设计 | v1 冻结；v1.1 强基线修订；v1.2 对齐时间与事件单位 |
| 实时比赛 | 数据结构、冻结、Crowd 与评分流程已建立 |
| 正式前瞻样本 | 尚未积累到停止条件 |

历史演练中，目前表现最好的是“近期 30 天事件率”：简单说，就是看最近 30 天有多频繁，
再把这个频率当成明天会发生的概率。它的平均误差是 `0.118385`，略低于
EWMA 的 `0.118941` 和 Calendar 模型的 `0.122875`。这些结果只是历史回放；真正可信的
排名要等未来按时锁定、到期后评分的正式预测积累起来。
详细结果见 [strong_baselines_v1.md](reports/strong_baselines_v1.md)。

正式比较至少需要同时达到：

- 180 个有效正式日级轮次；
- 20 个 24 小时前瞻阳性。

在此之前，Dashboard 只展示概率、证据、覆盖率和描述性表现，不宣布“最佳模型”。

几个常见词的意思：

- `bootstrap`：演示或试运行，用来检查流程能不能跑通，不算正式比赛。
- `scheduled`：提前约定时间、按时锁定的正式预测。
- `独立重置事件`：同一次重置可能先发预告、再发完成公告；主结果只算一次。
- `平均误差`：概率预测的平方误差，越小越好。
- `惩罚大错`：对“很自信但猜错”的预测惩罚更重，也越小越好。

## 预测者

| 预测者 | 作用 |
| --- | --- |
| Global event rate | 只看长期平均多久发生一次 |
| Recent 30-day rate | 只看最近 30 天有多频繁 |
| Renewal M1 | 看“距离上次公告已经过了多久” |
| Calendar M2 | 再加入星期、月份和政策阶段 |
| Theory M3-lite | 再加入当时公开的官方事故和产品事件 |
| LLM forecaster | 阅读同一份冻结公开上下文并给出理由 |
| Independent player | 截止前提交的个人概率判断 |
| Crowd aggregate | 至少三名玩家判断的平均组合 |

所有预测都在结果发生前记录时间、证据截止点和文件指纹。Bootstrap、迟交、无效签发
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
  把“先预告、后执行”的帖子明确归到同一次独立重置事件；
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
一条公告包含多个动作时会在 action 表拆分。主结果按“独立重置事件”去重：同一次重置的
预告和完成帖只算一个事件；全部公告帖仍作为次要结果保留。

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

不要只看“谁排第一”。如果某个预测者只跑了 2 次，即使两次都猜对，也不能说明它长期更准。
还要看 `N`、覆盖范围、是否正式锁定、以及有没有在不同时间段持续表现稳定。

历史演练是“用过去训练、预测后一天、再对答案”的开发结果，不等于真正的未来验证。
真正有说服力的证据，只能来自以后每天按时锁定、到期后评分的正式预测。

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
