# 事件裁决协议 v1

## 官方账号范围

主口径只接受：

- `@thsottiaux`；
- OpenAI 官方账号（当前为 `@OpenAI`）。

其他员工、媒体、追踪器和社区帖子只能发现候选或确认实际到账，不能单独构成公告
金标准。账号必须由原始 X URL、oEmbed author 和 snowflake 时间共同核验。

## 公告判定

正例必须明确表示特殊 Codex 用量重置：

- 已承诺；
- 正在执行；
- 或声称完成。

正常个人 5 小时/周窗口刷新、猜测、请求重置、泛化产品更新和没有官方行动文本的
社区到账报告均排除。

## 预告、执行和重复帖子

- 预告本身若有明确承诺，是 announcement event；
- 后续执行帖也是 announcement event，但共享 `action_cluster_id`；
- 动作级分析只计算同一 cluster 中去重后的动作；
- 公告级预测以窗口内首次符合条件的公开声明为结果；
- 单纯转发或重复措辞且没有新增承诺/执行状态，不新增动作。

## 一条帖子包含多个动作

一条帖子可产生一个 announcement_id，但在 `reset_actions.csv` 拆成多行动：

- hard global reset；
- banked credit；
- targeted/conditional；
- extension/multiplier。

因此当前 41 条公告对应 42 条动作。模型预测公告，不把同帖的两个动作计成两个窗口
正例。

## 模糊与裁决

- 证据不足：`uncertain`，主分析排除；
- 只有二手来源：`needs_primary`；
- 与自然刷新无法区分：排除；
- “feeling like a reset”等明确未来意图按 promised 编码；
- 只有庆祝、故障或发布但没有 reset 行动文本：不是结果；
- 原因首次出现在公告本身时，可以解释但不得作为该公告的预测特征。

## 当前一致性证据

历史流程是 LLM 初标加一次人工接受，并非两名相互独立、互盲的人类标注者。因此当前
数据不能合法计算 Cohen's kappa 或 Krippendorff's alpha；把“人工接受 LLM 标注”
当作两名标注者会夸大可靠性。

后续新增候选采用：

1. LLM 按固定 prompt 初标；
2. 人工在不看模型预测和后续窗口结果的情况下独立复核；
3. 分歧进入 adjudication 表；
4. 每累计至少 20 个新候选，报告公告纳入、reset type、status 和 reason type 的
   原始一致率；名义字段报告 Cohen's kappa，有序字段报告加权 kappa；
5. 在达到可解释样本量前只报告分歧计数，不报告不稳定的单一 kappa。

任何未来一致性统计只针对新批次，不能追溯性宣称旧 41 条具有双人独立一致性。
