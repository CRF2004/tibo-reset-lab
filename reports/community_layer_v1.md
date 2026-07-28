# 社区预测层实施记录 v1

## 已实现的六层

| 层 | 当前落地 |
| --- | --- |
| Research | v1.1 前瞻修订、停止规则和冻结边界 |
| Dataset | 41 条历史公告、42 个动作、版本化上下文与证据 |
| Forecast | M0、M1、M2、M3 及强朴素基线的每日不可变输出 |
| Tournament | 统计模型、固定提示 LLM、独立玩家、Crowd 共用轮次和评分 |
| Audit | 公告事件裁决与账户侧应用确认分离；hard/banked 分开核查 |
| Dashboard | 展示概率、证据、覆盖率和成熟表现；停止条件前不宣称赢家 |

## 最终正式比较

正式表固定包含 Global event rate、Recent 30-day rate、Renewal M1、Calendar M2、
Theory M3-lite、LLM forecaster、Independent player 和 Crowd aggregate。近期 30 天
是主要强朴素参照，全局事件率只作为弱基准。

## 冻结与计分

- statistical forecast 由 Task-8 每日流程签发后同步；
- LLM 使用 `community/LLM_FORECAST_PROMPT_V1.md`，玩家使用同一证据截止；
- Crowd 是至少三名有效玩家的等权 logit pool，不包含模型或 LLM；
- 成熟结果使用接受的公告金标准，窗口定义为 `(签发时刻, 窗口结束]`；
- 排名仅使用 scheduled 轮次，bootstrap 永久排除。

2026-07-28 已完成一次 LLM bootstrap：24h 为 0.12、168h 为 0.58。该轮只验证
锁定和后续评分链路，不进入研究结论。
