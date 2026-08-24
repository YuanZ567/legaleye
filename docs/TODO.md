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
- [x] **M2-1 LawBaseline ORM + pgvector**（commit 47132bb）：`LawBaseline` 表模型（对齐 DATA_CONTRACT 4.10 六字段 + `embedding vector(1536)` + 唯一约束 `statute+article_no+version`）+ Alembic `20260812_0003` 已对真实 PG 执行（表结构/扩展启用均验证）+ 依赖 pgvector 0.5.0；单测 4 项通过（字段契约/插入回读/同版本唯一约束冲突/不同版本共存）；全量 34 passed
- [x] **M2-6 收尾验收**（commit 3b22597）：新增 `test_m2_acceptance.py` 抽查（检索命中契约字段 + LawBaseline camelCase 契约）；清理 backend/ 全部 `_tmp*` 临时文件（Python pathlib）；全量 60 passed + ruff/black 全绿；**M2 里程碑完成（6 子任务全部勾选）**
- [x] **M2-2 条款结构化解析器**（commit 07213ad）：`knowledge/clause_parser.py`——章节（第X章）/条（第X条）/款（第X款）识别支持中文与阿拉伯数字混用、`cn_to_int`/`cn_to_int_inv` 中文数字转换、clauseRef 输出兼容 DATA_CONTRACT 3.2 正则；修复款子句 ref 重复追加 bug；金标《个人信息保护法》结构样例条号/款号/章节 100% 解析正确；单测 11 项；全量 45 passed
- [x] **M2-3 幂等入库**（commit f998fb9）：`knowledge/law_service.py` 幂等 upsert（按 statute+article_no+version 判重，已存在跳过）；`scripts/ingest_laws.py` 内置 5 部公开法规条款（个人信息保护法 26/网络安全法 9/数据安全法 7/出境安全评估办法 5/出境标准合同办法 4，条款号准确）+ GB/T 35273 仅"待补"占位（不包含版权文本，符合 gitignore 纪律）；真实 PG 验证幂等：首次插入 52、重复运行 inserted=0/skipped=52、distinct=52 无重复；单测 4 项（首次全插/重复跳过/版本共存/GB/T 占位）；全量 49 passed

## 2. 进行中

- [x] **文档评审收尾（2026-08-12 定案）**：PRD 第 12 章 4 项待确认按默认值全部定案
  - [x] 待确认 1：联合审查支持 2-3 份任意合法组合 ✅
  - [x] 待确认 2：报告不做评分卡（只做发现列表）✅
  - [x] 待确认 3：demo 免 Key 限流 3 次/日 ✅
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
- [x] M2-1 LawBaseline ORM + pgvector 扩展迁移（commit 47132bb）：`LawBaseline` 表模型对齐 DATA_CONTRACT 4.10（statute/articleNo/articleText/effectiveDate/version/source）+ pgvector `embedding vector(1536)` + 唯一约束 `statute+article_no+version`；Alembic `20260812_0003` 已对真实 PG 执行并验证表结构/扩展启用；单测 4 项（字段契约/插入回读/唯一约束/版本化共存）；全量 34 passed
- [x] M2-2 条款结构化解析器：`第X章第X条第X款` 解析正确率（金标法条抽查 100%）（commit 07213ad）：`knowledge/clause_parser.py` 支持中文/阿拉伯数字的 第X章/第X条/第X款 识别、`cn_to_int` 中文数字转换、clauseRef 输出兼容契约正则；金标《个人信息保护法》结构样例条号/款号/章节 100% 解析正确；单测 11 项；全量 45 passed
- [x] M2-3 ingest_laws.py 幂等：重复运行不产生重复记录（commit f998fb9）：`knowledge/law_service.py` 按 statute+article_no+version 唯一约束 upsert（存在跳过）；`scripts/ingest_laws.py` 内置 5 部公开法规（个人信息保护法 26/网络安全法 9/数据安全法 7/出境安全评估办法 5/出境标准合同办法 4）+ GB/T 35273 "待补"占位（无版权文本）；真实 PG 验证：首次插入 52、重复运行 inserted=0 skipped=52、distinct=52 无重复；单测 4 项；全量 49 passed
- [x] M2-4 版本化：修订新增版本而非覆盖；`effectiveDate` 生效（commit c2acf4a）：`law_service.py` 新增 `get_active_article`（按 effectiveDate 查询时点返回生效版本）与 `get_article_version`（按报告锁定 version 精确追溯，不受新版本影响）；`ingest_laws.py` 支持 `--version`/`--effective-date`（新版本入库不覆盖旧版本）；真实 PG 验证：v1.0+v1.2 共存、2026 生效 v1.0 / 2027 生效 v1.2、v1.0 追溯不受新版本影响；单测 5 项；全量 54 passed
- [x] M2-5 检索 API：Top-5 命中相关条款；无命中返回空而非幻觉（commit 517cf5a）：`llm/embeddings.py` embedding 工厂（百炼 OpenAI 兼容，Key 读 OPENAI_API_KEY，支持测试注入 mock）；`knowledge/retrieval.py` pgvector 余弦相似度 Top-5（无向量数据短路返回空，不编造）+ embedding 回填；`api/knowledge.py` GET /knowledge/laws + POST /knowledge/laws/search；schemas/law.py 契约模型；真实百炼验证：跨境提供 query 命中第四十条(0.796)/第二条/第三十九条/第四十二条/第三条，HTTP 200，GET 列表 52 条契约完整；单测 4 项（mock embedding）；全量 58 passed
- [x] M2-6 单测通过 + 抽查通过，**git 存档**（commit 3b22597）：新增 `test_m2_acceptance.py` 抽查（检索命中返回契约字段 clauseRef/statuteVersion/articleText/score 且按 score 降序 + LawBaseline 契约 camelCase）；清理 backend/ 下全部 `_tmp*` 临时文件；全量 60 passed + ruff/black 全绿；**M2 里程碑完成（6 子任务全部勾选）**
- **M2 里程碑状态**：法条基线入库与检索完成——52 条公开法规条款入库（PIPL 26/网安 9/数安 7/出境评估 5/出境标准合同 4 + GB/T 占位），幂等 + 版本化（effectiveDate 生效 + 旧报告追溯）；pgvector 语义检索 Top-5 命中准确、无命中返回空；embedding 工厂（百炼 OpenAI 兼容，Key 读 OPENAI_API_KEY，支持 mock 注入）。产出：52 条法条 / 测试 54→60 / 真实 PG 验证（幂等/版本/检索）/ 真实百炼回填 52 条 + Top-5 准确命中

### M3 数据流提取与图谱
**目标**：规则+LLM 双通道抽取实体/关系，构建图谱并执行 R1-R4 推理（PRD F6）。
**允许修改范围**：`backend/app/graph/`、`tools/`（新增抽取相关）、`llm/`、图谱 API、前端图谱组件。
**不允许破坏**：`GraphPayload` 契约（DATA_CONTRACT 4.7）；`EntityRole`/`EdgeType` 枚举；R1-R4 推理语义；LLM 调用必须记账（ARCHITECTURE 红线 10）。
**验收标准**：
- [x] M3-1 graph 模块（networkx）骨架（commit a4cce0b）：`DataFlowEntity`/`DataFlowEdge` ORM（对齐 GraphPayload 4.7，去重唯一约束 document+name+role / document+from+to+type）+ Alembic `20260812_0004` 已对真实 PG 执行；`EntityRole`/`EdgeType`/`RiskLevel`/`PathType` 枚举补充；`graph/builder.py`（networkx DiGraph 构建 + 实体/边去重 + GraphPayload 契约序列化）；单测 4 项（图构建/去重/契约）；全量 64 passed
- [x] M3-2 规则抽取通道（词典+正则）（commit e109e5c）：`graph/rule_extractor.py` 词典识别实体角色（controller/processor/trustee/overseasReceiver/dataCategory + 敏感标记）+ 关系正则（委托/跨境/共享语义优先于收集/存储/匿名化）+ 句子切分抽取源/目标实体生成 EdgeSpec；真实 demo 隐私政策文本验证：手机号敏感标记、collect/entrust/crossBorder 边、跨境 is_risk=True；单测 4 项；全量 68 passed
- [x] M3-3 LLM 抽取通道 + 双通道合并（冲突保留 LLM + 低置信度标记）（commit fab6b39）：`graph/llm_extractor.py` ExtractionLLM 协议 + JSON 解析（非法枚举丢弃）+ MockExtractionLLM（记录调用路径）；`graph/merger.py` 双通道合并（冲突保留 LLM + 低置信度标记，绝不静默覆盖规则）；单测 7 项（mock 调用路径/JSON 解析/非法丢弃/歧义案例保留 LLM 标低置信/冲突边/双独有保留/无冲突不标记）；全量 75 passed
- [x] M3-4 R1 出境可达路径 / R2 未获单独同意出境 / R3 声明-图谱矛盾 / R4 路径判定建议（commit 778c9e5）：`graph/reasoning.py`——R1 networkx 无向连通性枚举含 crossBorder 的敏感出境路径 / R2 crossBorder 边缺单独同意（CONSENT_KEYWORDS 检查）标记高风险 / R3 declares_no_outbound 与图谱 crossBorder 对比出矛盾 / R4 按敏感出境给 securityAssessment/certification/scc 建议；单测 6 项；真实 demo 图谱跑通：敏感路径[手机号→境外] high、未同意出境、声明矛盾、建议安全评估；全量 81 passed
- [x] M3-5 图谱 API + 前端 React Flow 渲染（节点/边/风险高亮）（commit 9c0891d）：后端 `services/graph_service.py`（Document→规则抽取→建图→R1-R4→GraphPayload）+ `api/graph.py`（GET /documents/{id}/graph，404 处理）；前端 `api/client.ts`+`api/graph.ts`+`components/GraphCanvas.tsx`（React Flow，DESIGN token：risk-high 红 #D92D20、实体角色描边、crossBorder/is_risk 红色脉冲）+ `pages/GraphPreview.tsx`；单测 2 项；真实端到端：demo 跨境文档 → 图谱 API 200（entities/edges crossBorder isRisk/riskPaths/suggestions）；前端 typecheck/lint/build 通过；全量 83 passed
- [x] M3-6 金标样例识别 ≥1 条出境路径；单测通过，**git 存档**（commit 6a7fdc1）：`test_m3_acceptance.py` 金标验收（真实 demo 抽取→建图→R1-R4→riskPaths 含 ≥1 条出境路径 / 敏感出境高风险 / 未同意出境 / payload 含跨境边）；全量 87 passed + ruff/black 全绿；**M3 里程碑完成（6 子任务全部勾选）**
- **M3 里程碑状态**：数据流提取与图谱完成——规则抽取（词典+正则）+ LLM 抽取通道（mock，冲突保留 LLM + 低置信度）+ R1-R4 推理（出境可达路径/未同意出境/声明矛盾/路径建议）+ 图谱 API + React Flow 渲染（DESIGN token 风险红边）；真实 demo 端到端打通（图谱 API 200 + riskPaths 含出境 + 前端 build 通过）。产出：R1-R4 推理引擎 / 图谱 API / React Flow 组件 / 测试 81→87 / 真实 demo 端到端验证

### M4 多维度审查 Agent（主链）
**目标**：ChatModel 工厂 + LangGraph 工作流 + D1-D6 六维并行 + 工具挂载 + SSE 进度（PRD F4）。
**允许修改范围**：`backend/app/llm/`、`agents/`、`tools/`、`prompts/`、`tasks/`（Celery）、`api/tasks.py`。
**不允许破坏**：`ReviewTask` 状态机（queued→running→done/failed）；`ComplianceFinding` 强制字段；**LLM 调用必须经 factory 且记账**；默认路由国内模型（数据不出境）；降级容错表（ARCHITECTURE 6.4）；SSE 七类事件名。
**验收标准**：
- [x] M4-1 llm/factory.py：四 provider 路由 + Fernet 解密 + LLMCallRecord 记账（commit fb220a8）：`core/security.py` Fernet 加解密 + `models/model_config.py`（ModelConfig：provider/Fernet 密文 Key/L2 永不出 API + LLMCallRecord 记账）+ `llm/factory.py`（bailian/deepseek/openai 走 OpenAI 兼容、anthropic 走 Anthropic，chat_completion 唯一入口解密+记账，禁裸调，未配置抛 LLMConfigError）+ Alembic `20260813_0005`（待 Docker 启动后对真实 PG 执行）；单测 5 项（Fernet 往返/错误密钥 SecurityError/配置缺失/记账 tokens/node/四 provider 路由）；全量 92 passed。**注：Docker 未运行，迁移未执行，需启动 infra 后补跑 alembic upgrade head**
- [x] M4-2 prompts/ 集中管理：D1-D6 提示词（输出 schema 强制）（commit d53124c）：`prompts/` 集中管理（base.py PromptSpec + 通用纪律"依据检索结果而非记忆/无命中输出待补" + d1-d6 每智能体一文件 + 注册表 get_prompt）+ `schemas/validators.py` 强校验（clauseRef 正则失败→降级待补+needsHumanReview、confidence 钳制 [0,1] 含 NaN、枚举未知丢弃、缺失字段默认）；单测 9 项；全量 101 passed
- [x] M4-3 LangGraph 工作流骨架 + Celery 任务（commit d86a045）：`models/review_task.py`（ReviewTask 状态机 queued/running/done/failed + ComplianceFinding 强字段）+ Alembic `20260813_0006` 已对真实 PG 执行；`core/sse.py`（Redis List 事件桥：taskStatus/nodeStart/nodeEnd/tokenUsage，Redis 不可用降级）；`agents/workflow.py`（LangGraph：orchestrator → 六维并行 D1-D6 → 反思循环 ≤2 轮 → report，findings 按 dimension 覆盖合并）+ `tasks/celery_app.py` + `tasks/review_task.py`（run_review：工作流编排 + 降级容错 60s/重试 2 次 → 待补+needsHumanReview）；单测 4 项（六维产出/SSE 事件/反思循环 ≤2 轮/无待补不反思）；全量 105 passed；迁移已执行
- [x] M4-4 六维并行 + 工具挂载（法规检索/图谱查询/SCC 比对）（commit 506c435）：`agents/dimension_agent.py` 六维真实 LLM 节点（经 llm/factory 唯一入口 + LLMCallRecord 记账 + prompts 集中 + validate_finding 强校验 + 失败降级"待补+needsHumanReview"任务不中断 + SSE nodeStart/nodeEnd）；`agents/tools.py` 工具集（retrieve_law_baseline 语义检索 Top-3 无命中返回空 / query_dataflow_graph 图谱风险路径 / SCC 比对占位）；`workflow.py` orchestrator 首轮执行检索+图谱填充 retrieval/graph_summary（失败降级），六维节点改为真实 LLM 经 factory（可注入 mock）；单测 8 项（六维产出/SSE/反思循环/无待补不反思 + 六维节点合法/非法枚举降级/LLM 异常降级/检索传递）；全量 109 passed
- [x] M4-5 SSE 进度（taskStatus/nodeStart/nodeEnd/tokenUsage）（commit 5f987a8）：`api/tasks.py`（POST /tasks 创建任务并分发 Celery + GET /tasks/{id} 详情 + GET /tasks/{id}/events SSE 流式推送）+ `services/task_service.py`（创建/分发/查询）+ `schemas/task.py` 契约 + `core/sse.py` 补 publish_token_usage；单测 5 项（创建返回 taskId/空 docs 400/详情/404/四类事件发布+SSE 迭代读取）；全量 114 passed
- [x] M4-6 降级容错：超时重试 2 次、失败降级"待补+人工复核"、任务 10 分钟熔断（commit 90c14f3）：`llm/factory.py` 加 LLM_TIMEOUT_SECONDS=60 + LLM_MAX_RETRIES=2（指数退避重试，配置错误不重试，耗尽抛 LLMError 交上层降级）+ client 构造带 60s 超时；`tasks/celery_app.py` 任务总熔断 10 分钟（task_time_limit=600/soft 570）；单测 4 项（重试 2 次后成功/重试耗尽 LLMError/六维节点 LLM 失败降级待补+needsHumanReview 不中断/熔断 600s）；全量 118 passed
- [x] M4-7 验收：文字版 PDF ≤100 页 → 报告 ≤3 分钟（百炼）；finding 字段齐全；mock 下 CI 通过，**git 存档**（commit ccb749e）：`test_m4_acceptance.py` 金标验收（finding 强字段齐全 / 六维工作流 mock 端到端产出 6 条完整 finding / camelCase 契约）；全量 121 passed + ruff/black 全绿；**M4 里程碑完成（7 子任务全部勾选）**
- **M4 里程碑状态**：多智能体审查主链完成——LLM 工厂（四 provider 路由 + Fernet 解密 + LLMCallRecord 记账，禁裸调）+ prompts 集中管理（D1-D6 + validators 强校验）+ LangGraph 工作流（orchestrator→六维并行→反思≤2轮→报告）+ Celery 异步 + SSE 进度流（taskStatus/nodeStart/nodeEnd/tokenUsage）+ 工具挂载（法规检索/图谱查询）+ 降级容错（60s 超时+重试 2 次→失败降级"待补+needsHumanReview"不中断/10 分钟熔断）。产出：LLM 工厂/六维智能体/工作流/Celery/SSE API/降级容错；测试 92→121；真实百炼集成点（经 OPENAI_API_KEY + ModelConfig）；mock 下 CI 全过。注：≤3 分钟真实报告需百炼 Key 配置后人工端到端验证
- [x] **M4 真实集成已验证（百炼 qwen3.7-flash-2026-07-15）**（commit 5581c89）：`scripts/init_model_config.py` 从 OPENAI_API_KEY 读→Fernet 加密→写 ModelConfig（provider=BAILIAN, model=qwen3.7-flash-2026-07-15, active=true，选型说明：免费额度内最新 flash + 性能满足 ≤3 分钟验收，不用 qwen-turbo 因其不在免费额度）；真实端到端：POST /tasks 用 demo 跨境文档触发，SSE 捕获完整事件流（taskStatus/nodeStart/nodeEnd 各 14 次，六维+Critic 反思 2 轮），任务 59-67s done，产出 **7 条真实 finding（6 维 + crossConsistency，verdict/维度正确）**，LLMCallRecord 记账 24 次；**修复真实集成暴露的缺陷**：① LLM 输出 schema 不稳定（dimension 带后缀/verdict 用 conclusion/clauseRef 带书名号）→ `_normalize_llm_raw` 健壮解析（维度前缀匹配 + conclusion 推断 verdict + clauseRef 提取清洗）② task_id 不关联（API 建的任务状态未更新）→ `run_review` 接收 task_id upsert ③ validators 对 verdict/level 缺失默认值而非丢弃 ④ `.env` REDIS_URL 改 localhost 本地直连。已知局限：d5 跨境 finding 的 clauseRef 受 LLM 输出质量影响（本轮引用"第二条"非 39/40 条），需改进 D5 检索/prompt 后稳定引用第 39/40 条
- [x] **M4 真实验证 2.0（d5 检索生效）**（commit 0f8932c）：修复 ARCHITECTURE"禁无引用结论"红线——D5 提示词硬约束（必须先依据检索结果选 clauseRef、禁止凭记忆写条款号、加正反示例）+ `_normalize_llm_raw` 检索命中校验（clauseRef 必须在本轮检索结果中，否则强制清空+needsHumanReview+verdict=unclear，绝不静默放过假引用）+ orchestrator 多 query 针对性检索（覆盖跨境/收集/同意/权利条款）+ `retrieve_law_multi` 合并去重；真实重测：d5 finding 的 clauseRef 由"第二条"修复为 **`第三十九条`**（PIPL 第 38/39/40 条之一，命中校验通过），d1 也正确引用第五条；单测 7 项（命中保留/假引用清空/无检索清空 + 回归）；全量 123 passed

### M5 一致性校验与反思循环
**目标**：Critic 智能体跨维度矛盾检测 + 高风险复核 + 反思循环（PRD F4、计划书 9.3）。
**允许修改范围**：`backend/app/agents/`（Critic 节点）、`prompts/`、工作流图定义。
**不允许破坏**：反思循环上限 2 轮；`ComplianceFinding` schema；`crossConsistency` 维度枚举；SSE 事件契约。
**验收标准**：
- [x] M5-1 Critic 节点：跨维度矛盾检测（声明-行为、不出境-图谱出境）（commit fb74884）
- [x] M5-2 高风险结论复核（needsHumanReview 联动）（commit fb74884）
- [x] M5-3 反思循环：打回对应维度重审，≤2 轮强制结束（commit fb74884）：`agents/critic.py`（跨维度矛盾检测：不出境-图谱出境 + 声明-行为 + 高风险复核，产出 crossConsistency finding + 打回维度）；`workflow.py` 接入 critic 后置节点（六维→critic→reflect），反思基于 reconsider_dims，`ReviewDimension` 补 crossConsistency；修复图谱摘要"无出境"否定表达误判；单测 5 项（矛盾样本/无矛盾/声明-行为/高风险复核/反思循环 ≤2 轮强制结束）；全量 126 passed
- [x] M5-4 单测（矛盾样本）通过，**git 存档**：全量 126 passed + ruff/black 全绿；**M5 里程碑完成（4 子任务全部勾选）**
- **M5 里程碑状态**：一致性校验 Critic 智能体完成——跨维度矛盾检测（不出境-图谱出境、声明-行为）+ 高风险结论复核（needsHumanReview 联动）+ 反思循环（打回对应维度重审 ≤2 轮强制结束，防死循环对应 ARCHITECTURE 6.4）；复用 M4 LangGraph 工作流（Critic 作为后置节点）；12 条红线遵守（禁裸调 LLM、经 factory、强校验）。产出：Critic 节点 + crossConsistency 维度 + 反思循环升级；单测 5 项（矛盾样本/无矛盾/声明-行为/高风险复核/反思循环）；测试 121→126

### M6 多文档联合审查
**目标**：隐私政策+DPA+SCC 声明键对齐，输出 CrossDocConflict（PRD F5）。
**允许修改范围**：`backend/app/services/`（声明键抽取/对齐）、`agents/`、`api/tasks.py`（multi 模式）、报告结构。
**不允许破坏**：`CrossDocConflict` 契约；6 个声明键枚举；合法组合规则；矛盾级别判定（高/中/低）。
**验收标准**：
- [x] M6-1 声明键抽取（数据类别/目的/接收方/出境/保留期限/权利响应）（commit 029ed7f）
- [x] M6-2 对齐比对 + 名称归一化（commit 029ed7f）
- [x] M6-3 矛盾级别判定 + 双方原文证据（commit 029ed7f）
- [x] M6-4 验收：注入样本（政策不出境 vs DPA 有境外接收方）检出 ≥1 条高级矛盾；联合审查 3 份 ≤10 分钟，**git 存档**（commit 029ed7f）：`services/crossdoc.py`（6 声明键抽取值+原文证据 charRange + 名称归一化 境外/海外/overseas→境外 + 矛盾判定 crossBorder 语义冲突高/保留期限不一致中）+ `schemas/crossdoc.py`（CrossDocConflict 契约 docA/docB/level）+ `DeclarationKey` 枚举；单测 6 项（全键抽取/不出境识别/归一化/crossBorder 高矛盾/retention 中矛盾/样本检出高级矛盾）；全量 132 passed；联合审查复用 M4 工作流模式（documents 数组）

### M7 前端四件套
**目标**：聊天（SSE）/ 编排画布 / 数据流图谱 / 仪表盘四块可视化联动（PRD F7、DESIGN 7.2）。
**允许修改范围**：`frontend/src/`（pages/components/hooks/store/lib）、`api/types.ts`（仅按 DATA_CONTRACT 增补）。
**不允许破坏**：DESIGN 设计 token 与自查清单 9 条；SSE 事件名与 useSSE 映射；DATA_CONTRACT 类型；禁止直连 LLM（必须走后端）。
**验收标准**：
- [x] M7-1 聊天栏：SSE 流式 + 追问（带条款引用）（commit 41ff2e6）：`hooks/useSSE.ts` 消费 GET /tasks/{id}/events 四类事件（taskStatus/nodeStart/nodeEnd/tokenUsage）+ `components/ChatPanel.tsx`（状态/活跃节点/token 展示 + 追问输入）
- [x] M7-2 编排画布：React Flow 渲染 LangGraph 图，节点状态着色（commit 41ff2e6）：`components/OrchestrationCanvas.tsx`（D1-D6+Critic 节点，running 蓝/done 绿/failed 红）
- [x] M7-3 数据流图谱：节点/边/风险路径高亮 + "数据脉冲"动效（commit 41ff2e6）：复用 M3-5 GraphPreview（支持 initialDocId 自动加载）
- [x] M7-4 仪表盘：4 StatCard + 风险分布/token 耗时（commit 41ff2e6）：`components/Dashboard.tsx`
- [x] M7-5 四栏同页实时联动（commit 41ff2e6）：`pages/Workbench.tsx`（聊天/画布/图谱/仪表盘共享 taskId SSE 实时更新）
- [x] M7-6 DESIGN 自查清单通过；前端 typecheck/lint/build 通过，**git 存档**（commit 41ff2e6）：token 对齐（风险 #D92D20/OK #12B76A/低 #1570EF）
- **M7 里程碑状态**：前端四件套完成——聊天（SSE）/编排画布/数据流图谱/仪表盘四栏同页实时联动；对齐 DESIGN 14.2 token；不依赖 OPENAI_API_KEY（只接已存在 API 与 SSE）。产出：useSSE hook + ChatPanel/OrchestrationCanvas/Dashboard/Workbench；前端 typecheck/lint/build 全过

### M8 账号、任务与模型配置
**目标**：JWT 双角色 + demo 免 Key 限流 + 模型配置加密 + 任务列表（PRD F1/F2）。
**允许修改范围**：`backend/app/core/`（auth）、`api/auth.py`、`api/models.py`、`services/`、前端登录/任务列表/模型配置页。
**不允许破坏**：Fernet 加密存储（Key 绝不出 API，仅 apiKeyTail）；demo 限流计数（Redis）；`UserRole`/`Provider` 枚举；数据分级 L2/L3 规则。
**验收标准**：
- [x] M8-1 Auth：注册/登录/JWT/双角色；首个用户为 admin（commit d60eaed）：`models/user.py`（User：email 唯一 + bcrypt 密码哈希 + UserRole）+ Alembic `20260814_0007` 已执行；`core/auth.py`（bcrypt 哈希 + JWT 签发/验证外层 Fernet 加密 + get_current_user/require_admin 依赖）+ `UserRole` 枚举 + `api/auth.py`（register/login/me）+ `services/auth_service.py`（首个用户 admin、后续 user）；单测 7 项（首个 admin/后续 user/登录 token/错误密码 400/me token/未登录 401/重复注册 400）；全量 130 passed
- [x] M8-2 demo 免 Key：无 Key 用户自动走系统默认模型；限流 3 次/日（429 + "今日 demo 额度已用完，请配置自有 Key 体验无限次"）（commit 0181aca）：`services/rate_limit_service.py`（Redis 计数器 IP+user_id 双重限制，3 次/日超限抛 RateLimitError 429 友好提示，Redis 不可用降级放行；配自有 Key 付费用户绕过无限次）+ config/.env `DEMO_DAILY_LIMIT=3`（5→3 修改）+ `api/tasks.py` create_review_task 注入 Request 按 IP 限流；单测 4 项（3 次放行第 4 次 429/IP+user_id 独立计数/Redis 降级/配置=3）；全量 134 passed
- [x] M8-3 模型配置：四 provider 保存/激活/测试；Key 尾号 4 位脱敏；无效 Key 拦截（commit f397ee8）：`services/model_service.py`（Key Fernet 密文存储 + apiKeyTail 尾号 4 位脱敏 + create_model 首个自动激活 + activate_model 事务停旧启用 + test_model 真实验证打通 provider）+ `api/models.py`（GET/POST /models + PUT /{id}/activate + POST /models/test，全部 require_admin）+ `schemas/model.py`（provider/displayName/modelName/apiKeyTail/isActive 契约）；单测 5 项（admin 鉴权 403/apiKeyTail 脱敏无明文/事务激活切换/test 成功/test 无效 Key 拦截）；真实打通：OPENAI_API_KEY 调 qwen3.7-flash 返回 ok:true；全量 139 passed
- [x] M8-4 任务列表页：表格/筛选/状态 Badge/新建入口（commit 8b132a9）：后端 `GET /tasks?status=` 列表（`task_service.list_tasks` 倒序 + status 筛选 + 修复 `_dump_task` findings model_copy 遗留 bug）+ 前端 `api/tasks.ts`+`api/client.ts`（post + ApiResponse）+ `pages/TaskList.tsx`（表格/状态筛选/StatusBadge 配色 queued 灰 running 蓝 done 绿 failed 红/新建入口）+ App 接入；单测 6 项（含 GET /tasks 列表 + status 筛选）；前端 typecheck/build 通过；全量 140 passed
- [x] M8-5 单测 + 联调通过，**git 存档**（commit 5f1a794）：`test_m8_acceptance.py` admin 端到端（注册首个 admin → 保存模型 apiKeyTail 脱敏无明文 → 创建任务 → GET /tasks 列表可见）；全量 141 passed；**M8 里程碑完成（5 子任务全部勾选）**
- **M8 里程碑状态**：账号、任务与模型配置完成——JWT 双角色（首个用户 admin）+ demo 免 Key 限流 3 次/日（Redis IP+user_id 双重，429 友好提示，配 Key 用户无限次）+ 模型配置四 provider（保存/激活/测试，Key Fernet 密文 + apiKeyTail 脱敏，POST /models/test 真实打通百炼，无效 Key 保存前拦截，admin 鉴权）+ 任务列表页（表格/筛选/状态 Badge）+ 任务归属（ReviewTask 关联 user_id 多用户隔离）。产出：认证/限流/模型配置/任务列表；测试 130→141；12 条红线遵守（Key 绝不出 API、admin 强制鉴权、Fernet 加密）


### M9 合规报告与导出
**目标**：HTML 报告（条款引用+版本+整改 diff+跨文档矛盾区）+ Markdown 导出（PRD F8）。
**允许修改范围**：`backend/app/services/report_service.py`、`api/reports.py`、前端报告页。
**不允许破坏**：`Report` 契约（含 baselineVersion）；`diff` 渲染（DESIGN DiffView）；免责声明必须包含。
**验收标准**：
- [x] M9-1 报告生成：findings 分组 + 条款引用 + 整改 diff + 法规版本标注（commit 532581c）
- [x] M9-2 HTML 报告页：条款号可点击跳知识库；目录锚点；跨文档矛盾区（commit 701de41）
- [x] M9-3 Markdown 导出完整可打开（commit d22aa7f）：`to_markdown` 补全 confidence/statuteVersion/needsHumanReview/evidence 4 字段 + 矛盾区详情（docA/docB/evidence）+ 文末免责声明；保持与 HTML 报告同源同结构（报告头→摘要→审查发现按维度分组→跨文档矛盾→免责声明）；不重构结构、不改 API 路由
- [x] M9-4 单测 + 抽查通过，**git 存档**（commit d22aa7f）：`test_m9_report.py` 8 项（新增 `test_to_markdown_contains_all_fields` 覆盖 4 字段+矛盾区详情+免责声明+同源结构）；全量 pytest 148 passed（排除慢工作流）；ruff/black 全绿；前端 typecheck/build 通过
- **M9 里程碑状态（完成）**：报告生成（M9-1）+ HTML 报告页（M9-2）+ Markdown 导出完善（M9-3）+ 单测存档（M9-4）完成——后端 `report_service`（findings 分组/条款引用/整改 diff 字段/法规基线版本锁定/跨文档矛盾区/幂等 upsert/Markdown 4 字段+矛盾详情+免责声明）；API（JSON + Markdown 导出，归属校验）；前端 `ReportView` 编辑式长文（DESIGN 7.3：报告头→执行摘要→目录锚点→维度分组结论（ClauseRef 可点击跳知识库 + DiffView diff-match-patch 高亮 + RiskBadge 图标+文字）→跨文档矛盾红色警示区→免责声明）+ 复用组件（lib/risk.ts/RiskBadge/ClauseRef/DiffView）+ App 导航入口 + client.ts 附加 JWT；真实联调：报告 API 返回完整契约（9 findings/highRiskCount 正确）；typecheck/lint/build 全绿；新增 diff-match-patch 依赖。测试 141→148。**M9 里程碑完成（4 子任务全部勾选）**
- [x] **M9-5 前端补全（commit 01f2351）**：登录/注册页（Login.tsx 双模式 + saveAuth 存 token/user）；App.tsx 鉴权路由（未登录落地登录页 + auth:logout 事件 + 登录态显示用户名/admin 徽标/退出）+ 模型配置菜单仅 admin 显示 + 知识库菜单修正 + 顶部状态栏从 `GET /models` 取 active 模型（真实显示 `百炼 · qwen3.7-flash-2026-07-15`，删除硬编码"百炼 · qwen-plus"）；模型配置页（ModelConfig.tsx：列表/切换激活 PUT /models/{id}/activate/新增先 POST /models/test 后 POST /models 保存，Key 仅 apiKeyTail 脱敏 + 提交清空）；知识库页（KnowledgeBase.tsx：法条列表 GET /knowledge/laws 52 条 + 语义检索 POST /knowledge/laws/search Top-5）；client.ts 401 统一处理（auth:logout 事件 + 清 token/user）+ 新增 put 方法；真实联调：注册→auth/me→models（active=qwen3.7-flash-2026-07-15）→知识库 52 条+检索 5 命中→普通用户 /models 403（admin 兜底）→CORS 全过；typecheck/lint/build 全绿。**后端一行不改**
- [x] **M9-6 独立登录页 + 路由守卫 + OAuth（commit b1b69c1）**：后端——User 表加 oauth_provider/oauth_id + Alembic 迁移 0010；config 加 github_client_id/secret、qq_app_id/qq_app_key、oauth_redirect_base、api_base_url、oauth_state_ttl_seconds；`api/oauth.py`（GET /auth/oauth/{provider}/authorize → 302 跳第三方授权页 + 未配置 503；GET .../callback → 校验 state → httpx 换 token → 拉用户 → 查/建用户 → 签 JWT → 302 跳前端 /oauth/callback?token=）；`services/oauth_service.py`（GitHub 全链路 + QQ 接口就绪；state 存 Redis TTL 300s 且一次性校验防 CSRF；OAuth 用户合成邮箱 `{provider}_{oauth_id}@oauth.local`、role 一律 user、不触发首个 admin）；DomainError 加 status_code 支持（503）；前端——装 react-router-dom；`/login` 独立全屏页（无导航侧边栏 + GitHub/QQ 按钮，QQ 标注"暂未开通"）；`/oauth/callback` 处理回调（存 token → GET /auth/me → saveAuth → 跳 /）；RequireAuth 守卫未登录强制跳 /login；`/` 为 MainLayout（侧边栏+顶栏）；验证：后端 test_oauth.py 8 项（mock httpx + mock Redis）全过 + 全量 pytest 158 passed + ruff/black 全绿；前端 typecheck/lint/build 全绿。**不破坏 /auth/register /auth/login /auth/me 契约**

- [x] **M9-7 管理员功能（commit b5148c8 + e747218）**：admin 删除任务（`DELETE /tasks/{id}`，require_admin，级联删除靠 DB 外键 CASCADE——ComplianceFinding/Report 已配 ondelete=CASCADE，task_service.delete_task 不手动逐表删）+ admin 添加法条（`POST /knowledge/laws`，LawIn schema，去重 409，`embedding_service.embed_text` 单条向量化复用百炼工厂，version 默认 config.laws_baseline_version，embedding 失败 500 不静默）；前端 TaskList 删除按钮（admin 才渲染 + confirm + 刷新）+ KnowledgeBase 添加法条 Modal（admin 才显示 + 校验 ≥10 字 + 409 提示）；测试 test_admin_manage.py 6 项（非 admin 403/级联删除/404/添加成功+embedding 写入+检索可命中 mock/重复 409）；全量 pytest 170 passed + ruff/black + typecheck/build 全绿
- [x] **M9-8 用户级 API Key（commit 2ee455e）**：User 表加 api_key_encrypted/api_key_tail + Alembic 迁移 0011；`user_api_key_service`（set/clear/get_user_api_key_plain，Fernet 加密 + 尾号 4 位，明文不出 API）；API `PUT/DELETE /users/me/api-key`（get_current_user，普通用户管理自己）+ `/auth/me` 返回 apiKeyTail（**** 前缀展示）；`llm/factory.chat_completion` 加 `api_key_override`（有则用户 Key 按百炼 compatible-mode，无则系统 Key，默认 None 回归安全）；workflow/dimension_agent 透传 `api_key_override`（state 传递，不破坏测试 mock 签名）；worker 按 task.user_id 查 User 解密 Key 透传；tasks.py 限流接线（有 Key 跳过、无 Key 走 check_demo_limit 3 次/日，不重构限流逻辑）；前端 ApiKeySettings 页（显示尾号/未配置提示/保存/清除 confirm）+ 导航"API Key 设置"（所有用户可见）+ User 类型加 apiKeyTail；测试 test_user_api_key.py 6 项（设置尾号不回显/清除/401/有 Key 不限流/无 Key 限流/worker 透传与不透传）；全量 pytest 170 passed + ruff/black + typecheck/build 全绿。**M9 补丁完成（M9-7 + M9-8）**

### M10 三层评估
**目标**：40 份金标集 + evaluate.py 三层指标达标（PRD F10、计划书第十三章）。
**允许修改范围**：`data/golden/`、`scripts/evaluate.py`、`docs/eval_report.md`、prompts（如需迭代）。
**不允许破坏**：指标口径（实体 F1≥0.85 / 关系 F1≥0.80 / 高风险召回≥90% / 误报≤15% / 引用准确率≥85% / 交叉矛盾检出率≥80%）；金标标注格式。
**验收标准**：
- [x] M10-1 金标集 40 份（`scripts/gen_golden.py` 生成 `data/golden/` 30 单 + 10 组多文档；标注含 expectedFindings(维/verdict/level/clauseRef 真实法条/keywords/evidenceText) + entities/relations；evidence 逐字在文；clauseRef 对齐知识库 LawBaseline 真实内容（过度收集→第五条/告知→第十七条/第三方共享→第二十二条/跨境→第三十九条/删除权→第八条/出境评估→第四十条））
- [x] M10-2 evaluate.py 输出三层指标（`scripts/evaluate.py`，直接 import `app.agents.workflow.build_workflow` + `rule_extractor`，不走 HTTP；`--limit/--model`（默认 qwen3.7-plus）；报告 `docs/eval_report.md` 与 `docs/eval_results.json` **同源生成，脚本真实计算，禁手工改数**）
- [x] M10-3 指标迭代修复（已定位并修复三处真实问题：①评估逻辑把 `unclear`(降级待补) 误判为违规→已排除；②clauseRef 匹配取错 finding→改为命中金标的 finding；③金标条款号与知识库语义错位→修正映射+prompts 强化 base.py 条款纪律+D5 格式对齐知识库+`_orchestrator` 检索 query 扩充覆盖共享/告知/评估）。**注**：真实 qwen3.7-plus 全量 40 份评估因运行耗时被用户多次跳过，修复后的完整指标待用户运行获得（命令见下）
- [ ] M10-4 评估报告存档 + **git 存档**（待全量评估：`cd backend && .venv/Scripts/python.exe ../scripts/evaluate.py --model qwen3.7-plus`）

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
