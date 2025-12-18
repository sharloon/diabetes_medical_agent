"""
配置文件 - 糖尿病智能诊断助手
"""
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# ============ API配置 ============
DASHSCOPE_API_KEY = "sk-5443e95b1bfd4c5284800039b8d3d5e7"
DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# LLM模型配置
LLM_MODEL = "qwen-plus-latest"
EMBEDDING_MODEL = "text-embedding-v2"

# ============ MySQL数据库配置 ============
MYSQL_CONFIG = {
    "host": "rm-bp1y35g510t57uexqlo.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "logcloud",
    "password": "Logcloud4321",
    "database": "medical_knowledge_base",
    "charset": "utf8mb4"
}

# ============ 路径配置 ============
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")
KNOWLEDGE_BASE_DIR = os.path.join(BASE_DIR, "knowledge_base")
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 确保目录存在
for dir_path in [KNOWLEDGE_BASE_DIR, LOG_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ============ RAG配置 ============
RAG_CONFIG = {
    "chunk_size": 512,
    "chunk_overlap": 50,
    "top_k": 5,
    "persist_dir": os.path.join(KNOWLEDGE_BASE_DIR, "vector_index"),
    "index_update_interval": 120  # 索引更新间隔（秒）
}

# ============ 日志配置 ============
LOG_CONFIG = {
    "log_file": os.path.join(LOG_DIR, "medical_agent.log"),
    "rotation": "10 MB",
    "retention": "7 days",
    "level": "INFO"
}

# ============ 术语映射表 ============
TERM_MAPPINGS = {
    # 疾病名称映射
    "心梗": "心肌梗死",
    "脑梗": "脑梗死",
    "脑卒中": "脑血管意外",
    "中风": "脑血管意外",
    "高血压": "高血压病",
    "糖尿病": "糖尿病",
    "冠心病": "冠状动脉粥样硬化性心脏病",
    "高血脂": "血脂异常",
    "肾衰": "肾功能衰竭",
    "心衰": "心力衰竭",
    
    # 药物名称映射
    "阿司匹林": "乙酰水杨酸",
    "拜阿司匹灵": "阿司匹林肠溶片",
    "络活喜": "氨氯地平",
    "代文": "缬沙坦",
    "倍他乐克": "美托洛尔",
    "格华止": "二甲双胍",
    "拜唐苹": "阿卡波糖",
    "诺和灵": "人胰岛素",
    "来得时": "甘精胰岛素",
    "诺和锐": "门冬胰岛素",
    
    # 检查项目映射
    "血糖": "血葡萄糖",
    "血脂": "血脂谱",
    "肾功": "肾功能",
    "肝功": "肝功能",
    "心电图": "心电图检查",
    "心超": "超声心动图",
    
    # 症状映射
    "头晕": "眩晕",
    "胸闷": "胸部不适",
    "心慌": "心悸",
    "气短": "呼吸困难",
}

# ============ 药物禁忌配置 ============
DRUG_CONTRAINDICATIONS = {
    "ACEI类": {
        "drugs": ["依那普利", "贝那普利", "培哚普利", "雷米普利", "福辛普利"],
        "contraindications": ["妊娠", "双侧肾动脉狭窄", "高钾血症", "血管性水肿史"],
        "interactions": ["保钾利尿剂", "NSAIDs", "锂盐"]
    },
    "ARB类": {
        "drugs": ["缬沙坦", "厄贝沙坦", "氯沙坦", "替米沙坦", "坎地沙坦"],
        "contraindications": ["妊娠", "双侧肾动脉狭窄", "高钾血症"],
        "interactions": ["保钾利尿剂", "NSAIDs", "锂盐"]
    },
    "CCB类": {
        "drugs": ["氨氯地平", "硝苯地平", "非洛地平", "尼群地平"],
        "contraindications": ["心源性休克", "严重主动脉瓣狭窄"],
        "interactions": ["β受体阻滞剂"]
    },
    "β受体阻滞剂": {
        "drugs": ["美托洛尔", "比索洛尔", "阿替洛尔", "普萘洛尔"],
        "contraindications": ["支气管哮喘", "严重心动过缓", "二度以上房室传导阻滞"],
        "interactions": ["非二氢吡啶类CCB", "胰岛素"]
    },
    "利尿剂": {
        "drugs": ["氢氯噻嗪", "呋塞米", "螺内酯", "吲达帕胺"],
        "contraindications": ["严重肾功能不全", "电解质紊乱"],
        "interactions": ["ACEI", "ARB", "锂盐"]
    }
}

# ============ 风险分层配置 ============
RISK_STRATIFICATION = {
    "hypertension": {
        "grade_1": {"sbp_range": (140, 159), "dbp_range": (90, 99)},
        "grade_2": {"sbp_range": (160, 179), "dbp_range": (100, 109)},
        "grade_3": {"sbp_range": (180, 999), "dbp_range": (110, 999)},
    },
    "diabetes": {
        "good_control": {"hba1c_range": (0, 7.0), "fasting_glucose_range": (0, 7.0)},
        "moderate_control": {"hba1c_range": (7.0, 8.5), "fasting_glucose_range": (7.0, 10.0)},
        "poor_control": {"hba1c_range": (8.5, 99), "fasting_glucose_range": (10.0, 99)},
    }
}

# ============ 高风险预警阈值 ============
EMERGENCY_THRESHOLDS = {
    "hypertensive_emergency": {
        "sbp": 180,
        "dbp": 120,
        "symptoms": ["头痛", "呕吐", "视物模糊", "意识障碍", "胸痛", "呼吸困难"]
    },
    "hypoglycemia": {
        "glucose": 3.9,
        "symptoms": ["出汗", "心悸", "颤抖", "饥饿感", "意识模糊"]
    },
    "diabetic_ketoacidosis": {
        "glucose": 16.7,
        "symptoms": ["多尿", "口渴", "恶心呕吐", "腹痛", "呼吸深快"]
    }
}

# ============ 证据等级说明 ============
EVIDENCE_LEVELS = {
    "ⅠA": "证据充分，强烈推荐",
    "ⅠB": "证据较充分，推荐",
    "ⅡA": "证据有限，可以考虑",
    "ⅡB": "证据不足，可能有益",
    "Ⅲ": "证据不足或有害，不推荐"
}

