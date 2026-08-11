# LegalEye 法眼 — 数据合同（DATA_CONTRACT）

> 版本：v1.0
> 日期：2026-08-11
> 状态：定稿（M0 开工前确认；**前后端开发必须逐字遵守**）
> 关联文档：`docs/OPENCODE.md`、`docs/PRD.md`（API 摘要第 10 章）、`docs/ARCHITECTURE.md`
> 目的：定义 API schema 前后端契约、全局枚举字典、数据分级与字段来源，**根除前后端字段不统一**。

---

## 1. 目的与总原则

1. **单一事实源**：本文档是字段名/枚举值/JSON 结构的唯一权威。前端 TS 类型、后端 Pydantic schema、测试用例均以此为准，禁止各写一套。
2. **API 契约统一 camelCase**：HTTP/JSON 传输层全部 camelCase；后端 Python 模型内部 snake_case，序列化时经 alias 输出 camelCase；前端 TS 直接使用 camelCase。**双方都禁止在业务代码里手写另一套命名**。
3. **枚举值走字典**：所有枚举值见第 3 章字典，前端禁止魔法字符串，后端禁止散落字面量。
4. **LLM 输出必须过契约校验**：AI 生成字段（结论/图谱/矛盾项）必须经 Pydantic schema + 格式校验，不合格降级为"待补"，不得把脏数据写库。

---

## 2. 命名与序列化约定

| 层 | 命名 | 示例 |
|---|---|---|
| 后端 Python 模型/代码 | snake_case | `clause_ref`、`review_task` |
| HTTP/JSON 契约（本文件） | camelCase | `clauseRef`、`reviewTask` |
| 前端 TypeScript | camelCase | `clauseRef`、`reviewTask` |
| URL 路径 | kebab-case | `/export.md`、`/knowledge/laws` |
| 枚举值（字符串） | camelCase | `privacyPolicy`、`crossBorder` |

后端 Pydantic 落地方式（backend/app/schemas/）：
```python
from pydantic import BaseModel, ConfigDict, alias_generators

class APIModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=alias_generators.to_camel,   # 序列化输出 camelCase
        populate_by_name=True,                       # 允许 snake_case 入参
        use_enum_values=True,
    )
```
- 所有请求/响应模型继承 `APIModel`。
- **响应字段名不得偏离本文档**；新增字段必须先更新本文档（见第 8 章变更流程）。

---

## 3. 全局枚举字典（唯一事实源）

> 前端在 `frontend/src/api/types.ts` 定义为 `as const` 联合类型；后端在 `backend/app/core/enums.py` 定义 Enum；**两处必须与下表逐字一致**。

### 3.1 业务枚举
| 枚举 | 取值 | 说明 |
|---|---|---|
| `DocType` | `privacyPolicy` / `userAgreement` / `dpa` / `scc` | 文档类型 |
| `TaskType` | `single` / `multi` | 单文件 / 联合审查 |
| `TaskStatus` | `queued` / `running` / `done` / `failed` | 任务状态机 |
| `Dimension` | `D1` / `D2` / `D3` / `D4` / `D5` / `D6` / `crossConsistency` | 审查维度（D7/D8 增强项预留） |
| `Verdict` | `compliant` / `nonCompliant` / `pending` / `notApplicable` | 合规判定 |
| `RiskLevel` | `high` / `medium` / `low` | 风险等级 |
| `EntityRole` | `controller` / `processor` / `trustee` / `overseasReceiver` / `dataCategory` | 图谱实体角色 |
| `EdgeType` | `collect` / `store` / `share` / `entrust` / `crossBorder` / `anonymize` | 图谱边类型 |
| `Provider` | `bailian` / `deepseek` / `openai` / `anthropic` | LLM provider |
| `UserRole` | `user` / `admin` | 账号角色 |
| `ChatRole` | `user` / `assistant` | 聊天消息角色 |

### 3.2 常量与格式
| 常量 | 值/格式 | 说明 |
|---|---|---|
| `confidence` | 0-1 浮点 | 必填，LLM 输出后钳制到 [0,1] |
| `clauseRef` | `第?[一二三四五六七八九十\d]+条(第[一二三四五六七八九十\d]+款)?` | 正则校验，失败→pending |
| `statuteVersion` | `个人信息保护法(2021)` 形式 | 法规名(年份) |
| `baselineVersion` | `laws-v1.0-20260811` | 法规库版本号 |
| 文件限制 | PDF/Word ≤20MB、≤200 页 | 超限 400 |

### 3.3 SSE 事件类型（与 PRD F4 对齐）
`taskStatus` / `nodeStart` / `nodeEnd` / `findingCreated` / `graphUpdate` / `tokenUsage` / `error`

---

## 4. API 契约（全量 schema）

> 统一响应包裹：成功 `{"data": ...}`；失败 `{"error": {"code": string, "message": string}}`。HTTP 状态码语义见 PRD 异常清单 E1-E12。

### 4.1 Auth
```
POST /auth/register   {email: string, password: string} → {data: {token, user}}
POST /auth/login      {email, password} → {data: {token, user}}
GET  /auth/me         → {data: user}

User: {id: string, email: string, role: UserRole, createdAt: string(ISO)}
```

### 4.2 Models
```
GET  /models          → {data: ModelConfig[]}
POST /models          {provider: Provider, apiKey: string, model: string} → {data: ModelConfig}
PUT  /models/:id/activate → {data: ModelConfig}
POST /models/test     {provider, apiKey, model} → {data: {ok: boolean, message?: string}}

ModelConfig: {id: string, provider: Provider, model: string, apiKeyTail: string /*尾号4位*/, isActive: boolean}
```

### 4.3 Documents
```
POST /documents       (multipart: file, docType: DocType, sensitiveMode?: boolean)
                      → {data: Document}
POST /documents/from-url {url: string, docType: DocType} → {data: Document}

Document: {id: string, filename: string, docType: DocType, charCount: number,
           textPreview: string | null, sensitiveMode: boolean, createdAt: string}
```

### 4.4 Tasks
```
POST /tasks           {documentIds: string[], taskType: TaskType, modelConfigId?: string}
                      → {data: {taskId: string}}
GET  /tasks/:id       → {data: ReviewTask}
GET  /tasks           ?status=&taskType= → {data: ReviewTask[]}

ReviewTask: {id: string, taskType: TaskType, documentIds: string[], status: TaskStatus,
             progress: {node: string | null, percent: number}, createdAt: string,
             finishedAt: string | null, model: {provider: Provider, model: string} | null,
             tokenUsage: {inputTokens: number, outputTokens: number, costEst: number} | null,
             findingCount: number, highRiskCount: number}
```

### 4.5 SSE 事件流（GET /tasks/:id/events）
帧格式：`event: <EventType>\ndata: <JSON>\n\n`，事件数据：
```
taskStatus    {status, queuePosition?: number}
nodeStart     {node, nodeType: "orchestrator"|"extractor"|"dimension"|"critic"|"reporter"}
nodeEnd       {node, status: "ok"|"degraded"|"failed", findingsProduced?: number}
findingCreated{finding: ComplianceFinding}
graphUpdate   {graph: GraphPayload}
tokenUsage    {node, provider, model, inputTokens, outputTokens, costEst, latencyMs}
error         {message}
```

### 4.6 Chat（POST /tasks/:id/chat，SSE 增量文本）
```
请求 {message: string}
响应为 SSE 文本流；结束后发送 event: done；消息落库后可在任务详情回看。
ChatMessage: {id: string, role: ChatRole, content: string, createdAt: string,
              references?: string[] /* clauseRef 列表 */, taskId: string}
```

### 4.7 图谱（GET /graph/:taskId）
```
GraphPayload: {
  entities: [{id, name, role: EntityRole, isSensitive?: boolean}],
  edges: [{id, from: string, to: string, type: EdgeType,
           legalBasis?: string, isRisk: boolean}],
  riskPaths: [{id, path: string[], edges: string[], reason: string, level: RiskLevel}],
  suggestions: [{pathType: "securityAssessment"|"scc"|"certification"|"unknown",
                 advice: string, level: RiskLevel}]
}
```

### 4.8 结论 / 矛盾（GET /findings/:taskId）
```
ComplianceFinding: {id, taskId, documentId, dimension: Dimension, verdict: Verdict,
  level: RiskLevel, clauseRef: string, statuteVersion: string, description: string,
  remediation: string, confidence: number, needsHumanReview: boolean,
  evidence?: {text: string, charRange: [number, number]}}

CrossDocConflict: {id, taskId, declarationKey:
  "dataCategory"|"purpose"|"receivers"|"crossBorder"|"retention"|"rights",
  docA: {documentId, value, evidence: {text, charRange}},
  docB: {documentId, value, evidence: {text, charRange}},
  level: RiskLevel}
```

### 4.9 报告（GET /reports/:taskId, /reports/:taskId/export.md）
```
Report: {taskId, summary: string, baselineVersion: string, generatedAt: string,
  findingCount: number, highRiskCount: number,
  findings: ComplianceFinding[], crossDocConflicts?: CrossDocConflict[]}
```

### 4.10 知识库（admin）
```
GET  /knowledge/laws  ?statute=&version= → {data: LawBaseline[]}
POST /knowledge/laws/ingest {source: string} → {data: {taskId: string}} /* 异步 */
POST /knowledge/laws/search {query: string} → {data: {results: [{clauseRef, statuteVersion, articleText, score}]}}

LawBaseline: {id, statute: string, articleNo: string, articleText: string,
              effectiveDate: string, version: string, source: string}
```

---

## 5. 数据分级与访问矩阵

| 级别 | 定义 | 典型字段/资源 | 可见性 | 传输/存储要求 |
|---|---|---|---|---|
| **L0 公开** | 无敏感信息 | 错误码、枚举字典、公开条款号 | 任何人 | 无特殊 |
| **L1 内部（登录可见）** | 用户自己的业务数据 | 任务、文档元数据、图谱、报告、finding | 本人 + admin | HTTPS；数据库常规 |
| **L2 敏感** | 涉及隐私/凭据 | 用户邮箱、**API Key 密文**、文档原文（可选不持久化）、聊天内容 | 本人（Key 仅后端可解密） | Key 仅 Fernet 密文存储，绝不出 API；原文敏感模式仅内存 |
| **L3 机密（admin）** | 管理/版权/成本 | 法条原始文本（GB/T 版权）、LLMCallRecord（成本）、全用户数据 | 仅 admin | 不入 git；L3 接口 admin 校验 |

**前端规则**：
- 前端**永不接触** L2 的 Key 明文与文档原文全文（仅 textPreview 前 500 字）。
- L3 接口前端仅 admin 角色可见路由；服务端仍强制校验角色。

---

## 6. 字段来源标注与校验责任

> 每个字段标注来源，明确"谁保证它正确"。

| 来源 | 含义 | 责任 | 典型字段 |
|---|---|---|---|
| `USER_INPUT` | 用户填写/选择 | 前端校验 + 后端 Pydantic 再校验 | password、apiKey、docType、message、filename |
| `SYSTEM` | 系统生成，稳定 | 后端保证 | id、createdAt、status、charCount、apiKeyTail、tokenUsage |
| `LLM` | AI 生成，**需契约校验** | 后端 schema 校验 + 格式校验，失败降级"待补" | description、remediation、clauseRef、confidence、verdict、level、图谱实体/边、crossDocConflict |
| `KNOWLEDGE` | 来自法规/案例库 | 入库脚本保证 | statuteVersion、statute、articleText、effectiveDate、baselineVersion |

**LLM 字段强制校验清单（backend/app/schemas/validators.py）**：
- `clauseRef` 正则（3.2）失败 → verdict=pending + needsHumanReview=true；
- `confidence` 钳制 [0,1]；
- `dimension/verdict/level/role/edgeType` 必须命中枚举字典，未知值 → 丢弃该条 + 记录告警；
- 图谱实体/边去重（同 document+name+role 合并）。

---

## 7. 前端类型与使用约定

1. **类型集中**：`frontend/src/api/types.ts` 定义全部接口类型 + 枚举联合类型，与本文档逐字一致；**禁止在组件里内联定义与契约同名的类型**。
2. **枚举禁用魔法字符串**：
   ```ts
   export const DOC_TYPES = ['privacyPolicy','userAgreement','dpa','scc'] as const;
   export type DocType = typeof DOC_TYPES[number];
   ```
3. **API 封装**：`frontend/src/api/client.ts` 统一 `get/post/put`，自动解包 `{data}` 与 `{error}`，错误统一抛 `ApiError{code, message}`。
4. **SSE 消费**：`hooks/useSSE.ts` 按第 3.3 事件名分发到 store 回调；事件名变更必须同步本文档（红线 12）。
5. **展示映射**：`RiskLevel → RiskBadge` 配色/图标映射集中在 `lib/risk.ts`（见 DESIGN.md），组件不散落色值。

---

## 8. 变更流程

1. 任何 API 字段/枚举/事件变更，**先改本文档并 bump 版本**（v1.0 → v1.1…）。
2. 同步：后端 `schemas/`（Pydantic alias 自动 camelCase）→ 前端 `types.ts` + 相关 store/hook。
3. PR 描述注明"DATA_CONTRACT 变更"；CI 增加契约一致性检查（后端导出 schema JSON 与前端类型 diff，增强项）。
4. 破坏性变更（字段改名/删除）→ 前端先适配后合并，禁止前后端不同步上线。

---

## 9. 关键实体字段对照表（后端模型 → API → 前端）

| 后端模型字段（snake） | API/前端字段（camel） | 类型 | 来源 | 级别 |
|---|---|---|---|---|
| `ReviewTask.id / status / task_type` | `id / status / taskType` | string / enum | SYSTEM / USER_INPUT | L1 |
| `Document.filename / doc_type / char_count / text_preview` | `filename / docType / charCount / textPreview` | string / enum / number / string\|null | USER_INPUT / SYSTEM | L1 |
| `ComplianceFinding.clause_ref / statute_version` | `clauseRef / statuteVersion` | string | LLM + KNOWLEDGE | L1 |
| `ComplianceFinding.confidence / needs_human_review` | `confidence / needsHumanReview` | number / boolean | LLM | L1 |
| `DataFlowEntity.role / is_sensitive` | `role / isSensitive` | enum / boolean | LLM | L1 |
| `DataFlowEdge.edge_type → type / is_risk` | `type / isRisk` | enum / boolean | LLM + SYSTEM(R1-R4) | L1 |
| `ModelConfig.api_key_encrypted` | **永不出 API**（仅 `apiKeyTail`） | string | USER_INPUT | L2 |
| `LawBaseline.article_no / effective_date` | `articleNo / effectiveDate` | string | KNOWLEDGE | L1 |
| `LLMCallRecord`（内部） | 仅仪表盘聚合，不出明细 API | — | SYSTEM | L3 |

---

## 10. 评审自查清单

- [ ] 前后端均使用本文档字段名（全局搜索无 camelCase/snake_case 混用）
- [ ] 枚举值全部来自第 3 章字典，前端无魔法字符串
- [ ] 所有 API 响应符合 `{data | error}` 包裹
- [ ] LLM 字段校验清单已实现（validators.py），脏数据不落库
- [ ] 前端不出现 Key 明文 / 文档原文全文
- [ ] 新增字段已走变更流程并 bump 版本
