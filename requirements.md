# Requirements Document

## Introduction

课堂作业级的高血压+糖尿病决策助手，使用 Python + OpenAI SDK 调用阿里云百炼 API，参考 `example/chabot` 的轻量用法，整合指南 PDF、病例 Excel 与 MySQL 数据，完成基础 RAG 检索、画像与风险评估、个性化方案与安全预警，突出简洁实现与可验证结果。

## Alignment with Product Vision

- 贴合 PRD：用指南 PDF + Excel + MySQL 做统一检索与决策支持，满足作业评分点。
- 保持简单：沿用 `example/chabot` 的最小实现风格，少组件、易跑通。
- 强调安全与溯源：输出附带证据来源与预警，避免高风险幻觉。

## Requirements

### Requirement 1: SDK/平台与最小可运行

**User Story:** 作为开发者，我需要用 Python + OpenAI SDK 调用阿里云百炼 API，快速跑通最小聊天/RAG 入口。

#### Acceptance Criteria

1. WHEN 本地配置好百炼密钥 THEN 系统 SHALL 能用 OpenAI SDK 成功调用百炼模型完成一次问答（含错误处理）。
2. WHEN 参考 `example/chabot` 启动示例 THEN 系统 SHALL 提供最小 CLI/HTTP 入口可交互。
3. IF 调用失败（鉴权/超时） THEN 系统 SHALL 返回清晰错误信息并提示重试或检查配置。

### Requirement 2: 多源知识库构建与统一检索

**User Story:** 作为临床医生，我希望从指南 PDF、Excel 统计与 MySQL 数据库统一检索到结构化证据和患者信息，以便快速获得跨源决策支持。

#### Acceptance Criteria

1. WHEN 系统完成初次处理 THEN 系统 SHALL 解析两份指南目录/关键表格并生成简单向量索引；Excel 中胰岛素使用率入库 MySQL/或轻量 DataFrame。
2. WHEN 用户输入“高血压急症处理” THEN 系统 SHALL 跨 PDF/Excel/MySQL 返回命中内容并标注来源（页码/行号/表名）。
3. WHEN 用户按更新时间过滤到 2025-07-20 及以后 THEN 系统 SHALL 仅返回满足时间条件的片段。
4. IF 新增《中国高血压防治指南.pdf》 THEN 系统 SHALL 触发索引重建并记录时间戳日志。

### Requirement 3: 数据标准化与术语映射

**User Story:** 作为医生，我希望同义词和俗称能自动标准化（如“心梗”→“心肌梗死”），避免检索遗漏。

#### Acceptance Criteria

1. WHEN 用户检索俗称或别名 THEN 系统 SHALL 返回标准术语及原术语映射表展示。
2. IF 术语未映射成功 THEN 系统 SHALL 提供近似词建议并允许人工补充映射。

### Requirement 4: 临床数据查询与风险评估

**User Story:** 作为医生，我希望输入患者 ID 即可生成完整画像并得到风险分层和随访计划。

#### Acceptance Criteria

1. WHEN 输入患者 ID (如 42) THEN 系统 SHALL 查询 MySQL 并输出年龄、性别、BMI、诊断、用药、检查结果的结构化画像。
2. WHEN 画像生成完成 THEN 系统 SHALL 基于指南规则输出高血压/糖尿病风险等级与随访计划（含时间与指标）。
3. WHEN 患者存在多药联合 THEN 系统 SHALL 检测药物冲突/禁忌并给出预警理由。

### Requirement 5: 个性化诊疗与循证输出

**User Story:** 作为医生，我希望输入症状与检查数据即可获得鉴别诊断、治疗方案、疗效跟踪与再评估，且标注证据等级与出处。

#### Acceptance Criteria

1. WHEN 输入症状与检查（如头痛、BP 168/98、HbA1c 8.2%） THEN 系统 SHALL 生成≥3 个鉴别诊断并给出概率排序与推理路径。
2. WHEN 生成治疗方案 THEN 系统 SHALL 给出降压+控糖方案、剂量依据、证据等级（如 IA/IIB），并标注指南页码/Excel 行/MySQL 表来源。
3. WHEN 模拟 2 周疗效不佳 THEN 系统 SHALL 重新评估并调整方案，展示调整逻辑与依据。

### Requirement 6: 伦理安全与高风险预警

**User Story:** 作为医生，我需要系统对孕妇、急症等高风险场景进行主动预警和转诊建议。

#### Acceptance Criteria

1. IF 患者为孕妇且推荐 ACEI/ARB THEN 系统 SHALL 阻断并提示禁忌，给出甲基多巴/拉贝洛尔等替代方案并建议产科会诊。
2. IF 收缩压 >180mmHg 且伴神经症状 THEN 系统 SHALL 识别为高血压急症，建议静脉降压并明确紧急转诊理由。

### Requirement 7: 对话管理与健壮性

**User Story:** 作为用户，我希望问诊过程结构化且在异常情况下有优雅降级提示。

#### Acceptance Criteria

1. WHEN 主诉“头晕” THEN 系统 SHALL 以 SOAP 流程进行结构化问诊，并主动澄清血压数值、持续时间等关键信息。
2. WHEN 知识库无相关信息（如骨折治疗） THEN 系统 SHALL 返回专业的无匹配提示而非胡乱生成。
3. IF 数据库连接失败 THEN 系统 SHALL 优雅降级提示并记录错误以便运维。

### Requirement 8: 运维与性能（简化版）

**User Story:** 作为运维/数据工程师，我希望系统具备日志、性能与索引维护能力。

#### Acceptance Criteria

1. WHEN 执行复杂查询（如全院患者风险评估） THEN 系统 SHALL 提供简单优化方案并在 3 秒内返回结果。
2. WHEN 重建索引或新增文档 THEN 系统 SHALL 记录操作时间戳与结果，便于审核。

## Non-Functional Requirements

### Code Architecture and Modularity
- 单一职责且轻量：摄取/索引、检索、推理、对话按文件模块拆分，保持最小依赖。
- 模块化但简单：RAG 管道、术语映射、风险评估、对话管理各自独立函数/类，便于课堂演示。
- 依赖管理：只引入必要包（OpenAI SDK、向量库、MySQL 连接、基础 Web/CLI）。
- 清晰接口：检索、评估、推理统一返回结构化 schema（含来源字段）。

### Performance
- 跨源检索与画像生成 P95 响应 ≤3s；批量风险评估 SQL 优化到 3s 以内。
- 索引重建完成后 1 分钟内可服务最新文档。

### Security
- 遵循最小权限访问 MySQL，敏感字段脱敏展示；记录审计日志。
- 生成式输出需附来源与证据等级，禁止无依据的高风险建议。

### Reliability
- 数据源不可用时自动降级并告警；索引重建失败需回滚到上一次可用版本。
- 提供健康检查与重试机制，核心操作具备幂等性。

### Usability
- 输出结构化且带来源标注；支持日期过滤和术语映射提示。
- 对话中主动澄清关键缺失信息，错误提示专业可读。

