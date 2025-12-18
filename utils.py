"""
工具函数模块
"""
import os
import sys
from loguru import logger
from config import LOG_CONFIG


def setup_logger():
    """配置日志系统"""
    # 移除默认处理器
    logger.remove()
    
    # 添加控制台输出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # 添加文件输出
    logger.add(
        LOG_CONFIG["log_file"],
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        rotation=LOG_CONFIG["rotation"],
        retention=LOG_CONFIG["retention"],
        level=LOG_CONFIG["level"],
        encoding="utf-8"
    )
    
    return logger


def format_patient_profile(profile: dict) -> str:
    """格式化患者档案为可读文本"""
    if not profile:
        return "暂无患者信息"
    
    lines = []
    lines.append(f"【患者基本信息】")
    lines.append(f"患者ID: {profile.get('patient_id', 'N/A')}")
    lines.append(f"姓名: {profile.get('name', 'N/A')}")
    lines.append(f"性别: {profile.get('gender', 'N/A')}")
    lines.append(f"年龄: {profile.get('age', 'N/A')}岁")
    
    if profile.get('height_cm'):
        lines.append(f"身高: {profile.get('height_cm')}cm")
    if profile.get('weight_kg'):
        lines.append(f"体重: {profile.get('weight_kg')}kg")
    if profile.get('bmi'):
        lines.append(f"BMI: {profile.get('bmi')}")
    
    if profile.get('diagnoses'):
        lines.append(f"\n【诊断信息】")
        for diag in profile['diagnoses']:
            lines.append(f"- {diag.get('diagnosis_name', '')} ({diag.get('diagnosis_type', '')})")
    
    if profile.get('medications'):
        lines.append(f"\n【用药记录】")
        for med in profile['medications']:
            lines.append(f"- {med.get('drug_name', '')} {med.get('dosage', '')} {med.get('frequency', '')}")
    
    if profile.get('hypertension_assessment'):
        ha = profile['hypertension_assessment']
        lines.append(f"\n【高血压评估】")
        lines.append(f"血压: {ha.get('sbp', 'N/A')}/{ha.get('dbp', 'N/A')} mmHg")
        lines.append(f"风险等级: {ha.get('risk_level', 'N/A')}")
        lines.append(f"危险因素: {ha.get('risk_factors', 'N/A')}")
    
    if profile.get('diabetes_assessment'):
        da = profile['diabetes_assessment']
        lines.append(f"\n【糖尿病评估】")
        lines.append(f"空腹血糖: {da.get('fasting_glucose', 'N/A')} mmol/L")
        lines.append(f"糖化血红蛋白(HbA1c): {da.get('hba1c', 'N/A')}%")
        lines.append(f"控制状态: {da.get('control_status', 'N/A')}")
    
    if profile.get('lab_results'):
        lines.append(f"\n【检验结果】")
        for lab in profile['lab_results'][:10]:  # 只显示前10条
            abnormal = "↑" if lab.get('is_abnormal') else ""
            lines.append(f"- {lab.get('test_item', '')}: {lab.get('result_value', '')} {lab.get('unit', '')} {abnormal}")
    
    return "\n".join(lines)


def format_source_reference(source: dict) -> str:
    """格式化来源引用"""
    source_type = source.get('type', 'unknown')
    
    if source_type == 'pdf':
        return f"[PDF] {source.get('filename', '')} 第{source.get('page', '')}页"
    elif source_type == 'excel':
        return f"[Excel] {source.get('filename', '')} 第{source.get('row', '')}行"
    elif source_type == 'mysql':
        return f"[数据库] {source.get('table', '')}表"
    else:
        return f"[{source_type}] {source.get('ref', '')}"


def calculate_bmi(height_cm: float, weight_kg: float) -> float:
    """计算BMI"""
    if height_cm and weight_kg and height_cm > 0:
        height_m = height_cm / 100
        return round(weight_kg / (height_m ** 2), 1)
    return None


def get_bmi_category(bmi: float) -> str:
    """获取BMI分类"""
    if bmi is None:
        return "未知"
    if bmi < 18.5:
        return "偏瘦"
    elif bmi < 24:
        return "正常"
    elif bmi < 28:
        return "超重"
    else:
        return "肥胖"


def get_bp_grade(sbp: int, dbp: int) -> str:
    """获取血压分级"""
    if sbp is None or dbp is None:
        return "未知"
    
    if sbp < 120 and dbp < 80:
        return "正常血压"
    elif sbp < 140 and dbp < 90:
        return "正常高值"
    elif sbp < 160 or dbp < 100:
        return "1级高血压"
    elif sbp < 180 or dbp < 110:
        return "2级高血压"
    else:
        return "3级高血压"


def get_hba1c_control_status(hba1c: float) -> str:
    """获取糖化血红蛋白控制状态"""
    if hba1c is None:
        return "未知"
    if hba1c < 7.0:
        return "控制良好"
    elif hba1c < 8.5:
        return "控制一般"
    else:
        return "控制不佳"


# 初始化日志
setup_logger()

