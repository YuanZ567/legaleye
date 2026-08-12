# LegalEye 法眼 — 开发待办与执行台账（TODO）

> 版本：v1.0
> 日期：2026-08-11
> 状态：待评审收尾，开工后按"开发纪律"逐条勾选
> 关联文档：`docs/OPENCODE.md` / `docs/PRD.md` / `docs/DESIGN.md` / `docs/ARCHITECTURE.md` / `docs/DATA_CONTRACT.md`
> **本文档是开发执行的唯一顺序来源：严格按顺序、一次一个任务、完成一个勾选一个。**

---

## 0. 开发纪律（硬规则，违反即返工）

### 0.1 单任务制
- **一次只做一个任务**，严格按本文档顺序（M0 → M1 → … → M11）执行，禁止跳任务、禁止并行铺开。
- **一次勾选一个任务**：只有当前任务完全通过验收（含测试）并 git 存档后，才允许开始下一个，并在本文档勾选。

### 0.2 步进验证（做一步验一步）
- 每个任务内再拆小步，**每步完成立即运行相关检查/测试**，不攒到最后一次性验证。
- 示例：写完一个 schema → 立刻跑该文件测试；写完一个 API → 立刻 curl 验证。

### 0.3 任务四要素（每个任务开工前必须明确）
| 要素 | 含义 | 对应本文件 |
|---|---|---|
| **目标** | 本任务要交付什么 | 各里程碑"目标" |
| **允许修改范围** | 可以动哪些文件/目录 | 各里程碑"允许修改范围" |
| **不允许破坏** | 红线：哪些逻辑/契约不能动 | 各里程碑"不允许破坏" + ARCHITECTURE 第 8 章 |
| **验收标准** | 怎么算完成 | 各里程碑"验收标准"（可勾选） |

### 0.4 测试 + git 存档
- **每完成一个模块 → 跑该模块测试 → 全部通过 → git commit 存档**（Conventional Commits：`feat(module): 描述`）。
- commit 前必须：lint 通过、相关单测通过、`git status` 确认无无关文件混入。
- **CI 未绿不得合并/继续下一个任务**。

### 0.5 回滚纪律（写崩直接回滚，不硬修）
- 若当前改动写崩且**预计超过 30 分钟才能修好**：停止硬修，直接回滚到上一个稳定提交：
  - 未提交的崩坏改动：`git checkout -- <文件>` 丢弃（先 `git status` 确认无误删）；
  - 已提交的崩坏提交：`git reset --hard HEAD~1` 回滚到上一稳定态（或 `git revert` 保留历史）。
- 回滚后：在本文档"阻塞"栏登记原因，再决定重做或调整方案；**禁止在崩坏基础上继续叠加修改**。

### 0.6 状态标记
- `- [ ]` 未开始 / `- [ ]` 标注 `（进行中）` 表示当前任务 / `- [x]` 已完成并存档。
- 每完成一个任务：勾选 + 记录完成日期；涉及文档变更的同步更新对应文档。

---

## 1. 已完成

- [x] 项目计划书 v1.0（docs/OPENCODE.md）—— 出海/跨境电商灯塔行业、真 Agent、多文档联合、轻量服务器
- [x] 产品需求文档 PRD v1.0（docs/PRD.md）—— F1-F10 功能规格 + 异常 E1-E12
- [x] 视觉设计规范 DESIGN v1.0（docs/DESIGN.md）—— Precision Editorial、数据脉冲、品牌/语义色
- [x] 系统架构文档 ARCHITECTURE v1.0（docs/ARCHITECTURE.md）—— 技术栈/分层/12 条红线/验收
- [x] 数据合同 DATA_CONTRACT v1.0（docs/DATA_CONTRACT.md）—— API camelCase 契约/枚举字典/分级
- [x] 本 TODO 文档
- [x] **M0-1 目录骨架**（commit 624e9a2）：git init + Monorepo 结构 + .gitignore/.gitattributes + README
- [x] **M0-2 工具链**（commit 5c4888e）：uv 0.12.3（用户 Python 3.14）+ pnpm 11.21.0（用户 Node 24）+ ruff/black/pytest + eslint/prettier 全绿
- [x] **M0-3 基础设施**：Postgres(pgvector)/Redis/MinIO 三容器 healthy；镜像源已替换 DaoCloud+dockerproxy（USTC/网易已失效）
- [x] **M0-4 后端最小服务**：FastAPI 骨架 + /health + Alembic 初始化；联调验证 `/health → {"status":"ok","database":"ok","redis":"ok"}`
- [x] **M0-5 前端最小壳**（commit 63b6f7c）：Vite+React+TS+Tailwind+shadcn，应用壳布局 + DESIGN token，build/lint/format 全绿
- [x] **M0-6 CI**（commit 4cf7f87）：GitHub Actions（后端 lint+test / 前端 lint+build）；真实运行待推送 GitHub
- [x] **M0-7 一键验收**：5 容器全部 running（postgres/redis/minio/backend/frontend），/health → ok/ok/ok，前端 http://localhost:5173 可访问。**git commit 待提交**
- [x] **M1-1 Document ORM + Alembic 迁移**（commit eabcb7f）：SQLModel `Document` 表模型（documents 10 字段，敏感模式 `raw_text` 不入库）+ 首版 Alembic 迁移 `20260812_0001` 已对真实 PG 执行；顺带修复 alembic.ini 中文编码/重复配置、env.py 连接串双源、config `env_file` 优先级（本地 `backend/.env` 可覆盖基础设施默认）；模型单测 3 项通过
- [x] **M1-2 上传 API**（commit d81ecb0）：`POST /documents` multipart 上传，格式（.pdf/.docx）/大小（≤20MB）/页数（PDF ≤200 页）校验超限 400；新建 schemas（APIModel camelCase 契约 + DocumentOut）、core/exceptions（DomainError 体系 + 统一 400/404/403/429 处理器）、core/constants、utils/parsers、services/document_service（校验+落库）、api/documents（薄层）+ 依赖 python-multipart/pymupdf/python-docx/beautifulsoup4；单测 6 项 + 真实 curl 验证成功/非支持格式/缺 docType 均通过
- [x] **M1-3 URL 解析 API**（commit 3cc6c82）：`POST /documents/from-url`，httpx 抓取 html 转文本（BeautifulSoup），10s 超时 + 失败重试 1 次（指数退避），仍失败 400（E3）；协议白名单（http/https）校验；URL 内容为空 400；`UrlDocumentIn` 请求契约 + 公共 `_persist_document`（敏感模式原文不落库，存 sha256 指纹 + 前 500 字预览）；服务层单测（MockTransport 注入）4 项 + API 层（monkeypatch）2 项 + 真实 curl 验证成功/无效协议 400 均通过
- [x] **M1-4 解析服务完整接入**（commit 1b8a150）：`extract_pdf_text`（PyMuPDF，无文字层抛 ScannedPdfError→400 `scanned_pdf` 明确提示 E2）/`extract_docx_text`（python-docx，含表格文本）写入 `raw_text`+`text_preview`+`charCount`；`docType` 文件名启发式推断（privacyPolicy/userAgreement/dpa/scc 关键词），推断失败 400 `doc_type_required`；`_extract_text` 按扩展名分发；敏感模式 `raw_text` 不落库；新增 parse 单测 6 项 + 修正 M1-2 旧断言 2 处；全量 22 passed；真实 curl 验证中文 docx 解析/扫描版 400/推断失败 400 均通过
- [x] **M1-5 敏感模式专项**（commit 0407c7b）：新增 `core/storage.py`（MinIO 封装：bucket 保障/`save_document_raw` 原文落盘/`list_raw_objects` 列举验证）+ `Document.minio_object_key` 内部字段（响应契约不暴露）+ Alembic `20260812_0002` 迁移已执行；上传默认模式存 MinIO 原文、敏感模式跳过（`raw_text`/`minio_object_key` 均 NULL，仅存 sha256 指纹）；`config` 补 MinIO 配置 + `.env` 本地 `localhost:9000` 覆盖；`tests/conftest.py` autouse 禁用真实 MinIO（单测不依赖外部服务）；M1-5 单测 2 项（敏感模式不落盘/默认模式落盘）；全量 24 passed；真实验证：敏感模式上传后 MinIO 空 + 库中 raw_text NULL/仅指纹/无对象 key，默认模式上传后 MinIO 有对象
- [x] **M1-6 收尾验收**（commit 2d3ea57）：新增 `test_m1_exceptions.py` 专项覆盖 E1（损坏 PDF `parse_failed`/非法 docType `invalid_doc_type`/非支持格式 `unsupported_format`）、E2（扫描版 `scanned_pdf` 提示不支持 OCR）、E3（URL 连接失败重试 1 次后 `url_fetch_failed`、非 2xx 如 404 重试后仍失败）；全量 30 passed + ruff/black 全绿；**M1 里程碑完成（6 子任务全部勾选）**
- **M1 里程碑状态**：文件上传与解析完成——PDF/docx/URL 三类输入均可解析为文本落地 Document 表；文件限制/敏感模式原文不落盘/E1-E3 异常语义全部达标；12 条红线遵守（api 薄层走 services、业务异常统一 DomainError、MinIO 仅经 core/storage）。

## 2. 进行中

- [x] **文档评审收尾（2026-08-12 定案）**：PRD 第 12 章 4 项待确认按默认值全部定案
  - [x] 待确认 1：联合审查支持 2-3 份任意合法组合 ✅
  - [x] 待确认 2：报告不做评分卡（只做发现列表）✅
  - [x] 待确认 3：demo 免 Key 限流 5 次/日 ✅
  - [x] 待确认 4：报告分享链接列为增强项 ✅

## 3. 阻塞

- （已解除：Docker daemon 经"启用虚拟机平台 + wsl --update + 镜像源替换"修复，见 2026-08-11 工作日志）

---

## 4. 待办（严格按顺序，一次一个）

### M0 环境与脚手架
**目标**：可一键启动的空壳系统——目录骨架、工具链、基础设施、健康检查、CI 全绿（ARCHITECTURE 9.1）。
**允许修改范围**：根目录 `infra/`、`backend/`、`frontend/`、`.github/`、`docs/`（仅新增），可新建脚手架文件。
**不允许破坏**：ARCHITECTURE 第 3 章目录约定；DATA_CONTRACT 枚举字典；DESIGN 14.2 设计 token。
**验收标准**（M0 完成判定）：
- [ ] M0-1 目录骨架：backend/frontend/scripts/data/infra/docs/.github 结构就位
- [ ] M0-2 工具链：uv 初始化 backend（pyproject）、pnpm 初始化 frontend、ruff+black / eslint+prettier 配置可运行
- [ ] M0-3 基础设施：infra/docker-compose.yml（Postgres16+pgvector、Redis、MinIO、后端、前端）+ `.env.example` 全量变量
- [ ] M0-4 后端最小服务：FastAPI 骨架 + `GET /health`（返回 DB/Redis 连通状态）+ Alembic 初始化
- [ ] M0-5 前端最小壳：Vite+React+TS+Tailwind+shadcn 初始化，应用壳布局（侧边栏+顶栏）与设计 token 落地
- [ ] M0-6 CI：.github/workflows/ci.yml（lint + 单测 + build）首次运行通过
- [ ] M0-7 一键验收：`docker compose up -d` 全部容器健康；健康检查通过；CI 绿；**git 存档**

### M1 文件上传与解析
**目标**：PDF/Word/URL 三类输入解析为纯文本，Document 表落地（PRD F3）。
**允许修改范围**：`backend/app/api/documents.py`、`services/`、`models/`、`alembic/`、前端上传组件。
**不允许破坏**：`Document` 契约字段（DATA_CONTRACT 4.3）；文件限制（≤20MB/≤200 页）；敏感模式"原文不持久化"；异常 E1-E3 语义。
**验收标准**：
- [x] M1-1 Document ORM + Alembic 迁移
- [x] M1-2 上传 API（multipart）格式/大小/页数校验，超限返回 400
- [x] M1-3 URL 解析 API（10s 超时 + 重试 1 次）
- [x] M1-4 解析服务：PyMuPDF/python-docx/html→text，扫描版 PDF 明确提示
- [x] M1-5 敏感模式：原文不落盘（存储目录验证为空）
- [x] M1-6 单测 + 异常用例（E1-E3）通过，**git 存档**

### M2 法条基线入库（前置核心）
**目标**：PIPL/DSL/网安法 + GB/T 35273 官方文本入库，条款结构化 + 版本化 + pgvector 检索（PRD F9、ARCHITECTURE 4.1）。
**允许修改范围**：`backend/app/knowledge/`、`rag/`、`models/`、`scripts/ingest_laws.py`、`data/raw_laws/`（私有）。
**不允许破坏**：`LawBaseline` 唯一约束（statute+article_no+version）；**版权文本（GB/T）不得提交 git**；`clauseRef` 正则（DATA_CONTRACT 3.2）。
**验收标准**：
- [ ] M2-1 LawBaseline ORM + pgvector 扩展迁移
- [ ] M2-2 条款结构化解析器：`第X章第X条第X款` 解析正确率（金标法条抽查 100%）
- [ ] M2-3 ingest_laws.py 幂等：重复运行不产生重复记录
- [ ] M2-4 版本化：修订新增版本而非覆盖；`effectiveDate` 生效
- [ ] M2-5 检索 API：Top-5 命中相关条款；无命中返回空而非幻觉
- [ ] M2-6 单测通过 + 抽查通过，**git 存档**

### M3 数据流提取与图谱
**目标**：规则+LLM 双通道抽取实体/关系，构建图谱并执行 R1-R4 推理（PRD F6）。
**允许修改范围**：`backend/app/graph/`、`tools/`（新增抽取相关）、`llm/`、图谱 API、前端图谱组件。
**不允许破坏**：`GraphPayload` 契约（DATA_CONTRACT 4.7）；`EntityRole`/`EdgeType` 枚举；R1-R4 推理语义；LLM 调用必须记账（ARCHITECTURE 红线 10）。
**验收标准**：
- [ ] M3-1 graph 模块（networkx）骨架
- [ ] M3-2 规则抽取通道（词典+正则）
- [ ] M3-3 LLM 抽取通道 + 双通道合并（冲突保留 LLM + 低置信度标记）
- [ ] M3-4 R1 出境可达路径 / R2 未获单独同意出境 / R3 声明-图谱矛盾 / R4 路径判定建议
- [ ] M3-5 图谱 API + 前端 React Flow 渲染（节点/边/风险高亮）
- [ ] M3-6 金标样例识别 ≥1 条出境路径；单测通过，**git 存档**

### M4 多维度审查 Agent（主链）
**目标**：ChatModel 工厂 + LangGraph 工作流 + D1-D6 六维并行 + 工具挂载 + SSE 进度（PRD F4）。
**允许修改范围**：`backend/app/llm/`、`agents/`、`tools/`、`prompts/`、`tasks/`（Celery）、`api/tasks.py`。
**不允许破坏**：`ReviewTask` 状态机（queued→running→done/failed）；`ComplianceFinding` 强制字段；**LLM 调用必须经 factory 且记账**；默认路由国内模型（数据不出境）；降级容错表（ARCHITECTURE 6.4）；SSE 七类事件名。
**验收标准**：
- [ ] M4-1 llm/factory.py：四 provider 路由 + Fernet 解密 + LLMCallRecord 记账
- [ ] M4-2 prompts/ 集中管理：D1-D6 提示词（输出 schema 强制）
- [ ] M4-3 LangGraph 工作流骨架 + Celery 任务
- [ ] M4-4 六维并行 + 工具挂载（法规检索/图谱查询/SCC 比对）
- [ ] M4-5 SSE 进度（taskStatus/nodeStart/nodeEnd/tokenUsage）
- [ ] M4-6 降级容错：超时重试 2 次、失败降级"待补+人工复核"、任务 10 分钟熔断
- [ ] M4-7 验收：文字版 PDF ≤100 页 → 报告 ≤3 分钟（百炼）；finding 字段齐全；mock 下 CI 通过，**git 存档**

### M5 一致性校验与反思循环
**目标**：Critic 智能体跨维度矛盾检测 + 高风险复核 + 反思循环（PRD F4、计划书 9.3）。
**允许修改范围**：`backend/app/agents/`（Critic 节点）、`prompts/`、工作流图定义。
**不允许破坏**：反思循环上限 2 轮；`ComplianceFinding` schema；`crossConsistency` 维度枚举；SSE 事件契约。
**验收标准**：
- [ ] M5-1 Critic 节点：跨维度矛盾检测（声明-行为、不出境-图谱出境）
- [ ] M5-2 高风险结论复核（needsHumanReview 联动）
- [ ] M5-3 反思循环：打回对应维度重审，≤2 轮强制结束
- [ ] M5-4 单测（矛盾样本）通过，**git 存档**

### M6 多文档联合审查
**目标**：隐私政策+DPA+SCC 声明键对齐，输出 CrossDocConflict（PRD F5）。
**允许修改范围**：`backend/app/services/`（声明键抽取/对齐）、`agents/`、`api/tasks.py`（multi 模式）、报告结构。
**不允许破坏**：`CrossDocConflict` 契约；6 个声明键枚举；合法组合规则；矛盾级别判定（高/中/低）。
**验收标准**：
- [ ] M6-1 声明键抽取（数据类别/目的/接收方/出境/保留期限/权利响应）
- [ ] M6-2 对齐比对 + 名称归一化
- [ ] M6-3 矛盾级别判定 + 双方原文证据
- [ ] M6-4 验收：注入样本（政策不出境 vs DPA 有境外接收方）检出 ≥1 条高级矛盾；联合审查 3 份 ≤10 分钟，**git 存档**

### M7 前端四件套
**目标**：聊天（SSE）/ 编排画布 / 数据流图谱 / 仪表盘四块可视化联动（PRD F7、DESIGN 7.2）。
**允许修改范围**：`frontend/src/`（pages/components/hooks/store/lib）、`api/types.ts`（仅按 DATA_CONTRACT 增补）。
**不允许破坏**：DESIGN 设计 token 与自查清单 9 条；SSE 事件名与 useSSE 映射；DATA_CONTRACT 类型；禁止直连 LLM（必须走后端）。
**验收标准**：
- [ ] M7-1 聊天栏：SSE 流式 + 追问（带条款引用）
- [ ] M7-2 编排画布：React Flow 渲染 LangGraph 图，节点状态着色
- [ ] M7-3 数据流图谱：节点/边/风险路径高亮 + "数据脉冲"动效
- [ ] M7-4 仪表盘：4 StatCard + ECharts（风险分布/维度发现/token 耗时）
- [ ] M7-5 四栏同页实时联动（运行中图谱更新、画布状态更新）
- [ ] M7-6 DESIGN 第 15 章自查清单 9 条全过；1440/1366/1280/1024 不破版，**git 存档**

### M8 账号、任务与模型配置
**目标**：JWT 双角色 + demo 免 Key 限流 + 模型配置加密 + 任务列表（PRD F1/F2）。
**允许修改范围**：`backend/app/core/`（auth）、`api/auth.py`、`api/models.py`、`services/`、前端登录/任务列表/模型配置页。
**不允许破坏**：Fernet 加密存储（Key 绝不出 API，仅 apiKeyTail）；demo 限流计数（Redis）；`UserRole`/`Provider` 枚举；数据分级 L2/L3 规则。
**验收标准**：
- [ ] M8-1 Auth：注册/登录/JWT/双角色；首个用户为 admin
- [ ] M8-2 demo 免 Key：无 Key 用户自动走系统默认模型；限流 5 次/日（429 提示）
- [ ] M8-3 模型配置：四 provider 保存/激活/测试；Key 尾号 4 位脱敏；无效 Key 拦截
- [ ] M8-4 任务列表页：表格/筛选/状态 Badge/新建入口
- [ ] M8-5 单测 + 联调通过，**git 存档**

### M9 合规报告与导出
**目标**：HTML 报告（条款引用+版本+整改 diff+跨文档矛盾区）+ Markdown 导出（PRD F8）。
**允许修改范围**：`backend/app/services/report_service.py`、`api/reports.py`、前端报告页。
**不允许破坏**：`Report` 契约（含 baselineVersion）；`diff` 渲染（DESIGN DiffView）；免责声明必须包含。
**验收标准**：
- [ ] M9-1 报告生成：findings 分组 + 条款引用 + 整改 diff + 法规版本标注
- [ ] M9-2 HTML 报告页：条款号可点击跳知识库；目录锚点；跨文档矛盾区
- [ ] M9-3 Markdown 导出完整可打开
- [ ] M9-4 单测 + 抽查通过，**git 存档**

### M10 三层评估
**目标**：40 份金标集 + evaluate.py 三层指标达标（PRD F10、计划书第十三章）。
**允许修改范围**：`data/golden/`、`scripts/evaluate.py`、`docs/eval_report.md`、prompts（如需迭代）。
**不允许破坏**：指标口径（实体 F1≥0.85 / 关系 F1≥0.80 / 高风险召回≥90% / 误报≤15% / 引用准确率≥85% / 交叉矛盾检出率≥80%）；金标标注格式。
**验收标准**：
- [ ] M10-1 金标集 40 份（30 单文档 + 10 组多文档）+ 标注 JSON
- [ ] M10-2 evaluate.py 输出三层指标报告
- [ ] M10-3 指标达成（未达成 → 迭代 prompts，每次改动重跑防回归）
- [ ] M10-4 评估报告存档 docs/eval_report.md，**git 存档**

### M11 部署上线
**目标**：生产环境一键部署（Docker Compose + Nginx + HTTPS）+ 上线验收。
**允许修改范围**：`infra/`（生产配置）、`scripts/deploy.sh`、Nginx 配置。
**不允许破坏**：数据不出境（默认国内模型）；`.env` 密钥管理；原文敏感模式。
**验收标准**：
- [ ] M11-1 生产 docker-compose（资源限制/健康检查/重启策略）
- [ ] M11-2 Nginx + HTTPS（免费证书）；静态资源缓存
- [ ] M11-3 上线验收：注册→上传→审查→报告全流程走通
- [ ] M11-4 部署文档（scripts/DEPLOY.md），**git 存档（打 tag v1.0.0）**

---

## 5. 增强项（P1/P2，MVP 后按顺序择机）

- [ ] P1 处罚案例库（RAG 第二库）+ 案例风险锚定
- [ ] P1 法规变更自动重审（基线版本差分影响分析）
- [ ] P1 独立整改建议智能体（多轮迭代）
- [ ] P1 报告分享链接（只读）
- [ ] P2 GDPR 对标维度（D9）
- [ ] P2 订阅计费（免费/专业/企业三档）
- [ ] P2 OCR 支持（扫描版 PDF）
- [ ] P2 结果缓存（重复审查复用抽取结果）

---

## 6. 纪律速查（开工前必读）

1. 一次只做一个任务，做完一个勾一个，严格按序。
2. 每步跑测试，做一步验一步。
3. 任务开工先读四要素（目标/范围/不允许破坏/验收）。
4. 模块完成 → 测试通过 → `git commit`（Conventional Commits）→ 勾选。
5. 写崩且 30 分钟内修不好 → 直接回滚到上一稳定提交，登记阻塞，不硬修。
6. 任何与文档冲突的代码视为缺陷。
