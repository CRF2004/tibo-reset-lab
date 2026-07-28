# 五模型 LLM 竞猜建制记录 v1

## 固定阵容

| 预测者 | API 模型名 | 选择理由 |
| --- | --- | --- |
| DeepSeek V4 Pro | `deepseek-v4-pro` | DeepSeek 推理家族代表 |
| Qwen 3.5 397B | `qwen3.5-397b-a17b` | Qwen 大型稀疏模型代表 |
| Kimi K2.5 | `kimi-k2.5` | Moonshot 长上下文推理代表 |
| MiniMax M2.7 | `MiniMax-M2.7` | MiniMax 独立模型家族 |
| Step 3.5 Flash | `step-3.5-flash` | StepFun 推理模型，成本和结构化输出稳定 |

模型列表和价格在 2026-07-28 从 DMXAPI 公开价格页核对。最初测试的 GLM 5.2
连续读取超时，GLM 4.7 又返回无法解析的 JSON，因此没有为了品牌覆盖强行保留不稳定
路由，而改用 Step 3.5 Flash。失败调用不生成预测，也不进入排名。

## 共同协议

- 五个模型读取同一份由公开数据构成的冻结证据包；
- 禁止联网、私有信息和个人心理推断；
- 输出 24h、168h 概率、中文理由、支持证据 ID 和反向证据；
- temperature 固定为 0；
- 分别记录证据截止、API 完成和提交时间；
- 只有实际响应在轮次截止前返回才能进入比赛；
- 每个响应保存证据包哈希和原始响应哈希，不保存 API key。

## Bootstrap 结果

| 模型 | 24h | 168h | 轮次 |
| --- | ---: | ---: | --- |
| DeepSeek V4 Pro | 40% | 95% | 09:30 bootstrap |
| Qwen 3.5 397B | 15% | 55% | 09:30 bootstrap |
| Kimi K2.5 | 8% | 35% | 09:30 bootstrap |
| MiniMax M2.7 | 6% | 35% | 09:30 bootstrap |
| Step 3.5 Flash | 20% | 70% | 09:38 bootstrap |

这些概率只用于验证调用、解析、锁定和展示链路。两个 bootstrap 的证据截止与预测窗口
不同，不能横向判定谁更好，也永久排除正式排行榜。第一个共同 scheduled 轮次开始后，
五个模型才在相同目标窗口上累计 Brier、Log Loss、覆盖率和相对近期30天基线的 skill。

## 自动化

Task-8 preflight 在官方 feed 完整性门通过并开放当日轮次后调用五个模型。LLM 服务故障
不会阻止统计模型的正式签发；缺报保持缺失，后续不回填。重复运行会跳过已经锁定的
模型—轮次组合，避免重复计费。
