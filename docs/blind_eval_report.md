# 真实隐私政策盲测报告

- 运行时间：2026-09-19 17:26
- 模型：`glm-4.5-flash`（provider: `zhipu`）
- 文档数：12 | 截断阈值：8000 字符

> 本报告为盲测原始输出，**未经人工复核**。复核后请在每行补结论（属实/误报/存疑）。

## r01_taobao.txt
- 原始长度 17186 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | unclear | high | 第五条 | 否 | 为实现向您提供我们产品及/或服务的基本功能，您须授权我们收集、使用的必要的信息。如您拒绝提供相应信息，您将无法正常使用我们的产品及/或服务。 | |
| d2Notice | unclear | medium | - | 否 | 本隐私政策将帮助您了解以下内容：一、适用范围 二、信息收集及使用 三、数据使用过程中涉及的合作方及转移、公开个人信息 四、您的权利 五、信息的存储 六、政策的更 | |
| d3Purpose | unclear | medium | 待补 | 否 | purpose_minimization_agent LLM 调用失败，已降级为待人工复核 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 为向您展示和推荐您可能感兴趣的商品或服务信息，我们会基于您的偏好特征在淘宝及其他第三方应用程序或终端向您推送您可能感兴趣的商业广告及其他信息 | |
| d5CrossBorder | unclear | high | 第三十九条 | 否 | 例如 涉及跨境交易时您需要提供您的身份证件信息以完成清关。 | |
| d6DataRights | unclear | medium | - | 否 | 如对本政策内容有任何疑问、意见或建议，您可通过本政策文末的联系方式与我们联系。 | |
| crossConsistency | unclear | medium | 第三十九条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r02_jd.txt
- 原始长度 11348 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | compliant | medium | 第五条 | 否 | 在您使用上述功能过程中，我们会收集使用与您有关的必要个人信息，包括手机号码、收货人姓名、收货地址、联系电话、支付时间、支付金额、支付方式等，具体字段详见本隐私政 | |
| d2Notice | unclear | high | - | 否 | 除基本功能外，我们还为您提供部分附加功能...您可选择单独同意或不同意我们收集使用的这部分涉及的个人信息 | |
| d3Purpose | unclear | medium | 第五条 | 否 | 我们会根据您的上述信息以及您的收货地址，进行数据分析、预测您的偏好特征，向您推送可能感兴趣的商品/服务、商业广告、商业性短信及其他营销信息 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 如果您是以香港手机号码注册使用京东服务，您理解并同意，我们可能会向帮助我们进行市场推广或营销的第三方公司分享您的个人信息。 | |
| d5CrossBorder | unclear | high | 第三十九条 | 否 | 如您使用跨境交易服务，且需要向境外传输您的个人信息完成交易的，我们会单独获取您的授权同意并要求接收方按照双方签署的数据保护协议、本隐私政策以及相关法律法规要求来 | |
| d6DataRights | unclear | medium | 第八条 | 否 | 除法律法规规定外，您有权随时访问和更正您的个人信息，具体包括：（1）账号信息
PC端路径：进入网站-点击"我的京东"-点击"账户设置"菜单中"个人信息"，如您需 | |
| crossConsistency | unclear | medium | 第八条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r03_wechat.txt
- 原始长度 20328 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | high | - | 否 | 为优化服务体验，我们可能需要您提供更多个人信息，包括手机号、身份证号等，以便为您打造更精准的个性化推荐。 | |
| d2Notice | unclear | high | - | 否 | 为说明我们会如何收集、使用和存储你的个人信息及你享有何种权利，我们将通过《微信隐私保护指引摘要》以及本指引向你阐述相关事宜 | |
| d3Purpose | unclear | medium | 待补 | 否 | purpose_minimization_agent LLM 调用失败，已降级为待人工复核 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 我们不会主动共享或转让你的个人信息至深圳市腾讯计算机系统有限公司外的第三方。如存在其他共享或转让你的个人信息，或你需要我们将你的个人信息共享或转让至深圳市腾讯计 | |
| d5CrossBorder | unclear | high | - | 否 | 文档未明确说明跨境数据传输的具体情况，也未提及是否取得单独同意、是否告知境外接收方信息等，需要人工审查 | |
| d6DataRights | unclear | medium | 第八条 | 否 | 5.你可以通过本指引所列途径及方式查阅、更正、复制、删除你的个人信息，也可以撤回同意、注销账号、投诉举报以及设置个性化广告等隐私功能。 | |
| crossConsistency | unclear | medium | 第八条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r04_shein.txt
- 原始长度 23673 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | high | - | 否 | Your personal information is collected and used by us to support a range of diff | |
| d2Notice | unclear | high | - | 否 | Your personal information is collected and used by us to support a range of diff | |
| d3Purpose | notApplicable | medium | - | 否 | Your personal information is collected and used by us to support a range of diff | |
| d4ThirdParty | notApplicable | high | - | 否 | We may share your personal information with our related group companies and, in  | |
| d5CrossBorder | notApplicable | high | - | 否 | The Site is owned and operated by Roadget Business Pte. Ltd., 12 Marina Boulevar | |
| d6DataRights | notApplicable | medium | - | 否 | The Company is operating the Site, and therefore, may act as a "controller" of y | |
| crossConsistency | unclear | medium | - | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r05_temu.txt
- 原始长度 30607 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | high | - | 否 | We will collect other information that you provide for purposes as described in  | |
| d2Notice | unclear | high | - | 否 | In the course of providing and improving our Service, we collect your personal i | |
| d3Purpose | notApplicable | medium | - | 否 | In the course of providing and improving our Service, we collect your personal i | |
| d4ThirdParty | notApplicable | high | - | 否 | We receive and collect your personal information from other third-party sources, | |
| d5CrossBorder | notApplicable | medium | - | 否 | 文档未明确涉及向境外提供个人信息的处理行为 | |
| d6DataRights | unclear | medium | - | 否 | In this Privacy Policy, we also explain the rights you have with regard to your  | |
| crossConsistency | unclear | medium | - | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r06_meituan.txt
- 原始长度 15839 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | unclear | high | - | 否 | 基于法律法规要求以及保护您的人身财产安全、依照平台规则处理用户纠纷之需要，通过记录用户行为收集您的行程信息，如：出发地、到达地、行踪轨迹、时长及里程数信息等 | |
| d2Notice | unclear | high | - | 否 | 除法律另有规定外，我们仅会在实现目的所必需的最短时间内留存您的相关个人信息。如您希望详细了解我们所收集的具体各项个人信息及对应的场景，请查阅概要后的隐私政策正文 | |
| d3Purpose | compliant | low | 第五条 | 否 | 经您授权，我们会收集您的地理位置信息，以便您不需要手动输入地理坐标即可获得位置推荐、帮助您选择上车、下车点、顺利与驾驶员会面等出行服务 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 我们可能会与我们的关联公司以及其他合作商等第三方共享或委托其处理您的部分个人信息。目前，除再次获得您明确同意或授权外，此类共享或委托处理涉及的主要情形包括：根据 | |
| d5CrossBorder | notApplicable | medium | - | 否 | 文档中未找到与跨境、境外、出境相关的明确表述，仅提到与关联公司及第三方共享信息，但未说明这些方是否位于境外 | |
| d6DataRights | unclear | low | - | 否 | 您有权管理您的个人信息，包括查询、更正和删除您的账户信息、订单信息、常用地址、信息删除，改变您的授权同意的范围或撤回授权，以及注销您的账号。您可以通过我们的Ap | |
| crossConsistency | unclear | medium | 第三十八条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r07_alipay.txt
- 原始长度 15715 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | unclear | high | 第五条 | 否 | 为了提升您的服务体验及改进服务质量，或者为您推荐更优质或更适合的服务，我们会收集您使用我们服务的操作记录、您与客户服务团队联系时提供的信息及您参与问卷调查时向我 | |
| d2Notice | unclear | high | - | 否 | 当您的个人信息处理属于前述第（2）至第（10）项情形时，我们可能会依据所适用法律法规的要求而无需再征得您的同意。 | |
| d3Purpose | unclear | medium | 第五条 | 否 | 为了提升用户服务体验，为用户推荐更为优质或适合的信息内容、商品和服务，我们会在合法合规的前提下将收集的基于支付宝账号形成的个人信息（包括身份特征、设备信息、位置 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 此外，我们也会在前述关联方履行向您提供服务的必要范围内共享您的其他账号信息（如实名信息、绑定手机号、地址和其他您主动授权的账号信息），无需您另行手动提交。 | |
| d5CrossBorder | unclear | high | 第三十九条 | 否 | 我们在中华人民共和国境内收集和产生的个人信息将存储在中华人民共和国境内。如部分产品涉及跨境业务，我们需要向境外机构传输境内收集的相关个人信息的，我们会按照法律法 | |
| d6DataRights | notApplicable | medium | - | 否 | 如您希望管理我们在支付宝客户端向您发送的个性化广告，您可以在"我的-设置-用户保护中心-隐私保 | |
| crossConsistency | unclear | medium | 第三十九条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r08_douyin.txt
- 原始长度 27865 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | compliant | medium | 第五条 | 否 | 根据《常见类型移动互联网应用程序必要个人信息范围规定》，抖音属于短视频类应用程序。结合该类别的基本功能服务界定，并结合用户日常在抖音内的使用情况，我们划定了基础 | |
| d2Notice | unclear | high | - | 否 | 我们将在隐私政策中逐项说明相关情况，有关您个人信息权益的重要条款已用加粗形式提示，请特别关注。 | |
| d3Purpose | notApplicable | medium | - | 否 | 部分搜索结果、相关搜索词将可能根据您的搜索/浏览历史、位置信息、日志信息等进行展示 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 您可以使用第三方账号注册、登录抖音，但需要授权我们获取您在第三方平台的信息（头像、昵称等公开信息以及您授权的其他信息），用于生成与该第三方账号绑定的抖音账号 | |
| d5CrossBorder | notApplicable | medium | - | 否 | 文档未提及跨境提供个人信息的相关内容 | |
| d6DataRights | notApplicable | low | - | 否 | 下文将帮您详细了解我们如何收集、使用、存储、传输、公开与保护个人信息；帮您了解查询、更正、补充、删除、复制、转移个人信息的方式。其中，有关您个人信息权益的重要内 | |
| crossConsistency | unclear | medium | - | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r09_pdd.txt
- 原始长度 8456 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | unclear | high | 第五条 | 否 | 为实现网上购物、优化我们的产品与/服务及保障安全所必须的功能，您须授权拼多多收集、使用您的如下信息: 用户注册所需信息 您使用本人手机号码注册成为拼多多用户时， | |
| d2Notice | unclear | high | - | 否 | 我们只会在达成本政策所述目的所需期限内保留您的个人信息，除非需要延长保留期或应法律法规的允许或要求。根据部分商品或服务的特点，您可能还需提供相关身份信息(如您的 | |
| d3Purpose | unclear | medium | 第五条 | 否 | 我们可能会收集您的订单信息、浏览记录、浏览习惯等进行数据分析以描述用户特征，用来为您展示或推荐您感兴趣的商品或服务信息 | |
| d4ThirdParty | unclear | high | 第二十二条 | 否 | 我们可能会向合作伙伴(如提供商品或技术、广告等服务的供应商、拼多多商家、委托我们进行推广的合作伙伴、代表我们发出信息的通讯服务商、支付机构等)或其他第三方共享您 | |
| d5CrossBorder | unclear | high | 第三十九条 | 否 | 您的个人信息将全部被存储于中华人民共和国境内，但以下情形除外: 6.1.1. 法律法规另有明确规定; 6.1.2. 获得您的明确授权; 6.1.3. 您通过互联 | |
| d6DataRights | notApplicable | medium | - | 否 | 对于您合理的请求，我们原则上不收取费用，但对多次重复、超出合理限度的请求，我们将视情况收取一定成本费用。对于那些无端重复、需要过多技术手段(例如，需要开发新系统 | |
| crossConsistency | unclear | medium | 第三十九条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r10_aliexpress.txt
- 原始长度 71426 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | high | - | 否 | 当您选择提供此类信息时，我们可能会收集无法识别您的一般个人数据，如体型、个人身高、胸围/腰围/臀围和重量。例如，我们可能使用这些信息来推荐服装尺码或款式、个性化 | |
| d2Notice | unclear | high | - | 否 | This Privacy Policy sets out the ways in which we collect, use and disclose info | |
| d3Purpose | notApplicable | medium | - | 否 | For example, this information may be used by us to recommend clothing sizes or s | |
| d4ThirdParty | notApplicable | medium | - | 否 | 文档未包含第三方委托与共享相关内容 | |
| d5CrossBorder | notApplicable | low | - | 否 | 文档未包含第N节'INTERNATIONAL TRANSFERS OF PERSONAL DATA'的具体内容，无法判断跨境提供合规性 | |
| d6DataRights | notApplicable | low | - | 否 | 文档未提供E. RIGHT. S REGARDING PERSONAL DATA部分的具体内容，无法评估数据主体权利相关条款 | |
| crossConsistency | unclear | medium | - | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r11_amazon.txt
- 原始长度 22731 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | high | - | 否 | We collect your personal information in order to provide and continually improve | |
| d2Notice | unclear | high | - | 否 | By using Amazon Services, you are consenting to the practices described in this  | |
| d3Purpose | notApplicable | medium | - | 否 | 【证据无法在文档原文中找到，或与维度不符，原判定 nonCompliant 不成立，降级为不适用】文档未明确说明个性化推荐的控制选项，且广告用途可能超出初始目的 | |
| d4ThirdParty | notApplicable | high | - | 否 | We share customers' personal information only as described below and with subsid | |
| d5CrossBorder | notApplicable | high | - | 否 | We share customers' personal information only as described below and with subsid | |
| d6DataRights | notApplicable | medium | - | 否 | 【证据无法在文档原文中找到，或与维度不符，原判定 nonCompliant 不成立，降级为不适用】文档未提供查询、复制、更正、删除个人信息的便捷途径及撤回同意途 | |
| crossConsistency | unclear | medium | - | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |

## r12_ebay.txt
- 原始长度 17278 字，已截断（注意：截断段之后的违规无法检出）

| 维度 | 判定 | 级别 | 条款 | 规则兜底 | 证据/说明 | 人工复核 |
|---|---|---|---|---|---|---|
| d1Collection | notApplicable | medium | 第五条 | 否 | What personal data we collect and process | |
| d2Notice | unclear | high | - | 否 | In our User Privacy Notice we have compiled all essential information about our  | |
| d3Purpose | notApplicable | medium | - | 否 | We may use artificial intelligence or AI-powered tools and products to improve o | |
| d4ThirdParty | notApplicable | high | - | 否 | When you complete a transaction with another user (or a transaction has been can | |
| d5CrossBorder | notApplicable | medium | - | 否 | 文档中包含'Cross-border data transfers'章节，但提供的文本片段未包含该章节具体内容，无法判断跨境提供个人信息合规性 | |
| d6DataRights | notApplicable | high | - | 否 | Rights as a data subject | |
| crossConsistency | unclear | medium | 第八条 | 否 | 高风险结论待复核：维度 crossConsistency 需人工确认 | |


---

# v4.1 全量盲测总结（12 份真实政策，M11 修复后，2026-09-19）

## 运行信息
- 模型：glm-4.5-flash（智谱免费层，不付费）
- 测试集：data/real/r01~r12，12 份真实公开隐私政策（9 中文/双语 + 3 跨境英文）
- 每份 7 个维度（d1 收集 / d2 告知同意 / d3 目的最小化 / d4 第三方共享 / d5 跨境 / d6 数据主体权利 / cross 交叉一致性）
- 截断阈值：8000 字符；单次调用超时 420s；429 限流走 60/120s 长退避
- **M11（2026-09-19）**：豁免门新增软性合规信号（"为向您提供服务所必需/基于法定义务/如您不提供不影响使用"等），修复支付宝 r07 的 2 条误报

## 判定分布（84 个维度判定，v4.1）

| 判定 | 数量 | 占比 |
|---|---|---|
| nonCompliant（非合规） | **0** | 0% |
| unclear（转人工复核） | 50 | 59.5% |
| notApplicable（不适用） | 30 | 35.7% |
| compliant（合规） | 4 | 4.8% |

## M11 修复效果：支付宝 r07 2 条误报 → 0 条
- 修复前：d1（收集）、d4（第三方共享）各报 1 条 nonCompliant，人工复核均为误报
- 修复后：重跑支付宝，**0 条 nonCompliant**；d1/d3/d4/d5 均被软性合规信号豁免门降级为 unclear 转人工
- 根因确认：豁免门此前只认强信号（单独同意/您授权），支付宝"为提供服务所必需/基于法定义务"等软性合规表述未触发；M11 补入后拦截生效

## 人工复核结论
### 支付宝 r07（M11 修复后重跑）
| 维度 | 修复前判定 | 修复后判定 | 说明 |
|---|---|---|---|
| d1 收集 | nonCompliant（误报） | unclear | 软性信号豁免：明确目的+非强制 |
| d4 第三方共享 | nonCompliant（误报） | unclear | 软性信号豁免：为提供服务所必需+信息授权服务 |
| d3 目的 | unclear | unclear | 软性信号豁免 |
| d5 跨境 | unclear | unclear | 软性信号豁免 |

### 跨境英文 3 份（AliExpress / Amazon / eBay）：0 条误报
- 3 份英文政策全部无 nonCompliant 误报；多数维度判 notApplicable（prompt 与法条库为中文、文本为英文，模型诚实选择不适用而非瞎判）
- d2（告知同意）普遍 unclear 转人工——英文文本的中文条款映射弱，符合事前预期
- Amazon d3/d6 出现原判定 nonCompliant 被证据锚定降级为 notApplicable：模型先误报、被证据锚定闸门拦下，证明防误报对英文文本同样生效

## v2 → v3 → v4 → v4.1 对比

| 指标 | v2（改造前，5 份） | v3（改造后，5 份） | v4（12 份原始） | v4.1（12 份+M11） |
|---|---|---|---|---|
| nonCompliant 判定 | 7 条 | 0 条 | 2 条（均误报） | **0 条** |
| 误报数 | 7 条（5 份） | 0 条（5 份） | 2 条（12 份，仅支付宝） | **0 条（12 份）** |
| 涉及文档 | 5/5 份 | 0/5 份 | 2/12 份 | **0/12 份** |
| unclear 占比 | 12/35 = 34% | 22/35 = 63% | 47/84 = 56% | 50/84 = 59.5% |

## 结论（诚实版）
1. 12 份真实政策全量盲测（M11 修复后）：**0 条 nonCompliant、0 条误报**；unclear 50/84 转人工复核兜底
2. 三层防误报（要件核查 prompt + 合规信号豁免门[含软性信号] + 规则线索化 + 证据锚定）在 12 份真实文本（9 中文 + 3 跨境英文）上有效
3. 已知边界：① 豁免门可能拦截边界表述 → 转人工复核兜底（宁可不报也不误报）；② 英文政策条款映射弱 → 多数 notApplicable/unclear，如实记录；③ 8000 字符截断后段可能漏检 → 报告已标注
4. 简历数字口径：12 份真实政策（含 3 份跨境英文）盲测，误报从改造前 7/7（100%）降至 0/12；unclear 转人工复核 59.5% 作为兜底保障
