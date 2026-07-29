# 前瞻研究协议 v1.2 修订：时间锚点与事件单位

修订日期：2026-07-29  
基础协议：`preregistration_v1_frozen.md`、`preregistration_v1.1_amendment.md`  
适用条件：本修订只有在首个有效 `scheduled` 签发前合并时才进入 v1 序列；若合并时已经存在有效 `scheduled` 样本，则从独立 v2 序列开始，不回写既有预测。

## 修订原因

代码审计发现两项会影响历史训练与正式前瞻比较的一致性：

1. 历史日级 person-period 使用 `00:00 UTC` 窗口，而正式预测固定在 `17:00 UTC`，使训练标签和正式 24 小时目标的时间锚点不一致；
2. 历史结果把每条合格公告帖作为事件，可能将同一重置决策的预告和执行帖视为两个事件。

这两项问题在仓库检查时尚未产生有效 scheduled 样本。既有 bootstrap 仅为运行演示，继续排除于正式评分。

## 1. 统一时间锚点

历史训练与正式预测均使用每日 `17:00:00 UTC` landmark：

- 特征截止：`t = 17:00 UTC`；
- 24 小时标签窗口：`(t, t + 24h]`；
- 恰好位于 `t` 的事件属于已知历史，不属于未来标签；
- 恰好位于 `t + 24h` 的事件属于该窗口；
- 只允许完整 24 小时历史窗口进入训练；
- scheduled 签发要求最新训练窗口恰好结束于签发时刻。

所有 Calendar、renewal、近期事件率和理论特征均在该共同 landmark 数据上重建。旧的 `00:00 UTC` 历史回测保留为开发记录，但不再与 v1.2 前瞻序列直接比较。

## 2. 主事件单位

主结果改为：

> 每个 `action_cluster_id` 中最早出现的、通过裁决的公开重置承诺或执行公告。

记为 `cluster_first`。这更接近“一个新的重置决策首次公开”，避免同一行动的 promise、in-progress 和 claimed-done 帖重复贡献多个主事件。

次要结果 `announcement_post` 保留全部合格公告帖，用于回答“未来是否会再出现相关帖子”，但不作为 v1.2 主模型评分标签。

## 3. 显式映射

大多数公告通过 `reset_actions.csv` 获得 cluster。只有先于后台动作记录出现的 promise 需要进入 `announcement_cluster_overrides.csv`。覆盖表必须包含理由和置信度，不能按日期自动推断；任何 accepted 公告若没有 cluster 映射，数据验证和签发必须失败关闭。

当前显式覆盖将 2026-06-16 的 24 小时内重置承诺与 2026-06-18 报告的 double reset 放在同一 cluster，置信度标记为 medium。该映射在敏感性分析中应单独报告。

## 4. 评分与锁定

- `issue_task7_forecast.py`、`score_mature_forecasts.py` 和 `score_tournament.py` 使用同一 `cluster_first` 构造函数；
- 锁文件增加 `event_unit=cluster_first`；
- 输入哈希加入 `reset_actions.csv`、覆盖表和共享事件单位代码；
- 结果来源哈希由公告表、动作表和覆盖表共同生成；
- 既有 bootstrap 不因标签口径变化而升级为正式预测。

## 5. 报告要求

首次 v1.2 历史重建必须同时报告：

- cluster-first 主结果的事件数和 prevalence；
- announcement-post 次要结果；
- 17:00 对齐前后的标签差异；
- 6月16日/18日映射取同一 cluster 与分开计算的敏感性；
- 所有基线和 M1–M3-lite 在共同新窗口上的完整重跑结果。

v1.1 的强基线要求、停止规则、block bootstrap 和“不提前宣布冠军”规则保持不变。
