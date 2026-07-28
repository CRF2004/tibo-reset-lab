# 玩家提交与结果核查指南 v1

## 1. 玩家如何提交

1. 在 `community_players.csv` 注册稳定的匿名 `player_id`，阅读并接受当前 consent 版本。
2. 只查看轮次截止时已经公开的证据；不得使用私聊、内部消息或截止后信息。
3. 分别给出未来 24 小时和 168 小时至少发生一次合格公告的概率。
4. 概率必须在 0.001–0.999；168 小时概率原则上不低于 24 小时概率。
5. 写一至三句理由并列出实际使用的 `evidence_ids`。允许缺报，禁止截止后补报。

示例命令：

```bash
python3 scripts/submit_tournament_forecast.py \
  --round-id ROUND_YYYYMMDDTHHMMSSZ \
  --predictor-id P_PLAYER \
  --participant-id PLAYER_001 \
  --horizon-hours 24 \
  --probability 0.18 \
  --evidence-ids "ANN_X_...;CTX_..." \
  --rationale "最近事件率较高，但刚发生一次重置。"
```

同一轮次、同一玩家、同一窗口只能有一条记录。提交后生成 JSON 锁文件和
SHA-256；更正必须另留审计记录，不能覆盖原文件。

## 2. Crowd 如何形成

- 每个轮次和窗口至少三名状态为 `active` 的独立玩家。
- 只聚合截止前到达且 eligibility 为 `eligible` 的玩家预测。
- 使用等权 logit pooling；统计模型和 LLM 不进入 Crowd。
- 玩家不足时 Crowd 保持缺失，不以模型概率补位。

## 3. 人工如何核查结果

核查分成两个问题，不能混为一谈：

### A. 是否出现合格公告

核查员查看原始官方 X 帖或官方 OpenAI 来源，确认发布时间、账号、文本和链接，
再依照 `annotation/EVENT_ADJUDICATION_PROTOCOL_V1.md` 判断是否进入
`reset_announcements.csv`。预测窗口采用 `(issued_at, window_end]`。

### B. 公告是否实际应用

在 `reset_confirmations.csv` 中逐条记录可验证的账户证据：

- `applied_successfully=1/0`；
- `which_window_changed` 是 five-hour、weekly、banked 或 none；
- 套餐、客户端和地区（能够核实时）；
- 原帖、截图或存档的 `source_id`。

至少满足以下之一才可称为“已观察到应用”：官方完成公告明确描述应用完成；或有
可审计的账户侧前后变化证据。只有转述、投票或无法定位时间的评论不得作为强确认。

## 4. hard 与 banked 一致性

- `hard_global`：当前额度/窗口直接改变；若只增加银行额度，不得判为 hard。
- `banked_credit`：新增可保存信用，不要求当前窗口即时归零。
- 一条公告同时包含两种动作时，在 `reset_actions.csv` 拆成两个 action，并共享
  `action_cluster_id`，避免在公告级预测中重复计为两个事件。
- 公告类型与账户侧表现不一致时，保留公告原标签，在确认表记录实际窗口，并建立
  裁决备注；不得事后修改公告以迁就结果。

## 5. 评分与解释

每条成熟预测报告 Brier 和 Log Loss；汇总时同时报告覆盖率、阳性基准比例以及相对
近期 30 天事件率的 Brier skill。Bootstrap、迟交、无效签发和事后回填都不进入正式
排名。达到至少 180 个有效日级轮次且至少 20 个前瞻阳性之前，不发布“赢家”结论。
