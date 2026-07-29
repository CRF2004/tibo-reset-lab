# 社区预测 Dashboard

生成时间：2026-07-29T07:49:26Z

> 正式停止条件尚未满足：至少 180 个有效日级轮次且至少 20 个前瞻阳性。以下结果仅用于运行审计和描述，不宣称任何预测者优胜。

## 最新冻结概率

| 预测者 | 窗口(h) | 概率 | 轮次类型 | 证据/来源 |
|---|---|---|---|---|
| Calendar model | 24 | 34.5% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Calendar model | 168 | 84.1% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Global event rate | 24 | 12.0% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Global event rate | 168 | 59.2% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| LLM forecaster | 24 | 12.0% | bootstrap | ANN_X_2081940052154933696;CTX_208194005215493369 |
| LLM forecaster | 168 | 58.0% | bootstrap | ANN_X_2081940052154933696;CTX_208194005215493369 |
| DeepSeek V4 Pro | 24 | 25.0% | bootstrap | ANN_X_2082317452755751098;ANN_X_2081940052154933 |
| DeepSeek V4 Pro | 168 | 97.0% | bootstrap | ANN_X_2082317452755751098;ANN_X_2081940052154933 |
| Kimi K2.5 | 24 | 8.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| Kimi K2.5 | 168 | 35.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| MiniMax M2.7 | 24 | 25.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| MiniMax M2.7 | 168 | 58.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| Qwen 3.5 397B | 24 | 35.0% | bootstrap | ANN_X_2082317452755751098;ANN_X_2081940052154933 |
| Qwen 3.5 397B | 168 | 80.0% | bootstrap | ANN_X_2082317452755751098;ANN_X_2081940052154933 |
| Step 3.5 Flash | 24 | 28.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| Step 3.5 Flash | 168 | 72.0% | bootstrap | ANN_X_2081940052154933696;ANN_X_2082317452755751 |
| Recent 30-day rate | 24 | 40.6% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Recent 30-day rate | 168 | 95.5% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Renewal model | 24 | 22.5% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Renewal model | 168 | 69.6% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Theory model | 24 | 17.7% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |
| Theory model | 168 | 61.2% | bootstrap | 5a43d38475d1fc46f1e909693f21df4b3fe1d53c423aeaaa |

## 正式前瞻表现

有效成熟轮次：0。24 小时阳性状态将在各轮次成熟后累计。

_暂无可报告记录。_

## 比较对象

| 预测者 | 类别 | 作用 |
|---|---|---|
| Global event rate | statistical_model | Weak expanding historical-rate reference. |
| Recent 30-day rate | statistical_model | Strong naive adaptive-rate baseline. |
| Renewal model | statistical_model | Frozen M1 hazard based on log time since the last accepted announcement. |
| Calendar model | statistical_model | Renewal plus Pacific-time calendar cycles and policy indicator. |
| Theory model | statistical_model | Prediction-safe official incident state strength attention and age. |
| LLM forecaster | llm_forecaster | Reads only the frozen public context packet and returns probabilities with rationale. |
| DeepSeek V4 Pro | llm_forecaster | Independent frozen-context forecast through DMXAPI. |
| Qwen 3.5 397B | llm_forecaster | Independent frozen-context forecast through DMXAPI. |
| Kimi K2.5 | llm_forecaster | Independent frozen-context forecast through DMXAPI. |
| Step 3.5 Flash | llm_forecaster | Independent frozen-context forecast through DMXAPI; selected for provider diversity and reliable structured output. |
| MiniMax M2.7 | llm_forecaster | Independent frozen-context forecast through DMXAPI. |
| Independent player | human_player | Individual judgment submitted before the round deadline. |
| Crowd aggregate | crowd_aggregate | Equal-weight logit pool of at least three eligible independent players. |

## 解释边界

- 排名只使用按时冻结、已成熟的 scheduled 轮次；bootstrap 不进入正式比较。
- 玩家缺报保持缺失，不进行事后回填；Crowd 至少需要三名有效独立玩家。
- 同时报告 Brier、Log Loss、覆盖率和相对近期 30 天基线的 skill；样本不足时不作胜负推断。
- Audit 层独立核查公告是否实际应用，以及 hard/banked 行为是否与公告一致。
