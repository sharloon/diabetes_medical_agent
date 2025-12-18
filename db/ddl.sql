-- 创建医疗知识库数据库
CREATE DATABASE IF NOT EXISTS medical_knowledge_base;
USE medical_knowledge_base;

-- 患者基本信息表
CREATE TABLE IF NOT EXISTS patient_info (
    patient_id VARCHAR(200) PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    gender ENUM('男', '女') NOT NULL,
    age INT NOT NULL CHECK (age >= 0),
    height_cm DECIMAL(5,1) CHECK (height_cm >= 0),
    weight_kg DECIMAL(5,1) CHECK (weight_kg >= 0),
    bmi DECIMAL(4,1) GENERATED ALWAYS AS (weight_kg / POWER(height_cm/100, 2)) STORED,
    phone VARCHAR(20),
    address TEXT,
    create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 患者病历表
CREATE TABLE IF NOT EXISTS medical_records (
    record_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    visit_date DATE NOT NULL,
    chief_complaint TEXT,
    present_illness TEXT,
    past_history TEXT,
    family_history TEXT,
    physical_exam TEXT,
    preliminary_diagnosis TEXT,
    final_diagnosis TEXT,
    doctor_id INT,
    hospital VARCHAR(100),
    department VARCHAR(50),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
);

-- 检查检验结果表
CREATE TABLE IF NOT EXISTS lab_results (
    result_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    record_id INT,
    test_date DATE NOT NULL,
    test_type VARCHAR(100) NOT NULL,
    test_item VARCHAR(100) NOT NULL,
    result_value DECIMAL(10,2),
    unit VARCHAR(20),
    reference_range VARCHAR(50),
    is_abnormal BOOLEAN,
    test_notes TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (record_id) REFERENCES medical_records(record_id) ON DELETE SET NULL
);

-- 用药记录表
CREATE TABLE IF NOT EXISTS medication_records (
    med_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    record_id INT,
    medication_date DATE NOT NULL,
    drug_name VARCHAR(100) NOT NULL,
    drug_class VARCHAR(50),
    dosage VARCHAR(50),
    frequency VARCHAR(50),
    duration VARCHAR(50),
    prescribing_doctor VARCHAR(50),
    is_insulin BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (record_id) REFERENCES medical_records(record_id) ON DELETE SET NULL
);

-- 诊断记录表
CREATE TABLE IF NOT EXISTS diagnosis_records (
    diag_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    record_id INT NOT NULL,
    diagnosis_date DATE NOT NULL,
    diagnosis_code VARCHAR(20),
    diagnosis_name VARCHAR(100) NOT NULL,
    diagnosis_type ENUM('主要诊断', '次要诊断', '并发症') NOT NULL,
    severity_level ENUM('轻度', '中度', '重度', '危急') DEFAULT '中度',
    icd10_code VARCHAR(20),
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE,
    FOREIGN KEY (record_id) REFERENCES medical_records(record_id) ON DELETE CASCADE
);

-- 高血压风险评估表
CREATE TABLE IF NOT EXISTS hypertension_risk_assessment (
    assessment_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    assessment_date DATE NOT NULL,
    sbp DECIMAL(5,1) NOT NULL COMMENT '收缩压',
    dbp DECIMAL(5,1) NOT NULL COMMENT '舒张压',
    heart_rate INT,
    risk_factors TEXT COMMENT '危险因素',
    target_organs_damage TEXT COMMENT '靶器官损害',
    clinical_conditions TEXT COMMENT '临床疾患',
    risk_level ENUM('低危', '中危', '高危', '很高危') NOT NULL,
    follow_up_plan TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
);

-- 糖尿病控制评估表
CREATE TABLE IF NOT EXISTS diabetes_control_assessment (
    assessment_id INT PRIMARY KEY AUTO_INCREMENT,
    patient_id VARCHAR(200) NOT NULL,
    assessment_date DATE NOT NULL,
    fasting_glucose DECIMAL(5,1),
    postprandial_glucose DECIMAL(5,1),
    hba1c DECIMAL(4,1),
    insulin_usage BOOLEAN DEFAULT FALSE,
    insulin_type VARCHAR(50),
    insulin_dosage VARCHAR(50),
    control_status ENUM('良好', '一般', '不佳') NOT NULL,
    complications TEXT,
    FOREIGN KEY (patient_id) REFERENCES patient_info(patient_id) ON DELETE CASCADE
);

-- 指南推荐规则表
CREATE TABLE IF NOT EXISTS guideline_recommendations (
    rule_id INT PRIMARY KEY AUTO_INCREMENT,
    guideline_name VARCHAR(200) NOT NULL,
    disease_type ENUM('高血压', '糖尿病', '冠心病', '脑卒中') NOT NULL,
    patient_condition TEXT COMMENT '适用条件',
    recommendation_level ENUM('ⅠA', 'ⅠB', 'ⅡA', 'ⅡB', 'Ⅲ') NOT NULL,
    recommendation_content TEXT NOT NULL,
    evidence_source VARCHAR(200),
    update_date DATE,
    is_active BOOLEAN DEFAULT TRUE
);

-- 系统日志表
CREATE TABLE IF NOT EXISTS system_logs (
    log_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    operation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    operation_type ENUM('查询', '插入', '更新', '删除', '分析') NOT NULL,
    operation_user VARCHAR(50),
    operation_details TEXT,
    patient_id VARCHAR(200) NULL,
    execution_time_ms INT,
    status ENUM('成功', '失败', '警告') DEFAULT '成功'
);