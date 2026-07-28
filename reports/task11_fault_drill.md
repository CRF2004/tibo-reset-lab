# 任务 11：自动化故障演练

执行时间：2026-07-28T08:02:36.385035Z。

| 场景 | 结果 | 系统响应 |
| --- | --- | --- |
| fresh_known_signal | PASS | `passed` |
| stale_flag | PASS | `feed_stale` |
| old_feed | PASS | `feed_stale` |
| missing_signal | PASS | `feed_missing_signal` |
| unknown_signal | PASS | `unreviewed_signal:999` |
| revision_does_not_overwrite_original | PASS | `append_only` |
| duplicate_lock_rejected | PASS | `Refusing to overwrite /mnt/c/users/12879/desktop/projects/tibo/forecasts/locked_v1/RUN7_20260728T074256Z.json` |
| off_schedule_rejected | PASS | `Scheduled forecasts must be issued exactly at 17:00:00 UTC` |

演练在临时目录或既有不可覆盖锁上进行，没有创建 scheduled 预测，也没有修改任何
冻结概率。总计 8 项，通过 8 项。

尚不能在无人值守测试中安全模拟的外部条件是 Windows 完全退出登录和网络长期中断；
生产策略是在这种情况下由计划任务结果或 missed-run 审计暴露缺口。
