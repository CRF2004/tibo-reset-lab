# Tibo Codex 限额重置预测研究

本仓库研究公开情境与 Codex 特殊用量重置公告之间的预测关系。研究对象是公开的组织行动，不是对个人性格或内心动机的推断。

当前状态：**历史标注已晋升为 `gold_v1`；M0–M3-lite 已完成共同窗口滚动比较；
官方事故已回填至 2025-09；6 小时时间片和前瞻锁定协议均已建立；研究设计 v1
已冻结；每日预检、签发和评分已安装为 Windows 计划任务；兑现证据已达 20 条。**

## 目录

- `研究报告.md`：理论与整体研究框架
- `preregistration.md`：在正式标注和回测前冻结的研究决策草案
- `preregistration_v1_frozen.md`：只适用于未来 scheduled 预测的冻结协议
- `preregistration_v1.1_amendment.md`：在首个 scheduled 样本前加入强基线并修订停止规则
- `data/data_dictionary.md`：字段、枚举、缺失值和证据规则
- `data/raw/`：原始来源索引、状态事故回填、兑现证据及快照
- `data/interim/`：候选事件，只用于核验和双人盲标
- `data/processed/`：裁决后的公告、动作、情境、时间片、兑现与预测表
- `scripts/validate_data.py`：检查表结构、枚举、时间和外键
- `scripts/build_person_period.py`：从裁决后的公告构造连续日级时间片
- `scripts/baseline.py`：M0 历史基线与逐日 expanding-window 预测

## 研究状态与使用

候选事件不等于正例。只有完成两名标注者独立标注、来源核验和裁决后，事件才能进入
`data/processed/reset_announcements.csv`。

```bash
python3 scripts/validate_data.py
python3 annotation/automated_evidence_audit.py
python3 scripts/promote_gold.py
python3 scripts/build_person_period.py \
  --start 2025-09-17T00:00:00Z \
  --end 2026-07-29T00:00:00Z
python3 scripts/baseline.py
python3 scripts/descriptive_report.py
python3 scripts/rolling_baselines.py
python3 scripts/m3_lite_diagnostics.py
python3 scripts/collect_status_context.py
python3 scripts/build_context_events.py
python3 scripts/build_daily_context_features.py
python3 scripts/build_6h_dataset.py
python3 scripts/rolling_6h_models.py --data-cutoff YYYY-MM-DDTHH:MM:SSZ
python3 scripts/analyze_confirmations.py
python3 scripts/issue_task7_forecast.py \
  --issued-at YYYY-MM-DDT17:00:00Z --schedule-class scheduled
python3 scripts/score_mature_forecasts.py
python3 scripts/task8_daily_run.py --phase preflight
python3 scripts/task11_fault_drill.py
python3 scripts/audit_confirmation_evidence.py
python3 scripts/build_task13_dashboard.py
python3 scripts/task14_replay_test.py
cd paper && latexmk -pdf main.tex
```

前瞻预测按 `forecasts/README.md` 的协议签发。历史回测结果仍不等于实时预测表现；
只有签发后到期、再按原始锁定概率评分的记录才能回答实时效果。

## 下一阶段工作

1. 按日持续签发并评分锁定预测；
2. 扩充到账成功与失败报告，特别是带精确时间和账户方案的证据；
3. 将任务 6 的 6 小时 M2 与探索性滞后模型转入真正的锁定前瞻验证；
4. 对旧状态页回填中的一个近似起点做二次页面级核验。
