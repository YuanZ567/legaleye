# LegalEye 法眼 — 产品需求文档（PRD）

> 版本：v1.0
> 日期：2026-08-11
> 状态：待评审（基于 `docs/OPENCODE.md` v1.0 计划书起草，开发前须确认）
> 关联文档：`docs/OPENCODE.md`（项目计划书）、`docs/archive/OPENCODE_v0.3.md`

---

## 1. 文档目的

本 PRD 将项目计划书中的战略与范围翻译为**开发可直接照做的功能规格**，明确每个功能模块的：功能描述、业务规则、输入/输出、异常处理、验收标准。开发过程中如与计划书冲突，以本 PRD 为准；本 PRD 未覆盖之处，按计划书执行。

---

## 2. 背景与目标（摘要，详见计划书）

- **问题**：出海企业数据合规审查依赖人工逐条对照法条，耗时长、易漏跨境风险路径；隐私政策 / DPA / SCC 多文件分开审，声明不一致无人交叉核对。
- **方案**：多智能体（10 个：1 主控 + 1 抽取 + 6 维审查 + 1 校验 + 1 报告）按 PIPL 章节维度并行审查，输出带法规条款引用、数据流图谱推理、跨文档矛盾检测的结构化报告。
- **MVP 业务目标**：单份隐私政策审查 < 3 分钟；三文件联合审查 < 10 分钟；每条结论附法规条款号与版本。
- **MVP 质量目标**：三层评估达标（见第 9 章验收标准）。

---

## 3. 用户与场景

| 角色 | 说明 | 核心诉求 |
|---|---|---|
| 合规负责人（主用户） | 出海企业 DPO / 法务 / 安全 | 快速审查、可追溯依据、发现人工漏检的跨境风险与跨文档矛盾 |
| 管理员 | 项目运维者（本人） | 管理用户、知识库入库与版本、监控用量 |
| demo 用户 | 未配置 Key 的访客 | 免 Key 体验全流程，验证产品 |

**典型场景（P0）**：
- S1 单文件审查：上传隐私政策 PDF → 6 维审查 → 图谱出境路径高亮 → 报告导出。
- S2 多文件联合审查：上传隐私政策 + DPA（+SCC）→ 交叉一致性校验 → 跨文档矛盾清单。
- S3 追问：审查完成后在聊天区追问"如果改用香港机房呢？" → 得到基于当前图谱与法规的增量回答。

---

## 4. 产品范围与优先级

### 4.1 MVP 功能清单（P0 / P1）
| 编号 | 功能 | 优先级 | 说明 |
|---|---|---|---|
| F1 | 账号与登录（双角色 + demo 免 Key） | P0 | JWT；user/admin；demo 模式限流 |
| F2 | 模型配置管理 | P0 | 百炼默认；自带 Key（OpenAI/Anthropic/DeepSeek） |
| F3 | 文件上传与解析 | P0 | PDF/Word/URL；格式与大小校验 |
| F4 | 单文件审查任务（多智能体流水线） | P0 | 6 维并行 + 工具调用 + 反思循环 |
| F5 | 多文档联合审查 | P0 | 声明键对齐 + 跨文档矛盾 |
| F6 | 数据流知识图谱与推理 | P0 | 实体/关系抽取 + 出境可达路径 |
| F7 | 四块可视化 | P0 | 聊天 / 画布 / 图谱 / 仪表盘 |
| F8 | 合规报告与导出 | P0 | HTML + Markdown；条款引用 + diff |
| F9 | 知识库管理（管理员） | P1 | 法条列表/版本/重新入库 |
| F10 | 三层评估工具链 | P1 | 金标集 + evaluate 脚本 |

### 4.2 明确不做（MVP）
- 合规文件起草、App 代码级扫描、电子签章/OA 集成、计费支付、多人协作、OCR（扫描版 PDF）、多语言。

---

## 5. 功能需求详述

### F1 账号与登录

**功能描述**：邮箱+密码注册/登录；用户、管理员双角色；demo 免 Key 模式。

**业务规则**：
- 密码：≥8 位，含字母与数字；服务端 bcrypt 哈希存储。
- JWT：access token 有效期 2h，refresh token 7d；前端刷新自动续期。
- demo 免 Key 模式：注册用户未配置模型 Key 时，任务自动使用系统默认 provider（百炼）与默认模型；**限流：每用户每日 ≤5 次审查任务**，超额返回明确提示。
- 管理员：首个注册用户自动成为 admin（`role=admin`）；admin 可见全部任务与知识库管理入口。

**输入/输出**：
- `POST /auth/register` {email, password} → {token, user}
- `POST /auth/login` {email, password} → {token, user}
- `GET /auth/me` → {user}

**异常处理**：
| 场景 | 处理 |
|---|---|
| 邮箱已注册 | 400，提示"该邮箱已注册" |
| 密码强度不足 | 400，列出规则 |
| 登录失败 | 401，"邮箱或密码错误"（不区分提示） |
| demo 超限 | 429，"今日演示额度已用完，请配置自己的模型 Key" |

**验收标准**：
- [ ] 注册/登录/登出全流程可用，token 过期自动跳登录
- [ ] demo 用户（无 Key）可完成 1 次完整审查；第 6 次被限流拦截

---

### F2 模型配置管理

**功能描述**：用户配置/切换 LLM provider 与模型；服务端加密存储 Key。

**业务规则**：
- provider 枚举：`bailian`（默认）/ `deepseek` / `openai` / `anthropic`。
- Key 使用 `cryptography.Fernet` 加密后存储（主密钥来自环境变量 `LEGALEYE_SECRET_KEY`）；**任何接口不得返回明文 Key**，仅返回尾号 4 位（脱敏展示）。
- 每用户同时仅一个 `is_active=true`；切换时前端弹窗提示数据出境风险（切到 openai/anthropic 时）。
- 默认模型映射：bailian→qwen-plus；deepseek→deepseek-chat；openai→gpt-4o-mini；anthropic→claude-3-5-haiku（均以官方可用型号为准，可在配置页修改 model 名）。

**输入/输出**：
- `POST /models` {provider, api_key, model} → {model_config}（不含明文 Key）
- `GET /models` → [{provider, model_tail, is_active, model}]
- `PUT /models/:id/activate` → {model_config}

**异常处理**：
- Key 无效：保存时调用一次 `POST /models/test`（该 provider 最小请求）校验，失败 400 提示"Key 无效或额度不足"。
- 未配置 Key 且关闭 demo 模式：创建任务时 400 提示引导配置。

**验收标准**：
- [ ] 配置 4 家 provider 均可保存、激活、切换
- [ ] 数据库中 Key 为密文；前端仅显示尾号
- [ ] 无效 Key 保存被拦截

---

### F3 文件上传与解析

**功能描述**：上传合规文件（PDF/Word/URL），解析为纯文本用于审查。

**业务规则**：
- 格式：PDF（.pdf）、Word（.docx）、URL（http/https）。其他格式前端拦截、后端 400。
- 大小限制：≤20MB；超过提示"文件过大（≤20MB）"。
- 页数限制：≤200 页（仅 PDF 校验）；超过提示拆分为多份。
- doc_type：由用户选择（privacy_policy / user_agreement / dpa / scc）；若未选择，后端按文件名/内容启发式推断，推断失败提示手动选择。
- 解析：PyMuPDF（PDF）、python-docx（Word）、httpx（URL，超时 10s，抓取 html 转文本）。
- **扫描版 PDF（无文字层）**：检测到页文字为空时，明确提示"未检测到文字层，MVP 不支持 OCR，请提供文字版"。
- 原文存储：默认持久化至 MinIO；敏感模式开关开启时**仅内存解析后丢弃原文**，只存解析文本摘要。

**输入/输出**：
- `POST /documents`（multipart: file / doc_type / sensitive_mode）→ {document_id, doc_type, char_count, text_preview}
- `POST /documents/from-url` {url, doc_type} → 同上

**异常处理**：
| 场景 | 处理 |
|---|---|
| 非支持格式 | 400，格式清单提示 |
| 空文件 / 解析失败 | 400，"文件内容为空或无法解析" |
| URL 抓取失败/超时 | 自动重试 1 次（指数退避），仍失败 → 400 提示 |
| 扫描版 PDF | 400（含检测说明） |

**验收标准**：
- [ ] PDF（文字版）/ docx / URL 三类输入均可解析出文本
- [ ] 超限、空文件、扫描版均给出明确中文提示
- [ ] 敏感模式下原文不被持久化（验证存储目录无文件）

---

### F4 单文件审查任务（核心）

**功能描述**：创建审查任务，驱动 LangGraph 多智能体流水线执行，实时推送进度，产出结构化报告。

**业务规则（流水线）**：
1. 任务状态机：`queued → running → done / failed`；celery 排队，并发上限 2（worker 数）。
2. 执行链：
   - 合规编排官：识别 doc_type → 动态路由（privacy_policy 触发 D1-D6 全量；scc 触发 D4 为主 + D1/D2 辅助）→ 分发。
   - 数据流提取：规则 + LLM 双通道抽取实体/关系 → 构图（networkx）。
   - D1-D6 六路并行：各维度按需调用工具（`retrieve_law_baseline` / `retrieve_enforcement_case` / `query_dataflow_graph` / `compare_scc_template`）。
   - 一致性校验 Critic：跨维度矛盾检测 + 高风险结论复核；发现问题打回对应维度重审，**反思循环上限 2 轮**。
   - 合规报告：汇总生成报告 JSON + 整改 diff。
3. 每条 `ComplianceFinding` 强制字段：
   | 字段 | 说明 | 约束 |
   |---|---|---|
   | dimension | D1-D6 / cross_consistency | 枚举 |
   | verdict | 合规 / 不合规 / 待补 / 不适用 | 枚举 |
   | level | 高 / 中 / 低 | 枚举 |
   | clause_ref | 违规条款号，如"第39条第1款" | 非空（待补除外） |
   | statute_version | 法规名+版本，如"个人信息保护法(2021)" | 非空 |
   | description | 问题描述 | 非空，≤500 字 |
   | remediation | 整改建议文本 | 非空 |
   | confidence | 0-1 | 必填 |
   | needs_human_review | 是否建议人工复核 | 布尔；高风险默认 true |
   | evidence | 依据原文片段（可溯源） | 尽量非空 |
4. 工具调用规则：
   - D4 必须调用 `compare_scc_template`（比对官方 SCC 模板）；SCC 模板缺失时标记"待补"。
   - D1/D2/D3/D5/D6 检索法规库 ≥1 次（结果并入依据）。
   - D4/D5 查询图谱（出境边 / 敏感数据类别）。
5. 超时熔断：单任务总超时 **10 分钟**；单节点 LLM 调用超时 60s、重试 2 次（指数退避）；节点连续失败 → 该维度降级输出 `verdict=待补` + `needs_human_review=true`，任务不中断。
6. SSE 推送事件（`GET /tasks/:id/events`）：
   | event | 载荷 | 时机 |
   |---|---|---|
   | `task_status` | {status, queue_position?} | 状态变化 |
   | `node_start/end` | {node, node_type} | 每个智能体起止 |
   | `finding_created` | {finding} | 单条结论产出 |
   | `graph_update` | {graph} | 图谱节点/边新增 |
   | `token_usage` | {node, tokens, cost_est} | 每节点调用后 |
   | `error` | {message} | 异常 |

**输入/输出**：
- `POST /tasks` {document_id, model_config_id?} → {task_id}
- `GET /tasks/:id` → {task, findings, graph, report_summary}

**异常处理**：
- 文档已存在进行中任务：允许新建（文档可复用），不强制互斥。
- 模型不可用（Key 失效/额度耗尽）：任务 failed，明确错误原因；前端提供"重试"按钮。

**验收标准**：
- [ ] 文字版 PDF 隐私政策（≤100 页）从提交到 done ≤ 3 分钟（百炼默认模型）
- [ ] 每条 finding 六个强制字段齐全，clause_ref 可点击跳转知识库原文
- [ ] SSE 六类事件前端可观察到；失败任务有原因与重试入口
- [ ] 反思循环超过 2 轮被强制终止（日志验证）

---

### F5 多文档联合审查

**功能描述**：对隐私政策 + DPA + SCC 的任意 2-3 份组合做交叉一致性校验，输出跨文档矛盾。

**业务规则**：
- 入口：审查页选择"联合审查"模式，上传 2-3 份文件并标记各自 doc_type。
- 合法组合：privacy_policy + dpa；privacy_policy + scc；privacy_policy + dpa + scc；dpa + scc。**不允许两份同 doc_type**。
- 执行：各文件独立完成 6 维审查后，一致性校验智能体执行声明键对齐：
  - **声明键**：数据类别、处理目的、接收方列表、是否出境、保留期限、权利响应方式。
  - 抽取：从各文件提取键值（含原文片段引用）。
  - 对齐：名称归一化（同义实体合并，如"XX 物流"与"XX 国际物流"）→ 键匹配 → 值不一致判为矛盾。
- 矛盾级别：
  | 级别 | 判定规则 | 示例 |
  |---|---|---|
  | 高 | 出境声明冲突 / 接收方缺失或冲突 | 隐私政策"数据不出境" vs DPA 含境外接收方 |
  | 高 | 敏感信息接收方未在另一文件中披露 | DPA 列境外接收方，隐私政策未披露 |
  | 中 | 保留期限 / 处理目的表述不一致 | 政策"保留 1 年" vs DPA"保留至服务终止" |
  | 低 | 措辞不一致但语义一致 | 术语叫法不同 |
- 输出 `CrossDocConflict`：{declaration_key, doc_a_value, doc_b_value, level, evidence_a, evidence_b}，报告中单独"跨文档矛盾"区呈现。

**输入/输出**：
- `POST /tasks` {document_ids: [..], task_type: "multi"} → {task_id}
- 报告 JSON 增加 `cross_doc_conflicts` 数组。

**异常处理**：
- 非法组合（同类型重复/少于 2 份）→ 400 提示。
- 某文件解析失败 → 400 提示具体文件。

**验收标准**：
- [ ] 用"政策说不出境 + DPA 有境外接收方"的注入样本，检出 1 条高级矛盾
- [ ] 矛盾项均带双方原文片段可溯源
- [ ] 联合审查（3 份）总耗时 ≤ 10 分钟

---

### F6 数据流知识图谱与推理

**功能描述**：从文档抽取数据流实体与关系，构建图谱，执行合规推理，前端可视化与高亮。

**业务规则**：
- 实体角色枚举：`controller`（控制者）/ `processor`（处理者）/ `trustee`（受托方）/ `overseas_receiver`（境外接收方）/ `data_category`（数据类别，含 `is_sensitive`）。
- 边类型枚举：`collect`（收集）/ `store`（存储）/ `share`（共享）/ `entrust`（委托）/ `cross_border`（跨境传输）/ `anonymize`（匿名化）；边属性：`legal_basis`、`is_risk`、`evidence`（原文片段）。
- 抽取：规则（实体词典 + 正则）与 LLM 双通道，结果交叉合并；冲突时保留 LLM 结果并标注低置信度。
- 推理规则：
  | 规则 | 逻辑 | 输出 |
  |---|---|---|
  | R1 出境可达路径 | BFS/DFS：data_category（is_sensitive=true）→ … → cross_border 边 → overseas_receiver | 路径列表（含中间跳） |
  | R2 未获单独同意出境 | cross_border 边 && 文档无对应单独同意条款 | 高风险边 |
  | R3 声明-图谱矛盾 | 文档声明"不出境" && 存在 cross_border 边 | 一致性冲突（转 F5/F4 Critic） |
  | R4 路径判定建议 | 依据出境数据量与敏感标记，输出建议（安全评估 / SCC / 认证 / 信息不足） | 建议 + "待补"标记 |
- 前端交互：节点点击 → 弹出相关原文片段与条款；高风险路径红色高亮；支持缩放/拖拽。

**输入/输出**：
- `GET /graph/:task_id` → {entities: [], edges: [], risk_paths: [], suggestions: []}

**验收标准**：
- [ ] 金标样例（含跨境数据流）能识别 ≥1 条出境可达路径并高亮
- [ ] R2 未获单独同意出境边被标记（金标验证）
- [ ] 图谱 JSON 与前端渲染一致（节点/边数量核对）

---

### F7 四块可视化

**功能描述**：审查页四栏联动展示：聊天 / 编排画布 / 数据流图谱 / 监控仪表盘。

**业务规则**：
- 聊天（左）：SSE 流式输出；支持审查完成后追问（走"问答 Agent"：基于当前报告 + 图谱 + 法规库回答，带引用）；消息持久化到 `ChatMessage`。
- 编排画布（右上）：React Flow 渲染 LangGraph 图；节点状态着色（运行中蓝 / 完成绿 / 失败红）；节点点击显示该智能体输入输出摘要。
- 数据流图谱（右下）：见 F6，复用 React Flow。
- 仪表盘（顶部条）：任务耗时、token 消耗、各维度发现数、风险分布（ECharts 环形/条形）。

**输入/输出**：
- `POST /tasks/:id/chat` {message} → SSE 流式增量文本
- `GET /tasks/:id/orchestration` → LangGraph 图 JSON（节点/边/状态）

**验收标准**：
- [ ] 四栏同页渲染，审查过程实时联动（图谱随抽取更新、画布随节点状态更新）
- [ ] 追问"改用香港机房"返回含条款引用的增量回答

---

### F8 合规报告与导出

**功能描述**：生成在线 HTML 报告 + Markdown 导出。

**业务规则**：
- HTML 报告结构：报告头（文档/任务/审查时间/**法规基线版本**）→ 执行摘要（发现数、高风险数）→ 按维度分组结论 → 每条结论含条款引用（可点击跳知识库原文）、版本、置信度、整改 diff（原文 vs 建议，`diff-match-patch` 高亮）→ 跨文档矛盾区（联合审查）→ 免责声明。
- Markdown 导出：同内容降级版（无交互跳转）。
- 报告持久化 `Report{content_json, md_export, baseline_version}`；baseline_version 记录审查时法规库版本号（如 `laws-v1.0-20260811`）。

**输入/输出**：
- `GET /reports/:task_id` → HTML
- `GET /reports/:task_id/export.md` → Markdown 下载

**验收标准**：
- [ ] HTML 报告条款号可点击跳转；diff 高亮正确
- [ ] Markdown 导出内容完整、可打开
- [ ] 报告标注法规基线版本

---

### F9 知识库管理（管理员，P1）

**功能描述**：查看法条基线列表与版本、触发重新入库、检索测试。

**业务规则**：
- 仅 admin 可访问；用户角色校验服务端强制。
- 入库幂等：同 statute+article_no+version 覆盖更新，不重复插入；入库异步执行（Celery）。
- 版本化：法规修订新增版本记录，`effective_date` 生效；报告引用时锁定版本。

**输入/输出**：
- `GET /knowledge/laws?statute=&version=` → 法条列表
- `POST /knowledge/laws/ingest` {source} → 入库任务（admin）
- `POST /knowledge/laws/search` {query} → 检索结果

**验收标准**：
- [ ] admin 可入库/查看版本；普通用户访问 403
- [ ] 重复入库不产生重复记录

---

### F10 三层评估工具链（P1）

**功能描述**：金标集 + 评估脚本，量化审查质量。

**业务规则**：
- 金标集：`data/golden/` 下 30 份单文档 + 10 组多文档，每份含标注 JSON（注入风险 + ground truth）。
- `scripts/evaluate.py` 运行评估，输出三层指标报告（见计划书第十三章），写 `docs/eval_report.md`。
- 每次 prompt/工作流改动后必须运行，防回归。

**验收标准**：
- [ ] evaluate.py 可运行并输出三层指标
- [ ] 指标达到第 9 章验收值

---

## 6. 数据模型要点（详见计划书第十五章，此处仅补字段级约束）

- `Document.raw_text`：敏感模式下为 NULL；解析文本摘要存 `text_fingerprint`。
- `ComplianceFinding.clause_ref`：格式校验 `^第?[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?$`（校验失败视为待补并告警）。
- `CrossDocConflict.evidence_a/evidence_b`：均存原文片段 + 文档引用（`{document_id, char_range}`）。
- `DataFlowEntity` 名称唯一约束（按 document_id + name + role 去重）。
- `LawBaseline` 唯一约束（statute + article_no + version）。

---

## 7. 非功能需求（摘要，详见计划书第十七章）

- 性能：单文件 < 3 分钟；联合审查 < 10 分钟；10 并发。
- 安全：数据不出境（默认百炼）；Key Fernet 加密；原文可选不持久化；JWT + RLS 等价的行级过滤。
- 可观测：loguru 结构化日志；token 统计；Sentry。
- 可扩展：维度 D7/D8 同式接入；provider 可扩展。

---

## 8. 异常与边界汇总（全局清单）

| # | 场景 | 处理 | 关联 |
|---|---|---|---|
| E1 | 上传非支持格式 | 前端拦截 + 400 | F3 |
| E2 | 扫描版 PDF | 明确提示不支持 OCR | F3 |
| E3 | URL 抓取失败 | 重试 1 次，仍失败 400 | F3 |
| E4 | 模型 Key 无效 | 保存时测试拦截；运行中失败 → 任务 failed + 重试入口 | F2/F4 |
| E5 | 单节点 LLM 超时 | 重试 2 次（退避），仍失败降级"待补+人工复核"，不中断任务 | F4 |
| E6 | 反思循环失控 | 上限 2 轮强制结束 | F4 |
| E7 | 法规库检索无结果 | 结论标记"待补：法规未命中"，**禁止臆造条款号** | F4 |
| E8 | 非法联合组合 | 400 提示合法组合 | F5 |
| E9 | 任务超时（10 分钟） | 熔断为 failed，保留已产出 findings | F4 |
| E10 | demo 限流 | 429 提示配置 Key | F1 |
| E11 | 图谱抽取冲突（规则 vs LLM） | 保留 LLM 结果 + 低置信度标记 | F6 |
| E12 | 并发超限 | Celery 排队，SSE 通知排队位置 | F4 |

---

## 9. 验收标准总清单（可勾选，MVP 交付）

**P0 必备（缺一不可）**：
- [ ] 注册/登录/双角色/demo 免 Key 全流程可用（F1）
- [ ] 文字版 PDF 隐私政策 ≤100 页：提交 → 报告 ≤ 3 分钟（百炼默认模型）（F4）
- [ ] 每条 finding 含 clause_ref + statute_version + confidence + needs_human_review，条款号可点击跳转原文（F4/F8）
- [ ] 金标样例可识别 ≥1 条出境可达路径并高亮（F6）
- [ ] "政策说不出境 + DPA 有境外接收方"样本检出 ≥1 条高级跨文档矛盾（F5）
- [ ] 四栏可视化同页实时联动（F7）
- [ ] 失败任务有明确原因与重试入口；无任何未处理异常（E1-E12 全部覆盖）（F4）
- [ ] 敏感模式原文不持久化（F3）
- [ ] 报告含法规基线版本标注 + 免责声明（F8）

**P1（时间允许时）**：
- [ ] 三层评估指标：实体 F1 ≥ 0.85 / 关系 F1 ≥ 0.80 / 高风险召回 ≥ 90% / 误报 ≤ 15% / 条款引用准确率 ≥ 85% / 交叉矛盾检出率 ≥ 80%（F10）
- [ ] evaluate.py 可运行，40 份金标跑通（F10）
- [ ] 知识库管理（admin）可用（F9）

**P2（增强项，不在 MVP 验收）**：处罚案例库、法规变更自动重审、GDPR 对标、独立整改迭代。

---

## 10. API 摘要（REST + SSE）

| 方法 | 路径 | 说明 | 权限 |
|---|---|---|---|
| POST | /auth/register, /auth/login | 注册/登录 | 公开 |
| GET | /auth/me | 当前用户 | 登录 |
| GET/POST | /models, /models/:id/activate, /models/test | 模型配置 | 登录 |
| POST | /documents, /documents/from-url | 上传/解析 | 登录 |
| POST | /tasks | 创建审查（single/multi） | 登录 |
| GET | /tasks/:id, /tasks/:id/events(SSE) | 任务详情/进度 | 登录 |
| POST | /tasks/:id/chat | 追问（SSE） | 登录 |
| GET | /graph/:task_id, /tasks/:id/orchestration | 图谱/编排图 | 登录 |
| GET | /reports/:task_id, /export.md | 报告/导出 | 登录 |
| GET/POST | /knowledge/laws* | 知识库管理 | admin |
| GET | /findings/:task_id | 结论列表 | 登录 |

---

## 11. 开发顺序建议（对应计划书里程碑）

M1(F3) → M2(知识库) → M3(F6 抽取+图谱) → M4(F4 主链) → M5(F4 反思) → M6(F5) → M7(F7) → M8(F1/F2) → M9(F8) → M10(F10/F9) → M11(部署)。

---

## 12. 待确认事项（评审时请一并确认）

1. 联合审查是否必须支持 3 份（还是 2 份即可作为 MVP 最低要求）？—— 计划书按 3 份能力设计，PRD 默认支持 2-3 份任意组合。
2. 报告是否需要"评分卡"（如总分 0-100 与通过/不通过）？—— PRD 当前只做发现列表，不做综合评分。
3. demo 免 Key 限流 5 次/日是否合适？
4. 是否需要在 MVP 增加"报告分享链接"（只读，供监管/客户查看）？—— 当前为增强项。
