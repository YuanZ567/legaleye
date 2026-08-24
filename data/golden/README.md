# 金标集（M10-1）

- 30 份单文档（single/g01-g30）+ 10 组多文档（multi/m01-m10，每组 2 份）
- 每份埋 2-4 个违规点 + 1 条合规干扰项（测误报）；多文档组埋 1-2 处交叉矛盾
- 标注引用知识库真实法条（clauseRef 与 LawBaseline 一致）
- 生成：`cd backend && .venv/Scripts/python.exe ../scripts/gen_golden.py`（种子 42 可复现）
- 标注结构：expectedFindings（dimension/verdict/level/clauseRef/descriptionKeywords/evidenceText）+ entities/relations
- 抽查记录见底部

## 抽查记录

- [ ] g01-g10 已抽查
- [ ] m01-m05 已抽查
