# 人工核对操作教程

适用版本：历史帖子 45 条，LLM 标注 v1

## 一、现在只需人工核对什么

经过自动审计后，人工不再核对作者、URL、帖子 ID、UTC 时间、oEmbed 抓取状态、
快照是否存在或三张表是否对齐。这些由 `automated_evidence_audit.py` 完成。

默认流程只需打开：

`templates/human_review_shortlist.csv`

其中只有 6 组真正需要判断的问题。其余 39 条直接采用 LLM 初标，后续抽样复核即可。

人工需要回答：

1. 这条帖子是否真的宣布了特殊重置？
2. 它是 hard reset、banked reset，还是仅调整限额？
3. 帖子说的是已经完成、正在执行，还是未来承诺？
4. 原因和适用范围是否有原文支持？
5. 它是否与另一条帖子描述同一个后台动作？

LLM 标注只是建议。人工核对者必须能够从英文原文或原始页面中找到依据。

## 二、推荐的精简流程

### 第 1 步：运行客观证据审计

```bash
python3 annotation/automated_evidence_audit.py
```

只有输出 `objective failures=0` 时才能继续。审计内容包括：

- 作者是否为 Tibo 或 OpenAI；
- URL、作者和帖子 ID 是否互相匹配；
- X Snowflake 时间是否精确匹配；
- oEmbed 是否抓取成功；
- 原始 JSON 快照是否存在；
- oEmbed 返回作者和 URL 是否匹配；
- 原文是否非空。

结果写入 `evidence/objective_audit.csv`，不需要人工重复勾选。

### 第 2 步：核对 6 组主观问题

复制精简模板：

```bash
cp annotation/templates/human_review_shortlist.csv \
   annotation/human/human_shortlist_review.csv
```

逐行填写：

- `human_final_choice`
- `human_reason`
- `reviewer_id`
- `reviewed_at_utc`

每组只需打开表中列出的帖子，不需要检查其余帖子。

### 第 3 步：抽样质检

从剩余 39 条中随机抽取约 10%，建议至少 4 条，检查：

- 英文原文是否明确支持 LLM 动作类型；
- 中文翻译是否改变含义；
- 是否误把普通限额提升当成 reset；
- 是否遗漏同帖 banked reset。

抽样全部通过即可接受剩余 LLM 标注；若发现一条核心错误，将抽样扩大到 20%；
若再次发现错误，再进行全量人工检查。

## 三、如需全量复核

只有论文审稿、数据发布前最终审计或抽样失败时，才使用下面的完整流程。

## 四、完整流程准备

每位核对者独立复制一份模板：

```bash
cp annotation/templates/historical_human_review_template.csv \
   annotation/human/human_a.csv

cp annotation/templates/historical_human_review_template.csv \
   annotation/human/human_b.csv
```

人工 A、B 在提交自己的表之前不要查看对方答案。推荐顺序：

1. 先看中英双语证据；
2. 独立填写自己的判断；
3. 再查看 LLM 结果；
4. 记录是否同意 LLM，以及不同意的理由。

需要打开的文件：

- `evidence/historical_x_posts_bilingual.csv`：便于阅读的英文摘录和中文翻译；
- `evidence/historical_x_posts.csv`：未经翻译的 X oEmbed 原文；
- `llm/historical_llm_annotations_v1.csv`：LLM 初标；
- `templates/historical_human_review_template.csv`：人工填写表；
- `GUIDELINES.md`：详细枚举与边界标准。

## 三、逐条核对步骤

### 第 1 步：查看自动审计结果

作者、URL、帖子 ID 和时间已经自动核对。人工只在
`objective_audit.csv` 出现失败时介入调查。

填写 `source_access`：

- `original_opened`：成功打开原始 X 页面；
- `oembed_only`：原始页面打不开，只能核对冻结的 oEmbed；
- `archive_only`：只能通过存档核对；
- `unavailable`：现有证据无法核对。

若作者或帖子 ID 不一致，立即在 `reviewer_notes` 记录，不继续默认接受。

### 第 2 步：只读英文原文

双语表为了可读性去掉了部分媒体短链，并可能展开缩写；中文翻译只用于辅助理解。
证据判断以 `historical_x_posts.csv` 中的 `oembed_text` 和原始 X 页面为准。

特别留意：

- `is_text_truncated=1` 表示 oEmbed 文本末尾被截断；
- 英文末尾出现 `…` 也通常表示长帖不完整；
- 截断部分可能包含重置、范围或原因，不能自行补全；
- 表中媒体链接和图片可能含附加文字，应打开原帖查看。

无法看到关键截断内容时，把结论设为 `uncertain` 或降低置信度。

### 第 3 步：判断是不是重置公告

填写 `llm_decision`：

- `accept_reset_announcement`：明确宣布重置已完成、正在执行或确定会执行；
- `related_limit_change`：只提高倍数、取消短窗口或改变计划，没有 reset；
- `related_policy_signal`：只解释 reset 机制或政策；
- `related_predictive_signal`：只是暗示、愿望或玩笑；
- `related_non_reset`：相关但没有重置或限额动作；
- `uncertain`：证据不足。

可接受的典型措辞：

- `We have reset...`
- `Reset button pressed`
- `will be fully reset in the next hour`
- `rate limit reset incoming`

不能单独接受的典型措辞：

- `I'm feeling like a limit reset`
- `You know what's coming`，但没有确定承诺；
- 用户说自己额度恢复；
- 普通周限额自然刷新。

### 第 4 步：标注状态

填写 `announcement_status`：

- `claimed_done`：帖子声称已执行，例如 `have reset`；
- `in_progress`：正在传播或将在明确短窗口内落地；
- `promised`：明确承诺未来执行，但尚未表示已开始；
- `not_applicable`：不是重置公告。

注意：`lands in the next hour` 不是模糊愿望，而是确定执行中的公告。

### 第 5 步：区分动作类型

填写 `primary_action`：

- `hard_global`
- `banked_credit`
- `targeted_or_conditional`
- `extension_or_multiplier`
- `none`

同一帖子包含多种动作时：

- 主要动作填入 `primary_action`；
- 其他动作写入 `secondary_actions`，用分号分隔；
- 对计数字段分别填 0 或 1。

例子：

```text
full reset + one reset into the bank
```

应填写：

```text
primary_action = hard_global
secondary_actions = banked_credit
new_hard_reset_actions = 1
new_banked_reset_actions = 1
```

### 第 6 步：判断是否与其他帖子重复

`action_cluster_id` 表示同一个后台动作。最常见的重复形式：

```text
帖子 A：明天会重置
帖子 B：重置按钮已经按下
```

如果 B 只是兑现 A：

- 两条帖子可以都算公告；
- 但只计一个唯一动作；
- A 的 `new_*_actions` 填 0；
- B 的 `new_*_actions` 填 1；
- 两条使用相同 `action_cluster_id`。

如果原文明确说 `another reset`，通常是一个新动作，不能因时间接近而合并。

不要仅凭时间相邻合并。至少需要承诺—兑现、相同事故或明确的上下文关联。

### 第 7 步：标注原因

`reason_type` 只能使用：

- `incident_compensation`
- `milestone_celebration`
- `launch_promotion`
- `community_response`
- `mixed_or_unclear`

只使用帖子正文或时间上早于公告的公开帖子。

例子：

- `after an almost global outage` → `incident_compensation`
- `we reached 10M` → `milestone_celebration`
- `plugins we just launched` → `launch_promotion`
- `there are enough reports` → `community_response`
- `Enjoy the weekend` → 不能据此推断原因，通常是 `mixed_or_unclear`

### 第 8 步：填写范围与不确定性

范围参考：

- `global_all`
- `all_paid`
- `plan_scoped`
- `targeted`
- `unknown`

不要把 `everyone` 自动解释成所有免费及付费用户。若产品当时只对付费计划开放，
应在备注中说明，并保留范围不确定性。

`uncertainties` 应具体写：

```text
长帖截断，无法确认 6M 原因是否在原文中。
```

不要只写：

```text
不确定。
```

### 第 9 步：与 LLM 比较

完成个人判断后再查看：

`llm/historical_llm_annotations_v1.csv`

填写：

- `agrees_with_llm=1`：所有核心字段一致；
- `agrees_with_llm=0`：至少一个核心字段不同。

不同意时，在 `reviewer_notes` 写清：

```text
LLM 将原因标为 launch_promotion，但原文只有周末庆祝，没有发布信息，
因此人工改为 mixed_or_unclear。
```

## 五、双人全量核对结束后

运行：

```bash
python3 annotation/compare_reviews.py \
  annotation/human/human_a.csv \
  annotation/human/human_b.csv \
  --output annotation/adjudication/historical_adjudication_queue.csv
```

程序只输出存在分歧的候选和字段。

裁决者需要：

1. 重新打开原始证据；
2. 查看两位核对者的理由；
3. 对每个分歧字段给出最终值；
4. 在 `rationale` 中写原文依据；
5. 无法解决时保留 `uncertain`，不能为了得到整齐数据强行选择。

## 六、建议优先复核的帖子

以下项目不应快速勾选：

- `1983973493864894739`：社区历史称其为 reset，但原帖只谈计划和 credits；
- `2031216405266481489` 与 `2031605592352313567`：可能是同一动作的预告与执行；
- `2066956441173323943` 与 `2067399435009622521`：可能属于同一 hard reset 动作；
- `2076365965915467978`：长帖被截断，重置和 6M 信息需要打开全文；
- `2081899343091843463`：只是 “feeling like a reset”，不能当正式公告；
- `2081940052154933696`：动作明确，但原因分类存在歧义。

## 七、完成标准

一份人工表只有同时满足以下条件才算完成：

- 45 行全部核对；
- 没有空的 `reviewer_id`、`reviewed_at_utc` 和 `source_access`；
- 每条都有决策、状态、动作、动作簇和三个动作计数；
- 所有非高置信项目都有具体不确定性说明；
- 与 LLM 不一致的项目都有理由；
- 没有使用中文翻译作为唯一证据。
