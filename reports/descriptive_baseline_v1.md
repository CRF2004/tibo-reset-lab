# 描述统计与 M0 基线 v1.2

数据版本：`gold_v1`  
观察期：2025-09-17T17:00:00Z 至 2026-07-29T17:00:00Z；日级窗口使用 17:00 UTC landmark 和 `cluster_first` 主口径。

## 样本规模

- 严格公告帖子：42
- 唯一 reset 动作：43
- 日级时间片：315
- 含公告的日级时间片：38
- 事件日占比：12.063%

## 公告间隔

- 间隔数量：41
- 平均间隔：7.68 天
- 中位间隔：3.55 天
- 最短间隔：0.15 天
- 最长间隔：67.74 天

短间隔与长沉寂并存，说明固定历史率只能作为最低基线，M1 应显式建模
`time_since_last_announcement`。

## 按月份

| 类别 | 数量 |
| --- | ---: |
| `2025-09` | 1 |
| `2025-11` | 2 |
| `2025-12` | 4 |
| `2026-03` | 6 |
| `2026-04` | 6 |
| `2026-05` | 3 |
| `2026-06` | 7 |
| `2026-07` | 13 |

## 公告状态

| 类别 | 数量 |
| --- | ---: |
| `claimed_done` | 26 |
| `in_progress` | 12 |
| `promised` | 4 |

## 原因类型

| 类别 | 数量 |
| --- | ---: |
| `community_response` | 1 |
| `incident_compensation` | 19 |
| `launch_promotion` | 6 |
| `milestone_celebration` | 9 |
| `mixed_or_unclear` | 7 |

## 去重动作类型

| 类别 | 数量 |
| --- | ---: |
| `banked_credit` | 5 |
| `hard_global` | 36 |
| `targeted_or_conditional` | 2 |

## 制度时期

| 类别 | 数量 |
| --- | ---: |
| `post_banked_reset` | 19 |
| `pre_banked_reset` | 23 |

## M0 expanding-window 基线

- 评分预测点：314
- 24h Brier Score：0.107598
- 模型：历史日事件率，使用 Beta(1,1) 平滑
- 7d 概率：由当前日 hazard 按常数情景聚合，仅作为基线

M0 不能利用等待时间、日历节律、事故或里程碑，因此后续模型必须在完全相同预测点
上比较，不能改变样本窗口。

## 下一步判定

1. 实现 M1 renewal：仅使用距上次公告时间；
2. 实现 M2 calendar：M1 加星期、PT 时段和月份/制度控制；
3. 使用 expanding-window 滚动预测；
4. 同时报告相对 M0 的 Brier Skill Score；
5. 在 M1/M2 稳定前不拟合 M3 理论模型。
