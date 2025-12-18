# 糖尿病智能诊断助手

基于RAG和智能体技术的专家级医疗决策支持系统，实现高血压、糖尿病临床诊疗全流程决策支持。

## 功能特性

### 基础数据层
- **PDF知识库构建**: 提取文档目录结构、关键表格，支持术语标准化映射
- **Excel数据处理**: 解析糖尿病病例统计数据，可视化胰岛素使用率等分布
- **多模态数据整合**: PDF+Excel+MySQL统一检索接口，支持指南时效性验证
- **智能对话**: 基于知识库的智能问答，无知识时给出专业提示
- **系统运维**: 每2分钟自动更新文档RAG索引，日志记录

### 专家智能体核心能力
- **临床数据查询与分析**: 患者画像构建、风险分层评估、用药冲突检测
- **个性化诊疗决策**: 诊断推理（≥3个鉴别诊断）、治疗方案生成、动态调整
- **循证医学支持**: 证据等级标注（ⅠA/ⅡB等）、多源知识融合
- **伦理安全控制**: 孕妇ACEI禁忌警示、高血压急症转诊建议
- **智能体对话管理**: SOAP格式结构化问诊、信息澄清能力

### 系统工程能力
- **异常处理**: 数据库连接失败优雅降级
- **性能优化**: 复杂查询<3秒响应
- **决策溯源**: 每个建议标注数据来源（PDF页码、Excel行号、MySQL表名）
- **推理可视化**: 决策路径展示

## 技术栈

- **后端**: Python + Flask
- **LLM**: 阿里云百炼 (通过OpenAI SDK)
- **RAG**: LlamaIndex + DashScope Embedding
- **数据库**: MySQL
- **前端**: Bootstrap 5 + Chart.js

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
# Windows
set DASHSCOPE_API_KEY=your-api-key

# Linux/Mac
export DASHSCOPE_API_KEY=your-api-key
```

### 3. 启动应用

```bash
python run.py
```

或者直接运行:

```bash
python app.py
```

### 4. 访问应用

打开浏览器访问: http://localhost:5000

## 项目结构

```
diabetes_medical_agent/
├── app.py                  # Flask主应用
├── run.py                  # 启动脚本
├── config.py               # 配置文件
├── requirements.txt        # 依赖列表
│
├── llm_client.py           # LLM客户端封装
├── db_service.py           # MySQL数据库服务
├── data_ingest.py          # 数据摄取(PDF/Excel)
├── vector_store.py         # 向量存储
├── rag_service.py          # RAG检索服务
├── term_mapper.py          # 术语映射
├── risk_engine.py          # 风险评估引擎
├── safety_guard.py         # 安全预警模块
├── diagnosis_agent.py      # 诊疗决策智能体
├── scheduler.py            # 定时任务调度
├── utils.py                # 工具函数
│
├── templates/              # 前端模板
│   ├── base.html
│   ├── index.html
│   ├── chat.html
│   └── ...
│
├── data/                   # 数据文件
│   ├── 高血压诊疗指南.pdf
│   ├── 中国高血压防治指南.pdf
│   └── 糖尿病病例统计.xlsx
│
├── db/                     # 数据库脚本
│   ├── ddl.sql
│   └── data.sql
│
└── knowledge_base/         # 向量索引存储
```

## 测试案例

### 测试案例1: 患者画像与治疗方案
- 输入: 患者ID = 1002_0_20210504
- 预期: 58岁男性，BMI 28.5，血压168/98mmHg，2级高血压合并2型糖尿病
- 输出: 联合降压方案 + 血糖控制建议 + 3个月随访计划

### 测试案例2: 孕妇用药禁忌
- 输入: 35岁孕妇，血压158/96mmHg
- 预期: 禁用ACEI/ARB，推荐甲基多巴或拉贝洛尔，建议产科会诊

### 测试案例3: 高血压急症
- 输入: 收缩压190mmHg，头痛呕吐3小时
- 预期: 识别高血压急症，建议静脉降压，紧急转诊至急诊科

## 数据库配置

MySQL连接信息已在config.py中配置。

## 注意事项

1. 本系统仅供学习和研究使用，不能作为临床诊疗依据
2. 所有诊疗建议需由执业医师审核确认
3. 请妥善保管API密钥和数据库凭据

## License

MIT License
