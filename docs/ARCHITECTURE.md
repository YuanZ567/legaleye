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

## 3. 目录结构（Monorepo · 2026-09-22 校准）

```
legaleye/                                  # 项目根目录
│
├── backend/                               # 后端服务：FastAPI + LangGraph + Celery（Python 3.14 + uv）
│   ├── app/
│   │   ├── main.py                        # FastAPI 应用入口（含 lifespan：users 表自动补列）
│   │   ├── api/                           # HTTP 接口层（11 个路由模块）
│   │   │   ├── auth.py                    #   注册/登录 + 账户管理（改资料/改密码/忘记密码重置）
│   │   │   ├── oauth.py                   #   第三方 OAuth 登录（GitHub）
│   │   │   ├── documents.py               #   文档上传（multipart：PDF/Word/Markdown/TXT）
│   │   │   ├── models.py                  #   模型配置（增/删/激活/连通性测试，admin）
│   │   │   ├── tasks.py                   #   审查任务（创建/详情/删除/SSE 进度流）
│   │   │   ├── reports.py                 #   合规报告（JSON + Markdown 导出）
│   │   │   ├── knowledge.py               #   法条知识库（入库/查询/检索）
│   │   │   ├── graph.py                   #   数据流图谱查询
│   │   │   ├── user_api_key.py            #   用户自有 API Key（Fernet 加密存库）
│   │   │   ├── health.py                  #   健康检查
│   │   │   └── errors.py                  #   全局异常处理（统一 {error:{code,message}}）
│   │   ├── agents/                        # ★ 智能体层（审查核心，禁随意改动）
│   │   │   ├── workflow.py                #   LangGraph 工作流（D1-D6 并行 → Critic → 反思 ≤2 轮）
│   │   │   ├── dimension_agent.py         #   六维审查节点 + 三道防线
│   │   │   │                              #   （证据锚定闸门 → 要件核查/合规豁免 → 高危规则兜底）
│   │   │   ├── critic.py                  #   交叉检查（跨维度一致性，规则引擎）
│   │   │   └── tools.py                   #   法条检索/图谱查询工具
│   │   ├── core/                          # 核心基础设施
│   │   │   ├── config.py                  #   配置（infra/.env 加载）
│   │   │   ├── db.py / security.py        #   数据库会话 / Fernet 加解密
│   │   │   ├── auth.py                    #   JWT 签发与校验（Fernet 加密 token）
│   │   │   ├── sse.py                     #   SSE 事件桥（Redis List；nodeEnd 同步写进度队列）
│   │   │   ├── constants.py / enums.py / exceptions.py
│   │   ├── graph/                         # 数据流图谱（规则抽取 → 构建 → R1-R4 推理）
│   │   ├── knowledge/                     # 知识库（pgvector 语义检索 + 法条管理）
│   │   ├── llm/
│   │   │   └── factory.py                 # ★ LLM 工厂（唯一出口；7 家供应商路由 + 记账 + 重试退避）
│   │   ├── models/                        # ORM：user/document/law_baseline/model_config/review_task/report
│   │   ├── prompts/                       # 提示词集中管理（base 公共纪律 + d1~d6 六维要件清单）
│   │   ├── schemas/                       # 数据契约层（validators.py 为 LLM 输出强校验）
│   │   ├── services/                      # 业务服务层（14 个：task/document/report/model/auth/oauth/
│   │   │                                  #   user_api_key/rate_limit/embedding/crossdoc/graph 等）
│   │   ├── tasks/
│   │   │   ├── celery_app.py              #   Celery 实例（Redis broker）
│   │   │   └── review_task.py             #   ★ 审查任务（跑工作流→落库→报告；进度跟踪线程；失败降级）
│   │   └── utils/parsers.py               # PDF/Word/Markdown/HTML 文本解析
│   ├── tests/                             # 40 个 pytest 测试文件
│   │   └── fixtures/                      # 证据闸门回归语料（真实证据基线 + 精选违规证据）
│   ├── alembic/                           # 数据库迁移（11 个版本）
│   ├── Dockerfile                         # uv sync --no-dev 构建；uv run --no-sync 启动（离线可起）
│   └── .venv/                             # 本地虚拟环境（不入库）
│
├── frontend/                              # 前端：React 19 + Vite + TS + Tailwind + shadcn/ui + ReactFlow
│   ├── src/
│   │   ├── api/                           # 后端接口封装（auth/documents/tasks/models/reports/graph/
│   │   │                                  #   knowledge/userApiKey + client 统一 fetch + types 契约）
│   │   ├── components/                    # MainLayout（导航+账户管理弹窗）/ ChatPanel / Dashboard /
│   │   │                                  #   OrchestrationCanvas / GraphCanvas / ReportView 组件族 / ui
│   │   ├── pages/                         # 9 个页面：Login（三模式）/ Workbench（新建审查+四栏联动）/
│   │   │                                  #   TaskList / ReportView / GraphPreview / ModelConfig /
│   │   │                                  #   ApiKeySettings / KnowledgeBase / OAuthCallback
│   │   ├── hooks/useSSE.ts                # SSE 进度流订阅
│   │   ├── lib/ styles/ styles/globals.css # 工具函数 / 设计令牌（公文卷宗主题：暖纸+墨色+朱砂红）
│   ├── dist/                              # 构建产物（Dockerfile 直接 COPY，改前端后需先 pnpm build）
│   ├── Dockerfile / nginx.conf            # nginx 托管 dist + /index.html 禁缓存 + API/SSE 反代
│   └── node_modules/                      # pnpm 依赖（不入库）
│
├── data/                                  # 评估语料（全部为真实文档，带来源 URL + 抓取日期头注）
│   ├── real/                              # 12 份真实隐私政策（淘宝/京东/微信/SHEIN/Temu/美团/支付宝/
│   │                                      #   抖音/拼多多/速卖通/Amazon/eBay）
│   └── real_contracts/                    # 10 份官方合同（EU SCC×2、中国标准合同、英国 IDTA、
│                                          #   AWS/Google/Microsoft/Shopify/Stripe/PayPal DPA）
│
├── docs/                                  # 项目文档（12 个）
│   ├── ARCHITECTURE.md / DATA_CONTRACT.md / DESIGN.md / PRD.md / TODO.md / OPENCODE.md
│   ├── blind_eval_report.md               # ★ 12 份真实隐私政策盲测（误报 0/12）
│   ├── blind_eval_results.json            # 盲测原始数据（证据闸门回归基线的来源）
│   ├── contract_eval_report.md            # ★ 10 份官方合同盲测 + 70 项判定人工复核（误报 0/10）
│   ├── contract_eval_results.json         # 合同盲测原始数据
│   └── eval_report.md + eval_results.json # 历史记录：合成金标回归基准（已标注弃用作效果证明）
│
├── scripts/                               # 工具脚本（6 个）
│   ├── blind_eval.py                      # ★ 真实语料盲测（复用生产工作流，与线上链路一致）
│   ├── evaluate.py                        # 合成金标评估（语料已删，运行会提示重建方式）
│   ├── gen_golden.py                      # 合成金标生成器（可重建已删除的金标语料）
│   ├── ingest_laws.py                     # 法条入库（→ LawBaseline + pgvector，幂等可重跑）
│   ├── init_model_config.py               # 模型配置初始化
│   └── wait_and_eval_modelscope.py        # 魔搭免费额度恢复探针 + 自动续跑
│
├── infra/                                 # docker-compose.yml（postgres/redis/minio/backend/worker/frontend）
├── outputs/                               # 导出文件目录
├── .github/workflows/ci.yml               # CI
├── .workbuddy/memory/                     # AI 协作记忆（不入库）
└── start_full_stack.bat                   # 本地一键启动
```

> 语料说明：合成金标语料（原 data/golden，40 份脚本生成文档）已于 2026-09-22 弃用删除
> ——它仅作为回归测试基准，不作为效果证明；删除后证据闸门回归改由
> `backend/tests/fixtures/` 中的真实证据基线（28 条）+ 精选违规证据（7 条）承载。
> 真实效果评估以 docs/ 下两份盲测报告为准。

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
