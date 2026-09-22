# LegalEye 法眼

面向中国出海企业的**数据合规智能审查多智能体系统**：多智能体按 PIPL 合规维度并行审查隐私政策 / DPA / SCC 等文件，输出带法规条款可追溯引用、数据流图谱推理、跨文档矛盾检测的结构化合规报告。

## 文档索引（开发前必读）

| 文档 | 内容 |
|---|---|
| `docs/OPENCODE.md` | 项目计划书（业务背景 / 竞品 / 商业模式 / 里程碑） |
| `docs/PRD.md` | 产品需求（F1-F10 功能规格 / 异常清单 / 验收） |
| `docs/DESIGN.md` | 前端视觉设计规范（色板 / 排版 / 组件 / 可视化） |
| `docs/ARCHITECTURE.md` | 系统架构（技术栈 / 分层 / 12 条红线 / 验收） |
| `docs/DATA_CONTRACT.md` | 数据合同（API 契约 / 枚举字典 / 数据分级） |
| `docs/TODO.md` | **开发台账（唯一执行顺序来源，含开发纪律）** |

## 仓库结构

```
backend/    # Python 3.11+ FastAPI + LangGraph + Celery
frontend/   # React 18 + Vite + TS + Tailwind + shadcn/ui + React Flow
scripts/    # 入库 / 评估 / 部署脚本
data/       # 真实评估语料（real/ 12 份隐私政策 + real_contracts/ 10 份官方 SCC/DPA，均带来源 URL）
infra/      # docker-compose.yml / .env.example / nginx
docs/       # 全部文档（真实效果评估：blind_eval_report.md / contract_eval_report.verified.md）
```

## 快速开始（M0 验收）

```bash
cd infra
cp .env.example .env          # 按需修改密钥
docker compose up -d          # 拉起 Postgres(pgvector)/Redis/MinIO/backend/frontend
# 健康检查:  GET http://localhost:8000/health
# 前端:      http://localhost:5173
```

## 开发纪律（详见 docs/TODO.md 第 0 章）

一次只做一个任务 · 严格按 TODO.md 顺序 · 做一步验一步 · 模块完成测试通过即 git 存档 · 写崩直接回滚。
