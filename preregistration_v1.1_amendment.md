# 前瞻研究协议 v1.1 修订

修订时间：2026-07-28T08:15:00Z  
修订时有效 scheduled 签发：0  
基础协议：`preregistration_v1_frozen.md`（永久保留）

## 修订原因

外部方法审阅指出全局 M0 过弱、policy regime 存在研究者自由度，且原 OR 停止规则
可能在阳性不足时过早分析。随后在同一历史共同窗口增加强基线，发现 rolling-30
Brier 为 0.119664，优于 M2 的 0.125443。因此 M2 的历史优势仅相对于弱全局平均，
不能继续称为最佳历史模型。

## 修订内容

1. 每次 scheduled bundle 增加 rolling-30、rolling-60、EWMA half-life 30 日、
   two-regime rate、离散 KM/renewal hazard 和 same-gap-30 基线。
2. 24h 主要预测比较改为 M2 对 rolling-30；M2 对全局 M0 降为兼容性结果。
3. M3-lite 对 M2 保持理论增量比较。
4. 首次正式分析必须同时满足：
   - 至少 180 个有效 scheduled 日；
   - 至少 20 个 24h 前瞻阳性。
5. 7、14、21 天 paired block bootstrap 全部报告；不依据其中最好看的区间选择结论。
6. 历史 policy regime 只有两个阶段，边界为 2026-06-11 首个 banked-reset 公开产品
   证据。该边界在查看历史结果的开发阶段确定，所以含 regime 的历史 M2 有选择偏差。
   `M2 without regime` 必须同时报告。
7. 日级约 15% 阳性不称为严格稀有；“rare event”只用于 6 小时约 3.8% 的尺度或作为
   相对描述。所有结果必须伴随 prevalence、skill、calibration、PR-AUC 和强基线。

该修订发生在首个 scheduled 签发之前，因此适用于完整前瞻序列。bootstrap 运行仍
不进入正式分析。
