# 双人标注与裁决工作区

本目录用于执行：

```text
原始证据冻结 → LLM 初标 → 人工 A 独立核对
                         → 人工 B 独立核对
                         → 自动生成分歧 → 人工裁决
```

LLM 是预标注者，不算“两名人工标注者”之一。人工 A、B 应分别复制
`templates/human_review_template.csv`，独立填写且在提交前不查看对方答案。

## 当前文件

- `GUIDELINES.md`：完整标注标准和边界案例
- `LLM_PROMPT.md`：可复用的模型提示词和输出约束
- `evidence/x_primary_sources.csv`：原始 X URL、帖子 ID、UTC 时间和可见文本
- `evidence/historical_x_posts.csv`：45 条历史相关帖的完整 oEmbed 抓取表
- `evidence/oembed_raw/`：逐帖冻结的原始 oEmbed JSON
- `llm/llm_annotations_v1.csv`：Codex 完成的第一轮 LLM 初标
- `llm/historical_llm_annotations_v1.csv`：全历史 45 条 LLM 分类与动作去重
- `HISTORICAL_COVERAGE.md`：完整性、总数口径与待裁决项
- `HUMAN_REVIEW_TUTORIAL.md`：人工 A/B 从准备到裁决的完整操作教程
- `evidence/historical_x_posts_bilingual.csv`：45 条可读英文摘录、中文翻译和翻译备注
- `automated_evidence_audit.py`：代替人工检查作者、URL、ID、时间和快照
- `evidence/objective_audit.csv`：客观字段自动审计结果
- `templates/human_review_shortlist.csv`：仅含 6 组主观分歧的精简核对表
- `templates/human_review_template.csv`：人工 A/B 核对模板
- `templates/historical_human_review_template.csv`：45 条全历史人工核对模板
- `adjudication/adjudication.csv`：最终裁决表，当前留空
- `REVISION_LOG.md`：候选表修正和证据追溯日志

## 建议流程

1. 人工核对者先阅读 `GUIDELINES.md`。
2. 打开原始 URL；如 X 不可访问，检查证据表中的 oEmbed 文本，但将
   `source_access` 标成 `oembed_only`。
3. 人工可参考 LLM 初标，但应先形成自己的判断；更严格的做法是完成个人表后再看 LLM。
4. 两份人工表完成后，按 `candidate_id` 比较所有核心字段。
5. 只有分歧项进入裁决；裁决者写明依据，不能只写“采用 A”。
6. 裁决为 `accept` 的事件才可写入 `data/processed/reset_announcements.csv`。

生成分歧队列：

```bash
python3 annotation/compare_reviews.py \
  annotation/human/human_a.csv \
  annotation/human/human_b.csv
```

## 版本原则

证据、LLM 标注、人工标注和裁决只追加新版本，不覆盖旧版本。来源被编辑或删除时，
在来源表更新状态并保留既有提取文本。

证据表中的 `normalized_excerpt_not_verbatim` 是便于标注的规范化摘录，不应当作逐字
引文；逐字核对以 `canonical_url` 和 X oEmbed/存档为准。长帖的截断状态已单列。
