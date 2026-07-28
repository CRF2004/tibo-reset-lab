# 数据字典 v0.1

所有时间使用 ISO 8601 UTC（`YYYY-MM-DDTHH:MM:SSZ`）。空字符串表示未知；真实的 0 必须写 `0`。布尔值只允许 `0` 或 `1`。

## 证据等级

- `primary`：原始官方账号、状态页、产品文档或仓库记录；
- `archived_primary`：原始内容的可核验存档；
- `independent_secondary`：独立二手报道或追踪站；
- `community_report`：单个用户报告；
- `unknown`：尚未评级。

候选事件可以来自二手来源，但进入金标准必须尽力取得 `primary` 或 `archived_primary`。

## 表关系

- `sources.source_id` 是原始证据主键。
- `reset_announcements.source_id` 外键指向 `sources`。
- 历史 X 金标准的 `SRC_X_<post_id>` 由
  `annotation/evidence/historical_x_posts.csv` 提供；它与 `sources` 共同构成来源索引。
- `reset_actions` 是去重后的动作级表。一个公告可产生 hard 和 banked 两个动作，
  多个预告/执行帖子也可通过 `action_cluster_id` 合并为一个动作。
- `reset_confirmations.announcement_id` 指向公告，`source_id` 指向证据。
- `context_events.source_ids` 使用分号连接来源 ID；正式数据库版本将改为关联表。
- `annotation_candidates` 保留两名标注者的独立答案，裁决后才写 processed 表。

字段定义以 CSV 表头为准。枚举与范围由 `scripts/validate_data.py` 执行检查。

## 时间与泄漏

`published_at_utc` 是来源声称的发布时间，`first_observed_at_utc` 是研究管线第一次实际获取时间。回测特征只能在后者之后可用。历史回填资料若无法证明当时已获取，不得伪装成实时可见数据。

## 候选状态

- `unreviewed`：尚未独立标注；
- `needs_primary`：只有二手/社区来源；
- `needs_human_review`：已取得原始来源并完成 LLM 初标，等待人工独立核对；
- `annotated`：已完成双人标注，尚未裁决；
- `accepted`：裁决为正例；
- `rejected`：不满足定义；
- `uncertain`：证据不足，主分析排除。
