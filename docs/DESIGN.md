# LegalEye 法眼 — 前端视觉设计规范（DESIGN）

> 版本：v1.0
> 日期：2026-08-11
> 状态：定稿（开发 M3/M7 前端工作前评审）
> 关联文档：`docs/OPENCODE.md`（计划书）、`docs/PRD.md`（需求）、技术栈：React + Vite + TS + Tailwind + shadcn/ui + React Flow + ECharts

---

## 1. 设计目标与原则

LegalEye 是面向**出海企业数据合规负责人**的 B 端审查工具。界面不是娱乐产品，而是**每天被盯着读 8 小时的审计工具**——设计的首要任务是让用户信任它、看懂它、不疲劳。

四条铁律：

1. **可信高于炫技**：克制、精确、有秩序。任何"漂亮但可疑"的设计都是负债。
2. **信息密度为服务**：审查结论、条款引用、图谱关系是高密度信息，排版让它们一目了然，而非稀释。
3. **风险即视觉层级**：全站最高视觉权重永远属于"高风险"，其次是中风险，其余让位。
4. **数据流即品牌**：节点、边、网格、脉冲——"数据流动"是贯穿品牌、图谱、动效的统一视觉语言。

---

## 2. 美学方向：数据流之上的"法眼"

| 项 | 定调 |
|---|---|
| 方向 | **Precision Editorial（编辑式精密）**——彭博终端的数据密度 × 审计报告的庄重 × 瑞士银行年报的克制 |
| 风格关键词 | 精确 · 冷静 · 网格化 · 细线 · 墨蓝与纸白 · 等宽数字 · 红为警示 |
| 记忆点（差异化） | **数据脉冲**：审查运行时，编排画布与图谱的边上流动着光点——"看数据流过系统"。这是评审 5 秒内记住的东西 |
| 明确的非目标 | 不用紫渐变、玻璃拟态、大圆角糖果色、emoji 图标、插画吉祥物。不做"AI 味"通用模板 |
| 背景隐喻 | 1px 细网格（数据网格）+ 点阵画布（React Flow）——用户始终站在"数据"之上 |

---

## 3. 品牌视觉

- **Logo 概念**："法眼" = 一只由数据节点构成的监视之瞳。圆形外环（监管/边界）+ 中心瞳孔（凝视/审查）+ 环上 4 个节点（四个可视化/合规维度）。
- **图形**：SVG 实现，圆环 + 中心实心圆 + 等距节点点；favicon 用同形 32px 简化版。
- **品牌标使用**：登录页居中、侧边栏顶部 32px、报告页眉 24px；品牌标旁字标 "LegalEye 法眼"（IBM Plex Sans 600，ink 色）。
- **页面底纹**：登录页与空态使用 CSS 细网格背景（`linear-gradient` 1px 线，brand-100 8% 透明），呼应"数据网格"。

---

## 4. 色彩系统

### 4.1 品牌色（法眼靛蓝，自定义色板）
| Token | 值 | 用途 |
|---|---|---|
| brand-50 | #EEF1FD | 选中底色、浅强调底 |
| brand-100 | #E0E5FA | hover 底色 |
| brand-200 | #C7CEF5 | 边框强调 |
| brand-400 | #7B89E8 | 链接 hover |
| brand-500 | #5B6DF0 | 图标/选中 |
| **brand-600（primary）** | **#4055E0** | 主按钮、主链接、焦点 ring |
| brand-700 | #3346C4 | 主按钮 hover |
| brand-800 | #2A3A9E | 按下/深底文字 |

### 4.2 语义色（合规风险——全站最高语义权重）
| Token | 值 | 底/边 | 用途 | 图标 |
|---|---|---|---|---|
| risk-high | #B42318（文字）/ #D92D20（主） | #FEF3F2 / #FDA29B | 高风险结论、风险边、熔断 | 实心三角 ⚠ 或实心圆点 |
| risk-medium | #DC6803 | #FFFAEB / #FEC84B | 中风险、需关注 | 半空心圆 ● |
| risk-low | #1570EF | #EFF8FF / #84CAFF | 低风险、提示 | 空心圆 ○ |
| risk-ok | #12B76A | #ECFDF3 / #6CE9A6 | 合规、通过、成功 | 对勾 ✓ |
| risk-pending | #98A2B3 | #F2F4F7 / #D0D5DD | 待补、信息缺失、未知 | 虚线圆 ⟳ |

> **颜色不唯一传达**：风险等级必须同时以 图标 + 文字 呈现（RiskBadge），色觉障碍用户不丢失信息。
> **对比度**：正文级红色一律用深值 #B42318（在纸白上 ≥4.5:1）；#D92D20 仅用于图形/描边。

### 4.3 中性色（结构）
| Token | 值 | 用途 |
|---|---|---|
| paper | #F7F7F5 | 页面背景（微暖纸白） |
| surface | #FFFFFF | 卡片/面板 |
| ink-900 | #0E1526 | 主文字（近黑蓝） |
| ink-600 | #475069 | 次要文字 |
| ink-400 | #8A93A6 | 三级文字/占位 |
| line-200 | #E3E7EF | 边框/分隔线（1px） |
| line-100 | #EDF0F5 | 更弱分隔 |

### 4.4 图谱专用色（节点角色 / 边类型）
| 角色 | 色 | 说明 |
|---|---|---|
| 控制者 controller | 蓝 #1570EF | 主蓝，信任 |
| 处理者 processor | 青 #0E9384 | 中性操作 |
| 受托方 trustee | 紫 #7A5AF8 | 委托关系 |
| 境外接收方 overseas_receiver | 红 #D92D20 | **出境=风险敏感，天然警示** |
| 数据类别 data_category | 墨灰 #475467；敏感类别描边转红 #D92D20 | 数据主体 |

| 边类型 | 色 | 样式 |
|---|---|---|
| collect 收集 | #1570EF | 实线 |
| store 存储 | #98A2B3 | 实线 |
| share 共享 | #0E9384 | 实线 |
| entrust 委托 | #7A5AF8 | 虚线 |
| cross_border 跨境 | #D92D20 | 实线加粗 + 运行期脉冲 |
| anonymize 匿名化 | #12B76A | 点线 |
| **风险边（is_risk）** | #D92D20 | 加粗 + 脉冲描边动画 |

---

## 5. 字体排印

| 用途 | 字体 | 引入 |
|---|---|---|
| UI 与数字正文 | **IBM Plex Sans**（拉丁/数字）+ 系统中文栈 | `@fontsource/ibm-plex-sans` |
| 条款号 / token 数 / 时间 / diff / 代码 | **IBM Plex Mono** | `@fontsource/ibm-plex-mono` |
| 中文回退 | `-apple-system, "PingFang SC", "Microsoft YaHei", "Noto Sans SC", sans-serif` | 系统 |

> 选 IBM Plex 而非 Inter：其"IBM 工程/企业气质"与监管级可信定位高度一致，避免通用 AI 模板感。

字号阶梯（B 端密集信息，**正文默认 14px**）：
| 阶梯 | 大小/行高 | 用途 |
|---|---|---|
| text-xs | 12 / 16 | 辅助说明、表格次要列 |
| **text-sm（默认）** | **14 / 20** | 正文、表格、表单 |
| text-base | 16 / 24 | 卡片标题、报告正文起始 |
| text-lg | 18 / 26 | 区块标题 |
| text-xl | 20 / 28 | 页面标题 |
| text-2xl | 24 / 32 | 报告大标题 |
| text-3xl | 30 / 38 | 登录页品牌标题 |

字重：仅 400 / 500 / 600 三档（600 只用于关键标题与统计数字）。**数字一律 `tabular-nums`**（token 数、时间、金额对齐）。

---

## 6. 间距 / 圆角 / 边框 / 阴影

- **间距**：4px 网格。token：`4/8/12/16/20/24/32/40/48/64`。卡片内 padding 统一 20px；面板间 gap 16px。
- **圆角**：`sm 4`（输入/按钮）/ `md 8`（卡片/面板）/ `lg 12`（大卡片/弹窗）/ `pill 999`（标签胶囊）。
- **边框**：默认 `1px solid line-200`；分割线 `line-100`。层级优先靠"背景差 + 边框"，而非阴影。
- **阴影**（极克制，仅浮动层）：
  - `shadow-xs: 0 1px 2px rgba(14,21,38,.05)`
  - `shadow-sm: 0 2px 6px rgba(14,21,38,.06)`
  - `shadow-lg: 0 12px 32px rgba(14,21,38,.12)`（仅弹窗/抽屉）

---

## 7. 布局系统

### 7.1 应用壳
```
┌────────┬────────────────────────────────┐
│ 侧边栏 │  顶栏（面包屑 · 模型切换 · 用户）   │
│ 232px  ├────────────────────────────────┤
│(可折叠 │                                │
│ 至68px)│         内容区（路由页面）          │
└────────┴────────────────────────────────┘
```
- 侧边栏：Logo + 导航（任务列表 / 新建审查 / 模型配置 / 知识库(admin) / 设置）；选中项 brand-50 底 + brand-600 左竖线 2px；折叠态仅图标。
- 顶栏 56px：左面包屑，右模型状态 chip（当前 provider + 模型名，mono）+ 用户菜单。
- 断点：`≥1440` 完整四栏；`1280-1439` 聊天栏可折叠；`<1280` 聊天栏默认收起（浮层展开）。

### 7.2 审查工作台（核心页面，四块可视化）
```
┌─────────────────────────────────────────────┐
│ 仪表盘条 72px（耗时 | token | 发现数 | 高风险数） │
├───────────┬─────────────────────────────────┤
│ 聊天栏     │  Tab 切换：[编排画布] [数据流图谱]   │
│ 320px     │  主工作区（React Flow 画布/图谱）    │
│（SSE流式） │                                   │
└───────────┴─────────────────────────────────┘
```
- **布局决策**：仪表盘为顶部横条；画布与图谱共用主区以 Tab 切换（同屏左右分栏为 ≥1600px 可选增强）——保证 1366px 笔记本上画布仍有足够操作空间。
- 任务运行中：仪表盘 4 个 StatCard 实时刷新；聊天栏流式滚动；画布节点状态着色；图谱 Tab 自动切到"运行中视图"（风险路径实时高亮）。

### 7.3 报告页（编辑式长文）
- 内容列 `max-width 820px` 居中；`≥1280` 右侧固定目录（维度锚点 + 高风险数）；顶部工具条（导出 Markdown / 打印）。
- 跨文档矛盾区：红色警示卡片组，独立于维度分组之上。

---

## 8. 组件规范（shadcn/ui 定制点 + 专属组件）

通用原则：**shadcn/ui 基础组件直接用，定制仅限颜色/圆角 token**；专属组件按本规范新建。

| 组件 | 规范 |
|---|---|
| Button | 主按钮 brand-600→hover 700；次要 outline（白底+line 边框+ink-600 字）；危险按钮 risk-high；`h-9 px-4 rounded-md text-sm` |
| Card | `rounded-lg border line-200 bg-surface`，无阴影；头部 padding 20 + 底部 20 |
| Badge | 见 RiskBadge；普通 Badge 用 neutral |
| Table | 表头 ink-600 12px 500 字；行高 52px；hover 行 paper 底；分隔线 line-100 |
| Input/Select | `h-9 rounded-md border line-200 focus:ring-2 ring-brand-600/30 focus:border-brand-600` |
| Tabs | 下划线式（底部 2px brand-600 指示条） |
| Dialog/Drawer | 阴影 shadow-lg；遮罩 ink-900/40；抽屉 400px |
| Toast | 右上角；错误用 risk-high 左竖线 + 图标 |
| Skeleton | 优先骨架屏（shadcn Skeleton）替代 spinner |

**专属组件**：
1. **RiskBadge**：`{label, level}` 胶囊（pill），配色 = 4.2 语义色底/字/边 + 图标 + 文字（颜色非唯一传达）。
2. **ClauseRef**：条款引用 chip（IBM Plex Mono 13px + 链接 icon）；hover 弹 tooltip 显示法条原文前 80 字；点击跳知识库原文（新标签）。
3. **DiffView**：整改 diff 视图——删除行红底 `#FEF3F2` 左竖线、新增行绿底 `#ECFDF3`；行内高亮用 `<del>/<ins>` 样式。
4. **GraphCanvas**：React Flow 封装（见第 9 章）。
5. **ChatStream**：气泡列表（用户右对齐 brand-600 底白字 / 系统左对齐 surface+边框）；流式时末气泡带 8px 光标竖线动画；markdown 渲染 + ClauseRef 组件复用。
6. **StatCard**：`{label, value, trend?}`——label 12px ink-400；value 20px 600 字 tabular-nums；可带颜色状态点。
7. **TaskStatusBar**：任务进度条 + 节点状态点序列（待办灰 / 运行中蓝脉冲 / 完成绿 / 失败红）。

---

## 9. 可视化规范（差异化核心）

### 9.1 编排画布（React Flow，LangGraph 图）
- 画布背景：点阵 grid（`{dots: true, lineColor: line-100}`），纸白底。
- 节点：圆角矩形 180×56，白底 + 1.5px 角色色描边；内部：图标 + 智能体名（13px 500）+ 状态点。
- 节点状态着色：待运行灰 / 运行中 brand-500 描边 + **脉冲动画** / 完成绿对勾 / 失败红叉。
- 边：`smoothstep`，默认 line-200；数据流边运行中显示**流动光点**（`dashArray + dashOffset` 动画，1.2s 循环）——"数据脉冲"记忆点。
- 迷你地图 + 缩放控制（React Flow Controls 默认样式微调）。

### 9.2 数据流图谱（React Flow，创新可视化）
- 节点：胶囊形（宽按文本自适应，≥120px），填充 = 角色色 8% 透明 + 1.5px 角色色描边；敏感数据类别加"火苗"角标。
- 边：类型配色见 4.4；**风险边（is_risk / cross_border 未合规）**：红 2.5px + 虚线 → 实线脉冲描边动画（`stroke-dashoffset` 流动）。
- 出境可达路径（R1 推理结果）：路径上所有边红色高亮 + 端到端光点流动；节点点击 → 右侧抽屉（角色、原文片段、相关条款 ClauseRef）。
- 布局：`dagre` 层级布局（自动），手拖后布局冻结；无环图优先。

### 9.3 仪表盘（ECharts）
- 统一浅色主题：`textStyle.color=ink-600, axisLine=line-100, splitLine=line-100`。
- 图表：风险分布环形图（语义四色）、各维度发现数条形（品牌色，高风险柱红）、token/耗时折线（brand-600）。
- 数字一律 tabular-nums；tooltip 深色（ink-900 底白字）。

---

## 10. 页面设计（9 页）

| 页面 | 结构要点 |
|---|---|
| `/login` `/register` | 居中 400px 卡片；背景细网格 + 角落法眼图标；品牌标题 IBM Plex Sans 600 |
| `/tasks` 任务列表 | 顶栏：标题 + "新建审查"主按钮；筛选（状态/类型）；表格（文档名、类型、状态 Badge、耗时、时间、操作）；空态：网格背景 + 引导文案 + CTA |
| `/tasks/:id` 审查工作台 | 7.2 四栏布局；运行中实时联动 |
| `/reports/:id` 报告页 | 7.3 编辑式长文；目录锚点；跨文档矛盾红色警示区；条款引用 ClauseRef |
| `/settings/models` | provider 卡片网格（百炼/DeepSeek/OpenAI/Anthropic，各含"国内/境外"标签）；表单（Key 显示尾号4位脱敏 + 测试按钮）；激活态卡片 brand 描边 |
| `/admin/knowledge`（admin） | 法条表格（法规/条号/版本/生效日）+ 版本筛选 + "重新入库"按钮（异步，TaskStatusBar） |
| `/settings/account` | 账号信息、安全（改密）、数据（注销） |
| `/404` | 网格背景 + 法眼图标 + "未找到该页面" + 返回按钮 |
| 全局错误/断线 | SSE 断线：顶栏黄色警示条 + 自动重连计数；崩溃页：居中错误卡 + 重载按钮 |

---

## 11. 交互状态规范

- **加载**：优先骨架屏（表格/卡片）；图谱节点"出现"动画（scale 0.96→1 + fade，150ms，按拓扑顺序 stagger 30ms）。
- **空态**：图标（线性，非 emoji）+ 一句话说明 + 一个 CTA。
- **错误**：内联错误文案（表单）+ Toast（操作失败）+ 页面级错误卡（含错误码与重试）。
- **流式输出**：聊天/报告流式时光标动画；已完成内容即时稳定（不重排抖动）。

---

## 12. 动效原则

| 场景 | 时长 | 缓动 |
|---|---|---|
| 微交互（hover/focus/按压） | 150ms | `ease-out` |
| 面板/抽屉/Toast | 300ms | `cubic-bezier(.4,0,.2,1)` |
| 页面/分区 staggered reveal | 600ms 总（每项 120ms 延迟） | 同上 |

**高光时刻（刻意做，其余从简）**：
1. 审查运行 → 图谱/画布"数据脉冲"（光点沿边流动）——品牌记忆点。
2. 高风险结论产出 → RiskBadge 出现时红色微脉冲（1 次，600ms）。
3. 工作台首屏 → 四区 staggered 淡入上移 8px。

**`prefers-reduced-motion: reduce` 时全部动画禁用**（仅保留状态色变化）。

---

## 13. 可访问性

- 对比度：正文 ≥4.5:1（红文字用 #B42318）；图形/图标 ≥3:1。
- 焦点：全局 `focus-visible` 2px brand-600 ring；图谱节点可 Tab 遍历 + Enter 选中 + Esc 关闭抽屉。
- 颜色非唯一传达：RiskBadge 带图标与文字；图表高风险柱同时加深加粗。
- 语义标签：图表提供 `aria-label` 数据摘要；SSE 流式区域 `aria-live="polite"`。
- 字号可缩放：布局在 125% 缩放下不破版（断点自适应）。

---

## 14. 设计 Token 落地（开发对接）

### 14.1 Tailwind config 扩展（tailwind.config.ts 摘要）
```ts
extend: {
  colors: {
    brand: { 50:'#EEF1FD',100:'#E0E5FA',200:'#C7CEF5',400:'#7B89E8',
             500:'#5B6DF0',600:'#4055E0',700:'#3346C4',800:'#2A3A9E' },
    ink:   { 900:'#0E1526',600:'#475069',400:'#8A93A6' },
    paper: '#F7F7F5',
    risk:  { high:'#D92D20', highText:'#B42318', medium:'#DC6803',
             low:'#1570EF', ok:'#12B76A', pending:'#98A2B3' },
  },
  fontFamily: {
    sans: ['"IBM Plex Sans"','-apple-system','"PingFang SC"','"Microsoft YaHei"','sans-serif'],
    mono: ['"IBM Plex Mono"','ui-monospace','monospace'],
  },
  boxShadow: { xs:'0 1px 2px rgba(14,21,38,.05)', sm:'0 2px 6px rgba(14,21,38,.06)',
               lg:'0 12px 32px rgba(14,21,38,.12)' },
}
```

### 14.2 shadcn/ui CSS 变量映射（globals.css 摘要）
```css
:root {
  --background: #F7F7F5;  --foreground: #0E1526;
  --card: #FFFFFF;        --card-foreground: #0E1526;
  --primary: #4055E0;     --primary-foreground: #FFFFFF;
  --secondary: #EEF1FD;   --secondary-foreground: #3346C4;
  --muted: #F2F4F7;       --muted-foreground: #8A93A6;
  --border: #E3E7EF;      --input: #E3E7EF;
  --destructive: #D92D20; --destructive-foreground: #FFFFFF;
  --ring: #4055E0;
}
```

### 14.3 React Flow 定制点
- `nodeTypes`：`orchestrator / extractor / dimension / critic / reporter`（画布）、`entity / edge-type`（图谱）。
- `edgeTypes`：`dataEdge`（脉冲边）、`riskEdge`（红色脉冲风险边）。
- 全局 `colorMode="light"`；背景 `dots` 点阵；`proOptions={{hideAttribution:true}}`。

### 14.4 依赖清单（前端 package 新增）
`@fontsource/ibm-plex-sans`、`@fontsource/ibm-plex-mono`、`@xyflow/react`（React Flow v12）、`echarts` + `echarts-for-react`、`dagre`（图谱自动布局）、`diff-match-patch`（diff 展示）、shadcn/ui 基础件。

---

## 15. 评审自查清单（实现后逐项过）

- [ ] 全站无紫渐变/玻璃拟态/大圆角糖果色
- [ ] 风险 Badge 均含图标+文字（不依赖颜色）
- [ ] 正文红使用 #B42318（非 #D92D20）
- [ ] 数字全部 tabular-nums
- [ ] 图谱风险路径红色脉冲高亮可见
- [ ] 审查运行"数据脉冲"动效存在且可被 prefers-reduced-motion 关闭
- [ ] 1440 / 1366 / 1280 / 1024 四个宽度下工作台不破版
- [ ] 键盘可完整操作图谱与全部表单
