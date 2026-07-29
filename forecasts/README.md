# 任务 7：前瞻预测锁定与评分协议 v2

## 正式签发

固定签发时点为每日 `17:00:00 UTC`。历史训练也必须使用相同 landmark：每行特征截止于
17:00 UTC，标签窗口为 `(17:00, 次日17:00]`。在完成当天来源采集、金标准更新及验证后运行：

```bash
python3 scripts/build_person_period.py \
  --start 2025-09-17T17:00:00Z \
  --end YYYY-MM-DDT17:00:00Z \
  --event-unit cluster_first
python3 scripts/build_daily_context_features.py
python3 scripts/validate_data.py
python3 scripts/issue_task7_forecast.py \
  --issued-at YYYY-MM-DDT17:00:00Z \
  --schedule-class scheduled
```

v1.2 主结果是每个 reset action cluster 的首次合格公开承诺或执行公告。全部公告帖是次要
结果，不进入主模型评分。签发器会拒绝以下输入：

- 不是 `cluster_first` 口径的 person-period；
- 历史窗口不是 17:00 UTC landmark；
- scheduled 最新训练窗口没有恰好结束于签发时刻；
- accepted 公告缺少 action cluster 映射。

每次同时锁定全局 M0、rolling-30/60、EWMA、two-regime rate、离散 KM/renewal、
same-gap、M2 和 M3-lite 的24小时与168小时预测。锁文件保存：

- `event_unit=cluster_first`；
- 签发时的官方事故特征与7个逐日 hazard；
- 公告、动作、显式 cluster override、上下文、训练表和代码的 SHA-256；
- 拒绝覆盖的 JSON 和 `forward_forecasts_v1.csv` 索引。

如果17:00前的数据采集未完成，当日记录为缺失签发，不得事后回填。`bootstrap`仅用于
建制测试，不进入正式 scheduled 主分析。

## 到期评分

在更新并核验金标准、action cluster 和显式 override 后运行：

```bash
python3 scripts/score_mature_forecasts.py
python3 scripts/score_tournament.py
```

两个评分器与签发器调用同一个 `scripts/event_units.py`，使用 `(issued_at, window_end]`
边界和 cluster-first 事件。结果来源哈希由公告表、动作表和 override 表共同生成。锁定
概率永不修改；漏标或 cluster 修订必须进入独立 revision 记录。

`forecast_exclusions_v1.csv` 保存无效运行。无效锁文件和索引仍保留，但评分器跳过。

## 冻结模型与修订

- M0：Beta(1,1) 平滑的 expanding historical daily rate；
- M2：`log1p(days_since_last)` + PT 星期、周末、月周期、制度，L2 logistic，`C=0.25`；
- M3-lite：renewal + 预测安全官方事故状态、48小时解决状态、强度、注意力和72小时年龄；
- 强基线：最近30/60日率、30日 half-life EWMA、两阶段 rate、离散 renewal hazard、
  same-gap-30。

v1.1 将 rolling-30 提升为 M2 的主要参照。v1.2 修正历史/前瞻时间锚点不一致，并把
主事件单位从所有公告帖改为首次 cluster 公告。旧的00:00 UTC / announcement-post
回测保留为开发记录，必须在共同新窗口重建后才能与 v1.2 前瞻表现并列报告。

## 停止和正式比较规则

第一次正式前瞻比较必须同时达到：

1. 至少180个有效 scheduled 日；
2. 至少20个24小时前瞻阳性。

正式比较按模型和 horizon 分开报告 Brier、Log Loss、校准和7/14/21日 paired block
bootstrap。bootstrap、排除运行及缺失签发不计入主分析，但单独披露。
