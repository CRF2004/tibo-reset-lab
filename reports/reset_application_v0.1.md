# 重置宣布到实际应用：初步兑现审计 v0.1

数据截止：2026-07-28。当前有 20 条公开个案报告：
13 条报告到账且未明确报告机制错误，4 条到账但报告窗口
或 hard/banked 机制不符，3 条报告未成功。

唯一具有精确发布时刻、可计算延迟的到账报告发生在宣布后 32.0 分钟。GitHub
只显示开帖日期的记录统一以当日 12:00 UTC 占位，其延迟不得进入均值、中位数或
生存分析。

| confirmation_id | 成功 | 观察到的变化 | 宣布后分钟 | 原始证据 |
| --- | ---: | --- | ---: | --- |
| CONF_X_2079617200584069200 | 1 | unspecified | 32.0 | [证据](https://x.com/agentic_works/status/2079617200584069200) |
| CONF_GH_28811 | 1 | hard_instead_of_banked | 1030.1（近似，不进入延迟统计） | [证据](https://github.com/openai/codex/issues/28811) |
| CONF_GH_32421 | 0 | timer_changed_but_usage_not_restored | 365.6（近似，不进入延迟统计） | [证据](https://github.com/openai/codex/issues/32421) |
| CONF_GH_33344 | 0 | weekly | 985.1（近似，不进入延迟统计） | [证据](https://github.com/openai/codex/issues/33344) |
| CONF_RD_1RJCWLI_C1 | 1 | weekly | 609.9（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1rjcwli/usage_limit_reset/) |
| CONF_RD_1RJCWLI_C2 | 1 | unspecified | 609.9（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1rjcwli/usage_limit_reset/) |
| CONF_RD_1UUP1E3_C1 | 1 | weekly | 31.0（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1uup1e3/removed/) |
| CONF_RD_1V2GQ77_C1 | 1 | weekly | 72.7（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v2gq77/i_planned_my_usage_around_no_more_resets_until_i/) |
| CONF_RD_1V2GQ77_C2 | 1 | unspecified | 72.7（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v2gq77/i_planned_my_usage_around_no_more_resets_until_i/) |
| CONF_RD_1V2GQ77_C3 | 1 | weekly | 72.7（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v2gq77/i_planned_my_usage_around_no_more_resets_until_i/) |
| CONF_RD_1V43J9T_C1 | 1 | weekly_reset_date_shifted | 2592.7（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v43j9t/so_just_another_reset_while_the_issue_of_usage/) |
| CONF_RD_1V43J9T_C2 | 1 | hard_reset_overwrote_banked_timing | 2592.7（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v43j9t/so_just_another_reset_while_the_issue_of_usage/) |
| CONF_RD_1V6HE1D_C1 | 1 | weekly | 42.8（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v6he1d/reset_is_in/) |
| CONF_RD_1V6HE1D_C2 | 1 | weekly | 42.8（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v6he1d/reset_is_in/) |
| CONF_RD_1V8MEYX_C1 | 1 | weekly | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v8meyx/removed/) |
| CONF_RD_1V8MEYX_C2 | 1 | weekly | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v8meyx/removed/) |
| CONF_RD_1V8M2Z0_C1 | 1 | weekly | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v8m2z0/removed/) |
| CONF_RD_1V8M2Z0_C2 | 0 | none_reported | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1v8m2z0/removed/) |
| CONF_RD_1UU2C1G_C1 | 1 | unspecified | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1uu2c1g/reset_discussion_megathread/) |
| CONF_RD_1UU2C1G_C2 | 1 | hard_reset_did_not_stack_as_banked | 50.6（近似，不进入延迟统计） | [证据](https://www.reddit.com/r/codex/comments/1uu2c1g/reset_discussion_megathread/) |

## 判读

- `applied_successfully=1` 仅表示该报告者观察到了某种额度变化，不代表所有账户到账。
- `hard_instead_of_banked` 是“发生了变化但机制与预期不一致”，不能与完全成功合并。
- `0` 包括额度未恢复、只有计时器变化以及明确遗漏的账户。
- 这些是自选择的公开报告，不能估计总体失败率；其作用是识别兑现延迟和失败模式。
- 原文及中文翻译保存在 `data/raw/confirmation_evidence.csv`。
