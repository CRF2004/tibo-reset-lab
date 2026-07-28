# 方法审阅意见响应 v1

## 1. M0 偏弱：接受

新增 rolling 30/60 日、30 日 half-life EWMA、two-regime rate、离散
KM/renewal hazard 和 same-gap-30。rolling-30 的 Brier 为 0.119664，优于 M2 的
0.125443。原先“M2 最佳”的结论撤回；前瞻主要参照改为 rolling-30。

## 2. Policy regime 自由度：接受

历史 M2 只有两个 regime，分界为 2026-06-11 的首个 banked-reset 公开产品证据。
5 小时限制变化不另设 regime。该边界是在历史开发阶段确定，存在选择偏差。
`M2 without regime` 的 Brier 为 0.127477，必须与原 M2 同时报告。

## 3. 历史模型选择：接受

历史 expanding-window 只保证逐点时间顺序，不提供未见数据上的模型选择验证。论文
现将全部历史成绩称为 model-development diagnostics；只有 v1.1 后的 scheduled
序列属于前瞻证据。

## 4. 停止条件：接受并修订

旧 OR 规则撤回。v1.1 要求至少 180 个有效 scheduled 日且至少 20 个 24h 阳性。
粗略 block-variance 计算表明识别 0.004 Brier 差可能需要 777–2548 日，说明 180/20
也不是功效保证。正式结果以效应量和区间为中心，不把不显著解释为等价。

## 5. 稀有性依赖尺度：接受

六小时正例率约 3.8%，日级为 14.919%。论文不再笼统称日级结果为稀有事件。强基线
报告同时给出 prevalence、Brier skill、校准截距/斜率、PR-AUC 和 Log Loss。

## 6. 标注协议：接受并澄清限制

新增公开裁决协议，说明官方账号、预告/完成去重、action cluster、同帖多动作和模糊
事件规则。历史数据是 LLM 初标加人工接受，不是两名独立人类标注，因此不能计算有效
的 Cohen's kappa 或 Krippendorff's alpha。未来批次将保留独立复核分歧，并在至少
20 个新候选后报告一致性。

## 7. Bootstrap block 敏感性：接受

新增 7、14、21 日 paired block、各 4000 次。M2 对 global M0、M2 对 rolling-60、
六小时 M2 对 M0、M3 对 M2 的区间均未给出稳健单向证据。单条约 315 日序列的区间
仍不稳定，论文已明确这一限制。

## 结论变化

最重要的修订不是“让 M2 更稳健”，而是承认 rolling-30 在历史上更好。当前最合理
的研究问题变为：

> 在完整前瞻序列中，结构化 calendar/renewal 模型能否超过一个强而简单的近期事件率；
> 官方事故特征是否在二者之上提供任何稳定增量？
