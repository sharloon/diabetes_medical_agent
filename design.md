# Design Document

## Overview
课堂级高血压+糖尿病决策助手，采用 Python 最小实现：用 OpenAI SDK 调用阿里云百炼模型，参考 `example/chabot` 的轻量结构；API 层明确采用 Flask。核心流程：数据摄取（PDF/Excel/MySQL）→ 术语映射 → RAG 检索 → 规则/LLM 推理（风险、诊疗、预警）→ 对话/HTTP 接口输出，强调可跑通、易截图与可溯源。

## Steering Document Alignment
### Technical Standards (tech.md)
- 无现有约束，遵循简单分层：配置、数据源适配、检索/推理服务、接口层。
- 使用 OpenAI Python SDK 直连百炼；统一封装 `llm_client.py`。
### Project Structure (structure.md)
- 保持最小目录：`example/chabot` 风格的 `app.py`/`service`/`data` 分层，避免过度拆分。

## Code Reuse Analysis
### Existing Components to Leverage
- `example/chabot`：示例入口与对话模式，沿用调用模式与配置加载方式。
- 现有 data 目录：PDF、Excel、SQL 脚本直接作为数据源。
### Integration Points
- MySQL：使用简单连接池/直连执行 SQL（建表/查询）。
- 向量存储：可选本地 FAISS 或内存索引，规模小优先内存/本地文件。
- LLM：OpenAI SDK → 百炼 endpoint，封装成统一 `generate`/`chat`。

## Architecture
模块化但简洁，单文件单职责。
```mermaid
flowchart TD
  A[app.py CLI/HTTP] --> B[chat_router/service]
  B --> C[RAG 服务]
  C --> D[文档索引 PDF/Excel]
  C --> E[MySQL 查询]
  B --> F[术语映射]
  B --> G[风险/规则引擎]
  C --> H[LLM(百炼 via OpenAI SDK)]
```

### Modular Design Principles
- 单文件单职责：配置、LLM 客户端、RAG、术语映射、风险评估、接口各自独立。
- 组件隔离：数据摄取/索引不依赖接口层；接口层仅调服务。
- 服务分层：数据访问（MySQL/索引）与业务推理（风险/诊疗）分离。
- 工具模块化：小型工具函数放 `utils.py`，避免臃肿。

## Components and Interfaces
### app.py / interface (Flask)
- Purpose: 提供最小 CLI 或 Flask HTTP 入口，与 `example/chabot` 结构一致。
- Interfaces: Flask 路由 `POST /chat`，`POST /patient/<id>`，`GET /health`。
- Dependencies: `chat_service`, `llm_client`, `rag_service`, `risk_engine`。
- Reuses: `example/chabot` 初始化/配置模式，Flask 轻量蓝图或单文件路由。

### llm_client.py
- Purpose: 封装 OpenAI SDK 调百炼（chat/completions）。
- Interfaces: `generate(prompt, history=[])`；错误返回标准结构。
- Dependencies: OpenAI SDK，百炼 base_url/key。
- Reuses: `example/chabot` 调用样例。

### data_ingest.py
- Purpose: 轻量解析 PDF（目录/表格摘要）、Excel（胰岛素使用率）、加载 MySQL DDL/data。
- Interfaces: `build_pdf_index()`, `load_excel_stats()`, `init_mysql()`。
- Dependencies: pypdf/camelot/类似工具，pandas，mysql client。
- Reuses: data 目录现有文件。

### vector_store.py
- Purpose: 简单向量索引（内存/FAISS）；存储 PDF/表格分块。
- Interfaces: `index_chunks(chunks)`, `search(query, k)`。
- Dependencies: sentence-transformers/百炼 embeddings（二选一，依简易与可用性）。

### term_mapper.py
- Purpose: 术语同义/映射表（如“心梗”→“心肌梗死”）。
- Interfaces: `normalize(term)`, `suggest(term)`，返回映射/近似词。
- Dependencies: 内置表/简单字典。

### rag_service.py
- Purpose: 跨源检索聚合与答案组织。
- Interfaces: `search(query, filters) -> {hits, sources}`；`rag_answer(query, patient_ctx?)`。
- Dependencies: vector_store, MySQL, term_mapper, llm_client。

### risk_engine.py
- Purpose: 基于患者画像做高血压/糖尿病风险分层与随访计划。
- Interfaces: `assess(profile) -> {risk_level, plan}`。
- Dependencies: 规则表（本地配置），MySQL 画像数据。

### safety_guard.py
- Purpose: 伦理/高风险预警（孕妇 ACEI/ARB 禁忌、高血压急症转诊）。
- Interfaces: `check(profile, recommendations) -> warnings`。
- Dependencies: 简单规则。

## Data Models
### PatientProfile (dict)
- id: int
- age, gender, bmi, bp_sbp, bp_dbp, diagnoses: list[str], meds: list[str], labs: dict
- source_refs: {table: rows}

### RetrievalHit (dict)
- content: str
- source: {type: pdf/excel/mysql, ref: page/row/table, updated_at}
- score: float

### Recommendation (dict)
- diagnosis_list: [{name, prob}]
- plan: [{step, drug?, dose?, rationale, evidence_level, source}]
- warnings: [{type, message, severity}]

## Error Handling
1. 百炼/LLM 调用失败：降级提示“LLM 不可用，请稍后重试/检查密钥”；记录日志。
2. MySQL 连接失败：返回友好提示并跳过数据库片段，仍可用 PDF/Excel 命中。
3. 知识库为空/无匹配：返回专业的无匹配提示，避免幻觉。

## Testing Strategy
### Unit Testing
- term_mapper 映射/建议。
- risk_engine 规则输出（含孕妇/高血压急症）。
- rag_service 检索聚合（mock 向量/DB）。
### Integration Testing
- LLM 客户端到百炼的调用（可用 sandbox/key）；MySQL 查询 + 检索聚合。
### End-to-End Testing
- 场景 1：患者 ID=42 画像+方案+随访。
- 场景 2：孕妇 35 岁，BP 158/96，禁用 ACEI/ARB 预警。
- 场景 3：SBP 190 急症→转诊建议与静脉降压提示。

