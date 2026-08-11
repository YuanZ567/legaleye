# LegalEye 法眼 — 系统架构文档（ARCHITECTURE）

> 版本：v1.0
> 日期：2026-08-11
> 状态：定稿（M0 脚手架开工前确认）
> 关联文档：`docs/OPENCODE.md`（计划书）、`docs/PRD.md`（需求）、`docs/DESIGN.md`（前端视觉）
> 读者：项目开发者 + 未来协作的 AI agent。**本文档是架构宪法，与本文档冲突的代码视为缺陷。**

---

## 1. 文档目的与总原则

本文档定义 LegalEye 的技术实现约束：**技术选型、目录边界、分层与依赖方向、LLM 引用机制、开发红线、验收标准**。任何代码改动不得违反"第 8 章 禁止破坏项"。

三条总原则：
1. **分层清晰胜过灵活**：api → services → 领域能力 → models，依赖单向向下，禁止反向。
2. **AI 调用可观测、可降级、可追溯**：每次 LLM 调用必须记账；失败必须降级而非崩溃；结论必须带条款引用。
3. **国内部署、数据不出境**是产品合规性本身，也是技术约束（默认模型路由国内）。

---

## 2. 技术栈定稿

| 层 | 选型 | 版本 | 说明 |
|---|---|---|---|
| 后端语言 | Python | 3.11+ | 类型注解强制 |
| Web 框架 | FastAPI | 0.111+ | 异步 + 自动 OpenAPI 文档 |
| 多智能体编排 | LangGraph | 0.2+ | 状态图 + create_react_agent（工具型 Agent） |
| LLM 调用 | langchain-openai / langchain-anthropic | 0.1+ / 0.1+ | ChatOpenAI（百炼/DeepSeek/OpenAI 兼容）+ ChatAnthropic |
| 任务队列 | Celery + Redis | 5.4+ / 7.2+ | 审查任务异步执行，SSE 进度经 Redis 桥接 |
| 数据库 | PostgreSQL + pgvector | 16 + 0.7+ | 自托管 Docker；业务 + 法规/案例向量 |
| 文档解析 | PyMuPDF / python-docx | 1.24+ / 1.1+ | PDF / Word |
| 图算法 | networkx | 3.3+ | 数据流图谱构建 + 可达路径推理 |
| 加密 | cryptography（Fernet） | 42+ | API Key 加密存储 |
| 前端 | React + Vite + TypeScript | 18 / 5 / 5.5 | strict 模式 |
| UI | Tailwind CSS + shadcn/ui | 3.4 / latest | 颜色/圆角 token 按 DESIGN.md |
| 图谱/画布 | @xyflow/react（React Flow v12） | 12.x | 编排画布 + 数据流图谱复用 |
| 图表 | echarts + echarts-for-react | 5.5+ / 3.0+ | 仪表盘 |
| 状态管理 | zustand | 4.x | 前端全局状态 |
| 包管理 | uv（Python）/ pnpm（前端） | latest / 9+ | 锁文件 uv.lock / pnpm-lock.yaml |
| 迁移 | Alembic | 1.13+ | 数据库版本管理 |
| 代码质量 | ruff + black / eslint + prettier | latest | CI 强制 |
| 测试 | pytest / Vitest | 8+ / 2+ | 单元/集成/E2E |
| CI | GitHub Actions | — | trunk-based，PR 必过 |
| 部署 | Docker Compose | 2.x | 本机开发 / 轻量服务器一键起 |
| 可观测 | loguru + Sentry | 0.7+ / 2+ | 结构化日志 / 错误上报（免费层） |

---

## 3. 目录结构（Monorepo）

```
/legaleye
├── backend/
│   ├── app/
│   │   ├── api/            # FastAPI 路由（薄层：参数校验 + 调 services，禁止业务逻辑）
│   │   ├── core/           # 配置(pydantic-settings) / 鉴权(JWT) / 依赖注入 / 常量
│   │   ├── services/       # 业务逻辑：任务管理 / 报告生成 / 加密 / 声明键对齐 / 限流
│   │   ├── agents/         # LangGraph 工作流图定义 + 10 智能体节点 + 反思循环
│   │   ├── tools/          # Agent 工具（每工具一函数 + JSON schema 注解）
│   │   ├── graph/          # 数据流图谱构建(networkx) + 推理规则引擎 R1-R4
│   │   ├── llm/            # ChatModel 工厂（provider 路由 + Key 解密 + token 记账）
│   │   ├── rag/            # 文档加载/分块/清洗 + pgvector 检索（法规库/案例库）
│   │   ├── knowledge/      # 法条基线入库 / 版本管理 / SCC 模板解析
│   │   ├── tasks/          # Celery 任务定义（审查/联合审查/入库）
│   │   ├── models/         # SQLModel ORM 实体（见计划书第十五章）
│   │   ├── schemas/        # Pydantic v2 请求/响应模型
│   │   ├── prompts/        # 提示词集中管理（禁止散落字符串）
│   │   └── utils/          # Fernet 加密 / loguru 日志 / diff 生成
│   ├── alembic/            # 数据库迁移
│   ├── tests/              # pytest：unit/ + integration/
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/          # 登录/任务列表/审查工作台/报告/模型配置/知识库/设置/404
│   │   ├── components/     # shadcn 基础件 + 专属组件(RiskBadge/ClauseRef/DiffView/GraphCanvas/ChatStream/StatCard/TaskStatusBar)
│   │   ├── api/            # 后端 REST 封装（axios/fetch）
│   │   ├── store/          # zustand stores
│   │   ├── hooks/          # useSSE / useTaskPolling 等
│   │   ├── styles/         # globals.css（设计 token，见 DESIGN.md 14.2）
│   │   └── lib/            # 工具（格式化/图谱数据映射）
│   ├── package.json
│   └── Dockerfile / nginx.conf
├── scripts/                # ingest_laws.py / evaluate.py / deploy.sh / seed_demo.py
├── data/                   # 运行时数据（不入库）
│   ├── golden/             # 金标集（30 单文档 + 10 多文档 + 标注 JSON）
│   └── raw_laws/           # 法条原始文本（GB/T 版权文本仅私有，禁止提交 git）
├── infra/                  # docker-compose.yml / .env.example / nginx/ / sentry/
├── docs/                   # 计划书/PRD/DESIGN/ARCHITECTURE/AGENTS.md
├── .github/workflows/      # ci.yml（lint+test）/ deploy.yml
└── .gitignore
```

---

## 4. 数据来源与知识库工程

### 4.1 法规基线库（RAG 主库，M2 前置核心）
| 来源 | 内容 | 落地方式 |
|---|---|---|
| 国家法律法规数据库 flk.npc.gov.cn | PIPL / 数据安全法 / 网安法全文 | 官方检索导出 + 人工校对条款号；禁止高频抓取；存 `data/raw_laws/`，标注来源与版本 |
| 全国信安标委 | GB/T 35273-2020 | 官方文本；**版权文本仅私有库使用，禁止提交 git** |
| 网信办 | 《数据出境安全评估办法》《个人信息出境标准合同办法》+ 官方 SCC 模板 | 官方公开文本 + 模板 PDF 结构化 |

- 入库脚本：`scripts/ingest_laws.py`（结构化源 → `LawBaseline` + pgvector embedding），**幂等可重跑**。
- 条款解析：`第X章 第X条 第X款` → `{statute, article_no, article_text, effective_date, version}`。
- 版本化：法规修订新增版本记录，`effective_date` 生效；报告引用锁定版本。

### 4.2 处罚案例库（P1 增强项）
- 来源：网信办公示执法信息 / 工信部 App 违规通报 / 市场监督总局处罚公示。
- 结构化：`{case_id, facts, violated_articles, penalty, occurred_at}`；遵守 robots 与访问频次。

### 4.3 金标集（评估）
- `data/golden/`：30 份单文档 + 10 组多文档；每份含注入标注 JSON（ground truth）。
- 评估：`scripts/evaluate.py` 输出三层指标（见计划书第十三章）。

### 4.4 用户输入（运行时）
- 上传 PDF/Word/URL → 解析清洗分块 → `Document` 表；**原文可选不持久化**（敏感模式仅内存）。

---

## 5. 服务层约定

### 5.1 分层与依赖方向（核心）
```
api（路由薄层）
  ↓ 调用
services（业务逻辑：任务/报告/加密/对齐/限流）
  ↓ 调用
agents（LangGraph 工作流）│ tools（Agent 工具）│ rag │ knowledge │ graph │ llm
  ↓ 依赖
models（ORM 实体）│ schemas（Pydantic）
```
硬性规则：
- **依赖单向向下**：上层可 import 下层；**下层禁止 import 上层**（如 models 不得 import services）。
- `api/` 只做：参数校验、鉴权、调用 services、异常转 HTTP；**禁止写业务逻辑、禁止直连 DB/LLM**。
- `services/` 是业务编排层：一个 service 函数 = 一个用例；可调用多个领域能力（agents/tools/rag/...）。
- `agents/` 是唯一允许定义 LangGraph 图与智能体节点的地方；图结构变更需更新编排画布映射。
- `models/` 只定义 ORM 与迁移；查询逻辑放 services 或专属 repository（`services/repositories/`）。
- 所有 LLM 调用必须经 `llm/` 工厂（见第 6 章），**禁止在 services/agents 里直接 `import openai` 裸调**。

### 5.2 命名与异常约定
- Python：`snake_case`；模块名小写；service 函数用动词（`create_review_task`、`generate_report`）。
- 异常：自定义异常体系 `core/exceptions.py`（`NotFoundError / ValidationError / LLMError / RateLimitError / ForbiddenError`），api 层统一 Handler 转 HTTP 状态码；**禁止在业务层裸抛 HTTPException**。
- 日志：loguru，统一格式 `logger.info("...", extra={...})`；关键节点记录 task_id + node + tokens。
- 配置：`core/config.py` 基于 pydantic-settings 读 `.env`；**一切密钥只从 env 读**。

### 5.3 数据库访问
- 迁移一律 Alembic；禁止手改库结构。
- 查询集中：写 `services/repositories/` 下的 repository 类；禁止散落原生 SQL。
- 多用户隔离：所有任务/文档查询必须带 `user_id` 过滤（等价 RLS）。

---

## 6. AI 引用机制（LLM 集成约定）

> 本章是"系统如何引用 AI"的宪法：路由、记账、降级、引用格式。

### 6.1 ChatModel 工厂（llm/factory.py）
```python
def get_chat_model(user_id: int, task_ctx: TaskContext) -> BaseChatModel
```
- 路由：`user 有 is_active ModelConfig` → 用户配置；否则 → 系统默认（bailian/qwen-plus）；都没有 → `RateLimitError`（引导配置 Key）。
- Key 解密：Fernet 只在工厂内解密并立即使用，**密文/明文均不得写日志**。
- 工厂返回前注册 `callback`：每次调用写 `LLMCallRecord{task_id, node, provider, model, input_tokens, output_tokens, cost_est, latency_ms}`（token 记账，供仪表盘与限流）。
- provider 映射：bailian/deepseek/openai → `ChatOpenAI(base_url=..., api_key=...)`；anthropic → `ChatAnthropic`。

### 6.2 Agent 工具注册（tools/）
- 每工具 = 一个函数 + `@tool`（LangChain 装饰器）暴露 JSON schema 注解。
- 工具清单（见计划书 9.2）：`retrieve_law_baseline` / `retrieve_enforcement_case`(P1) / `query_dataflow_graph` / `compare_scc_template` / `generate_diff`。
- 工具实现位于 `tools/`，**不得在提示词里内联工具逻辑**；Agent 通过 `create_react_agent` 挂载工具集。
- 工具错误：返回错误信息给 Agent 而非抛异常（Agent 可据此换策略），调用上限 3 次防循环。

### 6.3 提示词管理（prompts/）
- 所有提示词集中 `backend/app/prompts/`（每智能体一个 `.py` 或 `.j2` 模板），禁止字符串散落。
- 提示词必须：明确输出 schema（JSON）、要求"依据检索结果而非记忆"、无命中时输出"待补"而非编造条款号。
- 提示词变更走 PR + 必须跑 `scripts/evaluate.py`（防回归）。

### 6.4 降级与容错（关键）
| 场景 | 行为 |
|---|---|
| 单节点 LLM 超时（60s） | 重试 2 次（指数退避），仍失败 → 该维度输出"待补 + needs_human_review=true"，**不中断任务** |
| 反思循环 | 上限 2 轮，强制结束 |
| 单任务总超时（10 分钟） | 熔断 failed，保留已产出 findings |
| 法规检索无命中 | 结论标记"待补：法规未命中"，**禁止臆造条款号** |
| 模型不可用（Key 失效） | 任务 failed + 明确原因；前端提供重试 |

### 6.5 结论引用格式（不可绕过）
- 任何 `ComplianceFinding` 必须带：`clause_ref`（格式校验见 PRD 第 6 章正则）+ `statute_version` + `confidence` + `needs_human_review`。
- 引用可溯源：`evidence` 字段存原文片段（含 char_range），前端 ClauseRef 组件点击跳知识库原文。

### 6.6 数据不出境
- 默认路由国内模型（百炼）；用户显式切境外 provider 时前端提示 + 任务记录 `data_residency` 标记。

---

## 7. 开发约束

### 7.1 代码规范
- Python：ruff（E/F/I + docstring 基础）+ black；类型注解强制（新增函数必须带类型）；Pydantic v2。
- 前端：TS `strict: true`；eslint + prettier；组件用 shadcn 风格。
- 新增依赖必须说明理由（PR 中），锁文件提交。

### 7.2 工程流
- 提交：Conventional Commits（`feat/fix/refactor/docs/test/chore/ci`）。
- 分支：trunk-based；feature 分支 + PR；**PR 必过 CI（lint + 单测 + 构建）**方可合并。
- CI：`.github/workflows/ci.yml` 跑 ruff/black/eslint + pytest + vitest + 前端 build。

### 7.3 测试要求
- 后端：pytest——单元（services/tools 纯逻辑）+ 集成（API + DB + Celery，docker compose 起依赖）；LLM 调用用 mock（`respx`/monkeypatch），**CI 不碰真实模型**。
- 前端：Vitest（组件/工具）+ 关键流程测试；E2E（Playwright，M7 后可加）。
- LLM 质量评估：`scripts/evaluate.py` 单独跑（金标集），**不在 CI 默认跑**（成本），改动 prompts 必须手动跑。

### 7.4 环境与密钥
- `.env` 入 `.gitignore`；提供 `infra/.env.example`（全量变量清单）。
- 密钥只经 `core/config.py` 读取；**任何代码不得硬编码 Key**。

### 7.5 AI 协作约定（给未来协作 AI）
- 先读 `docs/` 四份文档 + 本文件再动手；与文档冲突的改动视为缺陷。
- 改动影响架构（新增目录/依赖方向/表结构/提示词）→ 同步更新对应文档。
- 默认实现路径：改代码 → 跑 lint/单测 → 提交 → PR。

---

## 8. 禁止破坏项（架构红线，违反即退 PR）

1. **禁止绕过服务层**：api 直连 DB / 直调 LLM / 直写文件存储。
2. **禁止反向依赖**：下层 import 上层（如 models import services）。
3. **禁止裸调 LLM**：一切模型调用必须走 `llm/factory.py`（保证记账与路由）。
4. **禁止无引用结论**：AI 产出无 `clause_ref` 的"不合规"结论。
5. **禁止硬编码密钥**：Key/密码只能来自 `.env`。
6. **禁止破坏数据不出境**：默认路由国内模型；境外切换必须有提示与记录。
7. **禁止提交私有数据**：`data/raw_laws/`（含 GB/T 版权文本）与 `.env` 不得进 git。
8. **禁止跳过 Alembic 改库**：表结构变更必须走迁移。
9. **禁止破坏分层目录**：新代码必须落入第 3 章对应目录；例外需架构文档更新。
10. **禁止跳过记账**：任何 LLM 调用路径必须产生 `LLMCallRecord`（仪表盘/限流依赖）。
11. **禁止在 services/agents 内联提示词字符串**：必须入 `prompts/`。
12. **禁止破坏 SSE 契约**：SSE 事件类型（PRD F4 六类）变更必须同步前端 hook 与文档。

---

## 9. 验收标准

### 9.1 M0 脚手架验收（开工即验）
- [ ] `cd infra && docker compose up -d` 一键拉起 Postgres(pgvector)/Redis/MinIO/后端/前端
- [ ] 健康检查：`GET /health` 返回 DB/Redis 连通状态；前端首页可访问
- [ ] `uv sync` / `pnpm install` 后 lint + 单测全绿
- [ ] Alembic 初始化迁移可执行；`.env.example` 覆盖全部环境变量
- [ ] CI（GitHub Actions）首次运行通过

### 9.2 模块验收（随里程碑）
| 模块 | 验收要点 |
|---|---|
| knowledge | `ingest_laws.py` 幂等入库；条款号解析正确率（金标法条抽查 100%） |
| rag | 法规检索 Top-5 命中相关条款（抽查）；无命中返回空而非幻觉 |
| llm | 工厂四 provider 可路由；每调用生成 LLMCallRecord；mock 下 CI 通过 |
| agents | 10 节点状态图可运行；工具调用记录完整；反思循环 ≤2 轮 |
| graph | R1-R4 推理输出符合 PRD F6；图谱 JSON 与前端渲染一致 |
| services | 任务状态机 queued→running→done/failed 无非法跳转；异常转 HTTP 正确 |
| frontend | DESIGN.md 自查清单 9 条全过；四栏工作台联动；SSE 六类事件消费正常 |

### 9.3 质量验收（M10）
- [ ] 三层评估指标达成（实体 F1 ≥0.85 / 关系 F1 ≥0.80 / 高风险召回 ≥90% / 误报 ≤15% / 引用准确率 ≥85% / 交叉矛盾检出率 ≥80%）
- [ ] 40 份金标集 evaluate 报告输出 `docs/eval_report.md`

---

## 10. 变更流程

- 架构变更（技术栈/目录/依赖方向/红线）→ 更新本文档并 bump 版本；PR 描述中注明"ARCHITECTURE 变更"。
- 新增外部依赖 → PR 说明理由；红线新增 → 全员知悉（docs 更新 + 同步 AGENTS.md）。
