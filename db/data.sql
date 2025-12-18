-- 生成100个测试患者
INSERT INTO patient_info (name, gender, age, height_cm, weight_kg, phone, address)
WITH RECURSIVE patients AS (
    SELECT 1 as n, 
           CONCAT('患者', LPAD(1, 3, '0')) as name,
           ELT(FLOOR(1 + RAND() * 2), '男', '女') as gender,
           FLOOR(30 + RAND() * 45) as age,
           CASE WHEN ELT(FLOOR(1 + RAND() * 2), '男', '女') = '男' THEN 165 + FLOOR(RAND() * 20) 
                ELSE 155 + FLOOR(RAND() * 15) END as height_cm,
           CASE WHEN ELT(FLOOR(1 + RAND() * 2), '男', '女') = '男' THEN 60 + FLOOR(RAND() * 30) 
                ELSE 50 + FLOOR(RAND() * 25) END as weight_kg,
           CONCAT('13', LPAD(FLOOR(RAND() * 900000000), 9, '0')) as phone,
           CONCAT('北京市', ELT(FLOOR(1 + RAND() * 5), '朝阳区', '海淀区', '西城区', '东城区', '丰台区'), 
                  LPAD(FLOOR(RAND() * 100), 2, '0'), '号') as address
    UNION ALL
    SELECT n + 1,
           CONCAT('患者', LPAD(n + 1, 3, '0')),
           ELT(FLOOR(1 + RAND() * 2), '男', '女'),
           FLOOR(30 + RAND() * 45),
           CASE WHEN ELT(FLOOR(1 + RAND() * 2), '男', '女') = '男' THEN 165 + FLOOR(RAND() * 20) 
                ELSE 155 + FLOOR(RAND() * 15) END,
           CASE WHEN ELT(FLOOR(1 + RAND() * 2), '男', '女') = '男' THEN 60 + FLOOR(RAND() * 30) 
                ELSE 50 + FLOOR(RAND() * 25) END,
           CONCAT('13', LPAD(FLOOR(RAND() * 900000000), 9, '0')),
           CONCAT('北京市', ELT(FLOOR(1 + RAND() * 5), '朝阳区', '海淀区', '西城区', '东城区', '丰台区'), 
                  LPAD(FLOOR(RAND() * 100), 2, '0'), '号')
    FROM patients WHERE n < 100
)
SELECT name, gender, age, height_cm, weight_kg, phone, address FROM patients;

-- 生成高血压风险评估数据
INSERT INTO hypertension_risk_assessment (patient_id, assessment_date, sbp, dbp, heart_rate, 
                                          risk_factors, target_organs_damage, clinical_conditions, 
                                          risk_level, follow_up_plan)
SELECT 
    patient_id,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY) as assessment_date,
    CASE WHEN RAND() < 0.3 THEN 120 + FLOOR(RAND() * 20)   -- 正常
         WHEN RAND() < 0.6 THEN 140 + FLOOR(RAND() * 20)   -- 1级
         ELSE 160 + FLOOR(RAND() * 30) END as sbp,         -- 2-3级
    CASE WHEN RAND() < 0.3 THEN 80 + FLOOR(RAND() * 10)    -- 正常
         WHEN RAND() < 0.6 THEN 90 + FLOOR(RAND() * 10)    -- 1级
         ELSE 100 + FLOOR(RAND() * 20) END as dbp,         -- 2-3级
    60 + FLOOR(RAND() * 30) as heart_rate,
    CASE WHEN RAND() < 0.4 THEN '吸烟,血脂异常'
         WHEN RAND() < 0.7 THEN '糖尿病,肥胖'
         ELSE '高龄,家族史' END as risk_factors,
    CASE WHEN RAND() < 0.3 THEN '左心室肥厚'
         WHEN RAND() < 0.6 THEN '颈动脉斑块'
         ELSE '肾功能异常' END as target_organs_damage,
    CASE WHEN RAND() < 0.4 THEN '冠心病'
         WHEN RAND() < 0.7 THEN '脑卒中'
         ELSE '慢性肾病' END as clinical_conditions,
    CASE WHEN RAND() < 0.3 THEN '低危'
         WHEN RAND() < 0.6 THEN '中危'
         ELSE '高危' END as risk_level,
    CASE WHEN RAND() < 0.3 THEN '3个月随访'
         WHEN RAND() < 0.6 THEN '1个月随访'
         ELSE '2周随访' END as follow_up_plan
FROM patient_info
WHERE RAND() < 0.8; -- 80%的患者有高血压评估

-- 生成糖尿病控制评估数据
INSERT INTO diabetes_control_assessment (patient_id, assessment_date, fasting_glucose, postprandial_glucose, 
                                        hba1c, insulin_usage, insulin_type, insulin_dosage, control_status, complications)
SELECT 
    patient_id,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 180) DAY) as assessment_date,
    CASE WHEN RAND() < 0.3 THEN 5.0 + RAND() * 2.0    -- 良好
         WHEN RAND() < 0.6 THEN 7.0 + RAND() * 2.0    -- 一般
         ELSE 9.0 + RAND() * 4.0 END as fasting_glucose,
    CASE WHEN RAND() < 0.3 THEN 7.0 + RAND() * 3.0    -- 良好
         WHEN RAND() < 0.6 THEN 10.0 + RAND() * 3.0   -- 一般
         ELSE 13.0 + RAND() * 5.0 END as postprandial_glucose,
    CASE WHEN RAND() < 0.3 THEN 6.0 + RAND() * 0.5    -- 良好
         WHEN RAND() < 0.6 THEN 7.0 + RAND() * 1.0    -- 一般
         ELSE 8.0 + RAND() * 2.0 END as hba1c,
    RAND() < 0.4 as insulin_usage,
    CASE WHEN RAND() < 0.3 THEN '门冬胰岛素'
         WHEN RAND() < 0.6 THEN '甘精胰岛素'
         ELSE '预混胰岛素' END as insulin_type,
    CASE WHEN RAND() < 0.3 THEN '10-20U'
         WHEN RAND() < 0.6 THEN '20-40U'
         ELSE '40-60U' END as insulin_dosage,
    CASE WHEN RAND() < 0.3 THEN '良好'
         WHEN RAND() < 0.6 THEN '一般'
         ELSE '不佳' END as control_status,
    CASE WHEN RAND() < 0.3 THEN '无'
         WHEN RAND() < 0.6 THEN '视网膜病变'
         ELSE '周围神经病变' END as complications
FROM patient_info
WHERE RAND() < 0.6; -- 60%的患者有糖尿病评估

-- 生成指南推荐规则
INSERT INTO guideline_recommendations (guideline_name, disease_type, patient_condition, 
                                      recommendation_level, recommendation_content, evidence_source, update_date)
VALUES
('中国高血压防治指南2023', '高血压', '1级高血压，无其他危险因素', 'ⅠA', '起始单药治疗，首选CCB、ACEI/ARB、利尿剂', '中华心血管病杂志2023;51(3):231-240', '2023-05-15'),
('中国高血压防治指南2023', '高血压', '2级高血压或1级高血压伴靶器官损害', 'ⅠA', '起始联合治疗，推荐CCB+ACEI/ARB或CCB+利尿剂', '中华心血管病杂志2023;51(3):231-240', '2023-05-15'),
('中国高血压防治指南2023', '高血压', '高血压急症，SBP>180mmHg', 'ⅠA', '立即静脉降压治疗，目标1小时内降低不超过25%', '中华心血管病杂志2023;51(3):231-240', '2023-05-15'),
('中国2型糖尿病防治指南2020', '糖尿病', '新诊断2型糖尿病，HbA1c<7.5%', 'ⅠA', '生活方式干预+二甲双胍起始治疗', '中华糖尿病杂志2021;13(4):315-322', '2021-04-20'),
('中国2型糖尿病防治指南2020', '糖尿病', 'HbA1c≥7.0%且二甲双胍单药控制不佳', 'ⅠA', '二甲双胍+胰岛素促泌剂或DPP-4抑制剂', '中华糖尿病杂志2021;13(4):315-322', '2021-04-20'),
('中国2型糖尿病防治指南2020', '糖尿病', 'HbA1c≥9.0%或有明显高血糖症状', 'ⅠA', '起始胰岛素治疗，可联合口服药', '中华糖尿病杂志2021;13(4):315-322', '2021-04-20'),
('冠心病合理用药指南2022', '冠心病', '稳定性心绞痛，无禁忌症', 'ⅠA', '阿司匹林75-100mg/d + 他汀类药物', '中国医学前沿杂志2022;14(5):1-30', '2022-06-01'),
('脑卒中二级预防指南2021', '脑卒中', '缺血性脑卒中后二级预防', 'ⅠA', '抗血小板治疗+积极控制危险因素', '中华神经科杂志2021;54(9):881-890', '2021-09-10');

-- 生成用药记录
INSERT INTO medication_records (patient_id, record_id, medication_date, drug_name, drug_class, 
                               dosage, frequency, duration, prescribing_doctor, is_insulin)
SELECT 
    p.patient_id,
    NULL as record_id,
    DATE_SUB(CURDATE(), INTERVAL FLOOR(RAND() * 365) DAY) as medication_date,
    ELT(FLOOR(1 + RAND() * 5), '氨氯地平', '缬沙坦', '氢氯噻嗪', '美托洛尔', '二甲双胍') as drug_name,
    CASE ELT(FLOOR(1 + RAND() * 5), '氨氯地平', '缬沙坦', '氢氯噻嗪', '美托洛尔', '二甲双胍')
        WHEN '氨氯地平' THEN 'CCB'
        WHEN '缬沙坦' THEN 'ARB'
        WHEN '氢氯噻嗪' THEN '利尿剂'
        WHEN '美托洛尔' THEN 'β受体阻滞剂'
        WHEN '二甲双胍' THEN '双胍类' END as drug_class,
    ELT(FLOOR(1 + RAND() * 3), '5mg', '10mg', '20mg') as dosage,
    '每日一次' as frequency,
    '长期' as duration,
    ELT(FLOOR(1 + RAND() * 3), '张医生', '李医生', '王医生') as prescribing_doctor,
    CASE WHEN ELT(FLOOR(1 + RAND() * 5), '氨氯地平', '缬沙坦', '氢氯噻嗪', '美托洛尔', '二甲双胍') = '二甲双胍' 
         AND RAND() < 0.3 THEN TRUE ELSE FALSE END as is_insulin
FROM patient_info p
WHERE RAND() < 0.7
LIMIT 200;