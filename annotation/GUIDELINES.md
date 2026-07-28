# 标注指南 v1.0

## 1. 标注单位

一个候选单位是“一条公开帖子中可区分的重置动作”。同一帖子包含 hard reset、
banked reset 或临时提高限额时，分别记录：

- `primary_action`：与候选事件对应的主要动作；
- `secondary_actions`：同帖伴随动作，以分号连接；
- 不因同帖含多个动作而复制成两个公告，除非帖子明确宣布两个不同生效时点的动作。

## 2. 是否接受为特殊重置公告

`eligibility_decision`：

- `accept`：官方/负责人明确表示特殊重置已发生、正在传播或确定将发生；
- `reject`：只是自然刷新、愿望、玩笑、模糊暗示、用户传闻或重复转发；
- `uncertain`：原帖不完整、对象/范围无法确定，现有证据不足。

接受必须满足：

1. 对象明确涉及 Codex 或与 ChatGPT Work 共享的 Codex 用量池；
2. 不是个人自然窗口刷新；
3. 文本至少包含已执行、正在执行或确定承诺执行；
4. 有原始官方帖子或可核验存档。

“I’m feeling like a reset”是信号，不是公告；“lands in the next hour”是确定承诺，可接受。

## 3. 公告状态

- `claimed_done`：`have reset`、`has been reset`、`reset button pressed`；
- `in_progress`：`rolling out`、`propagating`、`lands in the next hour`；
- `promised`：明确承诺未来行动，但尚未表示执行已开始。

若同帖同时出现完成和未来动作，针对主要动作编码，并在备注记录未来动作。

## 4. 重置类型

- `hard_global`：后台直接恢复广泛账号的用量；
- `banked_credit`：发放由用户稍后兑换的 reset；
- `targeted_or_conditional`：只针对特定用户、套餐或条件；
- `extension_or_multiplier`：取消短窗口、临时倍增或延长；
- `promise_only`：只有未来承诺，且观察窗内没有对应执行公告。

`banked_credit` 即使只发给部分用户，主类型仍记 `banked_credit`，范围另写
`scope_class=targeted`。

## 5. 原因类型

只根据帖子明确陈述和时间上先于公告的公开上下文：

- `incident_compensation`
- `milestone_celebration`
- `launch_promotion`
- `community_response`
- `mixed_or_unclear`

不要从语气推断原因。“Enjoy the weekend”不是里程碑；“9M active users”是明确里程碑。
如原因主要来自前序帖子，必须填写 `context_source_ids`。

## 6. 范围

`scope_class`：

- `global_all`：明确所有相关用户；
- `all_paid`：所有付费用户/套餐；
- `plan_scoped`：明确若干套餐；
- `targeted`：特定账号集合或资格；
- `unknown`。

`eligible_plans` 和 `quota_windows_affected` 只抄写证据支持的范围。未知不得填 `all`。

## 7. 公告与到账分离

帖子声称重置不等于所有账户到账。此表只标公告。到账证据进入
`reset_confirmations`，并可为成功、失败或部分成功。用户 GitHub issue 不能反向否定
“公告确实发生”，只能影响生效结果。

## 8. 时间

- 主时间取 X post ID 解码所得 UTC 毫秒时间；
- 页面显示日期只作交叉核验；
- 转发时间不能替代原帖时间；
- `first_observed_at` 与 `published_at` 分开。

## 9. 证据质量

- `primary_direct`：可打开原始 X/官方页面并核对文本；
- `primary_oembed`：X oEmbed 返回原帖作者和文本，但页面本体无法读取；
- `archived_primary`：可信存档；
- `secondary_only`：只有报道或追踪站。

`secondary_only` 一般不能直接裁决为 `accept`，除非原帖已删除且有多个独立存档。

## 10. LLM 与人工职责

LLM负责一致地提取字段、指出复合动作和不确定点。人工必须核对：

- 原始 URL、作者和帖子 ID是否匹配；
- 长帖是否被 oEmbed 截断；
- “所有用户”是否其实只指付费计划；
- 原因是否来自结果之后的信息；
- 同一动作是否被转发重复计数；
- banked credit 与 hard reset 是否混淆。

人工不能仅因 LLM `confidence=high` 而跳过证据。

