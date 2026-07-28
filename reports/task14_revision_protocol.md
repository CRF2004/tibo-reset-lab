# 任务 14：结果修订与回放协议

锁定预测和原始 outcome 永不修改。若后来发现漏标公告、时间修正或来源迟到：

1. 保留 `forecast_outcomes_v1.csv` 原行；
2. 在 `forecast_outcome_revisions_v1.csv` 追加一行；
3. 记录发现时间、旧/新标签、旧/新事件数、旧/新分数、原因和公告表 SHA-256；
4. 主报告同时给出 as-recorded 与 revised sensitivity；
5. 区分“签发时不可知”与“本应采集但漏采”，后者计入数据管线错误；
6. 同一 forecast 的多次修订按 recorded time 排序，不能覆盖前一次修订。

回放测试使用隔离的合成预测：`p=0.2`，原始无事件时 Brier 为 0.04；迟到发现事件后
标签变为 1，修订 Brier 为 0.64。测试必须确认原 outcome 字节不变，仅 revision 表
增加记录。
