# 任务 11–15 推进记录

执行日期：2026-07-28。

## 任务 11：故障演练

8/8 项通过：新鲜 feed、stale 标志、31 分钟旧 feed、缺失 signal、未知 signal、
append-only revision、重复锁、非 17:00 scheduled。演练没有签发新的 scheduled
预测，也没有修改冻结概率。

## 任务 12：兑现证据质量

20 条证据完成页面抓取、快照 SHA-256、时间精度和脆弱性审计：

- A 级：1；
- B 级：14；
- C 级：5。

所有社区报告仍缺稳定 reporter identity，因此同一讨论串内的评论不能当作统计独立
样本。只有 A 级精确时间记录进入延迟统计。

## 任务 13：只读看板

看板显示 scheduled 签发、前瞻正例、成熟结果、missed/excluded runs、待审候选和各
模型累计 24h Brier。正式样本目前为 0，未触发停止规则。每日 forecast 与 score
阶段都会刷新看板。

## 任务 14：修订和回放

建立独立 revision 表与追加式协议。隔离回放测试以 `p=0.2` 演示迟到事件把标签从
0 修订为 1、Brier 从 0.04 变为 0.64；原 outcome 文件 SHA-256 在回放前后不变。

## 任务 15：论文材料

使用 claims–evidence 矩阵生成 `PAPER_PLAN.md`，随后形成完整匿名 LaTeX 初稿。初稿
包含摘要、引言、相关工作、数据与协议、历史实验、运行审计、前瞻计划、伦理与局限、
附录和 7 条经 DOI 核验的参考文献。

论文明确将历史结果称为模型开发证据，并写明 scheduled 前瞻结果尚为空。LaTeX
成功编译为 4 页 PDF；所有引用、交叉引用、section input 和 bibliography key
一致，没有 TODO、FIXME、`[VERIFY]` 或作者身份信息。四页渲染检查未见裁切、重叠、
表格越界或不可读字符。

本轮论文审阅为 single-session review；没有调用外部 reviewer MCP。待前瞻停止规则
触发后，应补充成熟结果、图形和独立审稿。

## 验证

- 17 张受控 CSV 表、275 行通过验证；
- 任务 11 故障演练 8/8；
- 任务 14 回放测试通过；
- 论文引用集合与 BibTeX key 完全相等；
- `latexmk` 编译成功。
