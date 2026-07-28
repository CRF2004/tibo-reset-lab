# 任务 7：前瞻预测锁定与评分协议 v2

## 正式签发

固定签发时点为每日 `17:00:00 UTC`。在完成当天来源采集、金标准更新及验证后运行：

```bash
python3 scripts/validate_data.py
python3 scripts/issue_task7_forecast.py \
  --issued-at YYYY-MM-DDT17:00:00Z \
  --schedule-class scheduled
```

每次同时锁定全局 M0、rolling-30/60、EWMA、two-regime rate、离散
KM/renewal、same-gap、M2 和 M3-lite 的 24 小时与 168 小时预测。签发器：

- 只用签发前已经结束的完整日窗口训练；
- 保存签发时的官方事故特征与 7 个逐日 hazard；
- 保存四张输入表和签发脚本的 SHA-256；
- 向 `forward_forecasts_v1.csv` 追加索引；
- 在 `locked_v1/` 生成拒绝覆盖的 JSON。

如果 17:00 前的数据采集未完成，当日应记录为缺失签发，不得事后回填成 17:00
预测。`bootstrap` 仅用于建制测试，不进入正式 scheduled 主分析。

## 到期评分

在更新并核验金标准公告表后运行：

```bash
python3 scripts/score_mature_forecasts.py
```

评分器只处理已经到期且从未评分的预测，使用 `(issued_at, window_end]` 边界，将结果
追加到 `forecast_outcomes_v1.csv`。锁定预测及其概率永不修改。结果同时保存当时公告
表的 SHA-256，以便未来发现漏标时进行审计；更正必须另建修订记录，不能覆盖原分数。

`forecast_exclusions_v1.csv` 保存无效运行。无效锁文件和索引仍保留，但评分器跳过。

## 冻结模型与 v1.1 修订

- M0：Beta(1,1) 平滑的 expanding historical daily rate；
- M2：`log1p(days_since_last)` + PT 星期、周末、月周期、制度，L2 logistic，
  `C=0.25`；
- M3-lite：`log1p(days_since_last)` + 预测安全官方事故状态、48 小时解决状态、强度、
  注意力和 72 小时年龄，L2 logistic，`C=0.25`。
- 强基线：最近 30/60 日 Beta 平滑率、30 日 half-life EWMA、两阶段 rate、相同整数
  gap 的离散 renewal hazard、gap 最近 30 个历史风险集。

由于 scheduled 样本仍为 0，`preregistration_v1.1_amendment.md` 在前瞻序列开始前
将 rolling-30 提升为 M2 的主要参照。任务 7 期间不根据新分数修改这些特征或参数。

## 停止和正式比较规则

第一次正式前瞻比较必须同时达到：

1. 至少 180 个有效 scheduled 日；
2. 至少 20 个 24 小时前瞻正例。

正式比较按模型和 horizon 分开报告 Brier、Log Loss、校准和 7/14/21 日 paired
block bootstrap。bootstrap、排除运行及缺失签发不计入主分析，但单独披露。
