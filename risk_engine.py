"""
风险评估引擎 - 高血压/糖尿病风险分层与随访计划
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

from config import RISK_STRATIFICATION, EMERGENCY_THRESHOLDS


class RiskEngine:
    """风险评估引擎"""
    
    def __init__(self):
        self.risk_config = RISK_STRATIFICATION
        self.emergency_config = EMERGENCY_THRESHOLDS
        logger.info("风险评估引擎初始化完成")
    
    def assess_patient(self, profile: Dict) -> Dict:
        """
        综合评估患者风险
        
        Args:
            profile: 患者档案
            
        Returns:
            Dict: 风险评估结果
        """
        logger.info(f"开始患者风险评估，患者ID: {profile.get('patient_id', 'N/A')}")
        
        assessment = {
            'patient_id': profile.get('patient_id'),
            'assessment_time': datetime.now().isoformat(),
            'hypertension_risk': None,
            'diabetes_risk': None,
            'overall_risk_level': '低危',
            'risk_factors': [],
            'follow_up_plan': {},
            'recommendations': [],
            'warnings': []
        }
        
        # 高血压风险评估
        ha = profile.get('hypertension_assessment')
        if ha:
            assessment['hypertension_risk'] = self._assess_hypertension(ha, profile)
        
        # 糖尿病风险评估
        da = profile.get('diabetes_assessment')
        if da:
            assessment['diabetes_risk'] = self._assess_diabetes(da, profile)
        
        # 综合风险评估
        self._calculate_overall_risk(assessment, profile)
        
        # 生成随访计划
        assessment['follow_up_plan'] = self._generate_follow_up_plan(assessment)
        
        # 生成建议
        assessment['recommendations'] = self._generate_recommendations(assessment, profile)
        
        logger.info(f"患者风险评估完成，总体风险等级: {assessment['overall_risk_level']}")
        return assessment
    
    def _assess_hypertension(self, ha: Dict, profile: Dict) -> Dict:
        """高血压风险评估"""
        result = {
            'bp_grade': '未知',
            'risk_level': '低危',
            'risk_factors': [],
            'target_organ_damage': [],
            'clinical_conditions': [],
            'evaluation_logic': []
        }
        
        sbp = ha.get('sbp')
        dbp = ha.get('dbp')
        
        if sbp is None or dbp is None:
            return result
        
        # 血压分级
        if sbp < 120 and dbp < 80:
            result['bp_grade'] = '正常血压'
        elif sbp < 140 and dbp < 90:
            result['bp_grade'] = '正常高值'
        elif sbp < 160 or dbp < 100:
            result['bp_grade'] = '1级高血压'
        elif sbp < 180 or dbp < 110:
            result['bp_grade'] = '2级高血压'
        else:
            result['bp_grade'] = '3级高血压'
        
        result['evaluation_logic'].append(f"血压 {sbp}/{dbp} mmHg → {result['bp_grade']}")
        
        # 危险因素评估
        age = profile.get('age', 0)
        gender = profile.get('gender', '')
        bmi = profile.get('bmi')
        
        if (gender == '男' and age >= 55) or (gender == '女' and age >= 65):
            result['risk_factors'].append('年龄')
            result['evaluation_logic'].append(f"年龄 {age}岁，{gender}，属于高龄危险因素")
        
        if bmi and bmi >= 28:
            result['risk_factors'].append('肥胖')
            result['evaluation_logic'].append(f"BMI {bmi} ≥ 28，属于肥胖危险因素")
        
        # 从评估记录中提取危险因素
        risk_factors_str = ha.get('risk_factors', '')
        if risk_factors_str:
            for factor in ['吸烟', '血脂异常', '糖尿病', '肥胖', '高龄', '家族史']:
                if factor in risk_factors_str:
                    if factor not in result['risk_factors']:
                        result['risk_factors'].append(factor)
        
        # 靶器官损害
        target_damage = ha.get('target_organs_damage', '')
        if target_damage and target_damage != '无':
            for damage in ['左心室肥厚', '颈动脉斑块', '肾功能异常', '蛋白尿']:
                if damage in target_damage:
                    result['target_organ_damage'].append(damage)
        
        # 临床疾患
        clinical_cond = ha.get('clinical_conditions', '')
        if clinical_cond and clinical_cond != '无':
            for cond in ['冠心病', '脑卒中', '慢性肾病', '心力衰竭', '外周血管病']:
                if cond in clinical_cond:
                    result['clinical_conditions'].append(cond)
        
        # 风险分层
        risk_factors_count = len(result['risk_factors'])
        has_target_damage = len(result['target_organ_damage']) > 0
        has_clinical_cond = len(result['clinical_conditions']) > 0
        
        if has_clinical_cond:
            result['risk_level'] = '很高危'
            result['evaluation_logic'].append(f"存在临床疾患({', '.join(result['clinical_conditions'])}) → 很高危")
        elif has_target_damage or risk_factors_count >= 3:
            if result['bp_grade'] in ['2级高血压', '3级高血压']:
                result['risk_level'] = '很高危'
            else:
                result['risk_level'] = '高危'
            result['evaluation_logic'].append(f"存在靶器官损害或≥3个危险因素 → {result['risk_level']}")
        elif risk_factors_count >= 1:
            if result['bp_grade'] == '3级高血压':
                result['risk_level'] = '高危'
            elif result['bp_grade'] == '2级高血压':
                result['risk_level'] = '中危'
            else:
                result['risk_level'] = '中危'
            result['evaluation_logic'].append(f"{risk_factors_count}个危险因素 + {result['bp_grade']} → {result['risk_level']}")
        else:
            if result['bp_grade'] == '3级高血压':
                result['risk_level'] = '高危'
            elif result['bp_grade'] == '2级高血压':
                result['risk_level'] = '中危'
            else:
                result['risk_level'] = '低危'
            result['evaluation_logic'].append(f"无额外危险因素 + {result['bp_grade']} → {result['risk_level']}")
        
        return result
    
    def _assess_diabetes(self, da: Dict, profile: Dict) -> Dict:
        """糖尿病风险评估"""
        result = {
            'control_status': '未知',
            'risk_level': '低危',
            'risk_factors': [],
            'complications': [],
            'evaluation_logic': []
        }
        
        hba1c = da.get('hba1c')
        fasting_glucose = da.get('fasting_glucose')
        
        # 血糖控制评估
        if hba1c:
            if hba1c < 7.0:
                result['control_status'] = '控制良好'
                result['evaluation_logic'].append(f"HbA1c {hba1c}% < 7.0% → 控制良好")
            elif hba1c < 8.5:
                result['control_status'] = '控制一般'
                result['evaluation_logic'].append(f"HbA1c {hba1c}% 在 7.0-8.5% → 控制一般")
            else:
                result['control_status'] = '控制不佳'
                result['risk_level'] = '高危'
                result['evaluation_logic'].append(f"HbA1c {hba1c}% ≥ 8.5% → 控制不佳，高危")
        
        # 空腹血糖评估
        if fasting_glucose:
            if fasting_glucose >= 10.0:
                result['risk_factors'].append('空腹血糖过高')
                result['evaluation_logic'].append(f"空腹血糖 {fasting_glucose} mmol/L ≥ 10.0 → 危险因素")
        
        # 并发症评估
        complications_str = da.get('complications', '')
        if complications_str and complications_str != '无':
            for comp in ['视网膜病变', '周围神经病变', '肾病', '足病', '心血管病变']:
                if comp in complications_str:
                    result['complications'].append(comp)
            
            if result['complications']:
                result['risk_level'] = '高危'
                result['evaluation_logic'].append(f"存在并发症({', '.join(result['complications'])}) → 高危")
        
        # 胰岛素使用情况
        if da.get('insulin_usage'):
            result['risk_factors'].append('需要胰岛素治疗')
            result['evaluation_logic'].append(f"正在使用胰岛素({da.get('insulin_type', '')}) → 需密切监测")
        
        return result
    
    def _calculate_overall_risk(self, assessment: Dict, profile: Dict):
        """计算综合风险等级"""
        risk_levels = ['低危', '中危', '高危', '很高危']
        max_level = 0
        
        # 高血压风险
        if assessment['hypertension_risk']:
            ht_level = risk_levels.index(assessment['hypertension_risk']['risk_level'])
            max_level = max(max_level, ht_level)
            assessment['risk_factors'].extend(assessment['hypertension_risk']['risk_factors'])
        
        # 糖尿病风险
        if assessment['diabetes_risk']:
            dm_level = risk_levels.index(assessment['diabetes_risk']['risk_level'])
            max_level = max(max_level, dm_level)
            assessment['risk_factors'].extend(assessment['diabetes_risk']['risk_factors'])
        
        # 合并症加重风险
        if assessment['hypertension_risk'] and assessment['diabetes_risk']:
            # 高血压合并糖尿病，风险等级提升
            if max_level < 2:  # 如果不是高危/很高危
                max_level = 2  # 提升到高危
            assessment['risk_factors'].append('高血压合并糖尿病')
        
        # BMI评估
        bmi = profile.get('bmi')
        if bmi and bmi >= 28:
            if '肥胖' not in assessment['risk_factors']:
                assessment['risk_factors'].append('肥胖')
        
        # 去重
        assessment['risk_factors'] = list(set(assessment['risk_factors']))
        assessment['overall_risk_level'] = risk_levels[max_level]
    
    def _generate_follow_up_plan(self, assessment: Dict) -> Dict:
        """生成随访计划"""
        risk_level = assessment['overall_risk_level']
        
        plan = {
            'frequency': '',
            'next_visit': '',
            'monitoring_items': [],
            'lifestyle_goals': [],
            'medication_review': ''
        }
        
        today = datetime.now()
        
        if risk_level == '很高危':
            plan['frequency'] = '每2周随访'
            plan['next_visit'] = (today + timedelta(weeks=2)).strftime('%Y-%m-%d')
            plan['monitoring_items'] = ['血压(每日)', '血糖(每日)', '症状变化', '用药依从性']
            plan['medication_review'] = '2周后复诊评估疗效，必要时调整方案'
        elif risk_level == '高危':
            plan['frequency'] = '每月随访'
            plan['next_visit'] = (today + timedelta(weeks=4)).strftime('%Y-%m-%d')
            plan['monitoring_items'] = ['血压(每周3次)', '血糖(每周)', '体重', '用药依从性']
            plan['medication_review'] = '1个月后复诊，评估血压/血糖达标情况'
        elif risk_level == '中危':
            plan['frequency'] = '每2月随访'
            plan['next_visit'] = (today + timedelta(weeks=8)).strftime('%Y-%m-%d')
            plan['monitoring_items'] = ['血压(每周)', '血糖(每2周)', '体重', '生活方式执行']
            plan['medication_review'] = '2个月后复诊，评估控制效果'
        else:
            plan['frequency'] = '每3月随访'
            plan['next_visit'] = (today + timedelta(weeks=12)).strftime('%Y-%m-%d')
            plan['monitoring_items'] = ['血压(每2周)', '血糖(每月)', '体重']
            plan['medication_review'] = '3个月后常规复诊'
        
        plan['lifestyle_goals'] = [
            '低盐低脂饮食(每日盐<6g)',
            '规律运动(每周≥150分钟中等强度)',
            '控制体重(BMI<24)',
            '戒烟限酒',
            '保持良好睡眠'
        ]
        
        return plan
    
    def _generate_recommendations(self, assessment: Dict, profile: Dict) -> List[Dict]:
        """生成诊疗建议"""
        recommendations = []
        
        # 高血压相关建议
        if assessment['hypertension_risk']:
            ht = assessment['hypertension_risk']
            
            if ht['bp_grade'] in ['2级高血压', '3级高血压']:
                recommendations.append({
                    'category': '降压治疗',
                    'content': '建议起始联合治疗，推荐CCB+ACEI/ARB或CCB+利尿剂',
                    'evidence_level': 'ⅠA',
                    'source': '中国高血压防治指南2023',
                    'rationale': f"血压分级: {ht['bp_grade']}，需积极降压"
                })
            elif ht['bp_grade'] == '1级高血压':
                recommendations.append({
                    'category': '降压治疗',
                    'content': '建议起始单药治疗，首选CCB、ACEI/ARB或利尿剂',
                    'evidence_level': 'ⅠA',
                    'source': '中国高血压防治指南2023',
                    'rationale': f"血压分级: {ht['bp_grade']}，可先尝试单药治疗"
                })
        
        # 糖尿病相关建议
        if assessment['diabetes_risk']:
            dm = assessment['diabetes_risk']
            
            if dm['control_status'] == '控制不佳':
                recommendations.append({
                    'category': '降糖治疗',
                    'content': 'HbA1c≥8.5%，建议强化治疗，可考虑起始胰岛素或联合多种口服药',
                    'evidence_level': 'ⅠA',
                    'source': '中国2型糖尿病防治指南2020',
                    'rationale': f"HbA1c控制不佳，需加强降糖治疗"
                })
            elif dm['control_status'] == '控制一般':
                recommendations.append({
                    'category': '降糖治疗',
                    'content': '血糖控制一般，建议优化现有方案，可联合DPP-4抑制剂或SGLT-2抑制剂',
                    'evidence_level': 'ⅠA',
                    'source': '中国2型糖尿病防治指南2020',
                    'rationale': f"HbA1c未达标，需优化治疗"
                })
        
        # 合并症建议
        if assessment['hypertension_risk'] and assessment['diabetes_risk']:
            recommendations.append({
                'category': '综合管理',
                'content': '高血压合并糖尿病，优先选择ACEI/ARB类降压药（兼具心肾保护作用），'
                          '降糖药优先选择有心血管获益证据的SGLT-2抑制剂或GLP-1受体激动剂',
                'evidence_level': 'ⅠA',
                'source': '高血压/糖尿病联合指南',
                'rationale': '多重危险因素并存，需综合管理'
            })
        
        # 生活方式建议
        recommendations.append({
            'category': '生活方式干预',
            'content': '控制饮食（低盐低脂低糖）、规律运动、控制体重、戒烟限酒、'
                      '保持良好心态和睡眠',
            'evidence_level': 'ⅠA',
            'source': '各指南一致推荐',
            'rationale': '生活方式干预是治疗的基础'
        })
        
        return recommendations
    
    def check_emergency(self, profile: Dict) -> List[Dict]:
        """检查紧急情况"""
        warnings = []
        
        ha = profile.get('hypertension_assessment')
        if ha:
            sbp = ha.get('sbp')
            dbp = ha.get('dbp')
            
            # 高血压急症检查
            if sbp and sbp >= self.emergency_config['hypertensive_emergency']['sbp']:
                warnings.append({
                    'type': 'hypertensive_emergency',
                    'severity': 'critical',
                    'message': f'⚠️ 高血压急症警告：收缩压 {sbp} mmHg ≥ 180 mmHg！',
                    'action': '建议立即静脉降压治疗，目标1小时内降低不超过25%，需紧急转诊至急诊科',
                    'evidence': '中国高血压防治指南2023'
                })
            
            if dbp and dbp >= self.emergency_config['hypertensive_emergency']['dbp']:
                warnings.append({
                    'type': 'hypertensive_emergency',
                    'severity': 'critical',
                    'message': f'⚠️ 高血压急症警告：舒张压 {dbp} mmHg ≥ 120 mmHg！',
                    'action': '建议立即就医，需紧急降压治疗',
                    'evidence': '中国高血压防治指南2023'
                })
        
        da = profile.get('diabetes_assessment')
        if da:
            fasting_glucose = da.get('fasting_glucose')
            
            # 低血糖检查
            if fasting_glucose and fasting_glucose < self.emergency_config['hypoglycemia']['glucose']:
                warnings.append({
                    'type': 'hypoglycemia',
                    'severity': 'critical',
                    'message': f'⚠️ 低血糖警告：空腹血糖 {fasting_glucose} mmol/L < 3.9 mmol/L！',
                    'action': '立即补充糖分，监测血糖变化，必要时就医',
                    'evidence': '中国2型糖尿病防治指南2020'
                })
            
            # 糖尿病酮症酸中毒风险
            if fasting_glucose and fasting_glucose > self.emergency_config['diabetic_ketoacidosis']['glucose']:
                warnings.append({
                    'type': 'dka_risk',
                    'severity': 'warning',
                    'message': f'⚠️ 高血糖警告：空腹血糖 {fasting_glucose} mmol/L > 16.7 mmol/L',
                    'action': '注意观察有无酮症酸中毒症状（恶心、呕吐、腹痛、呼吸深快），及时就医',
                    'evidence': '中国2型糖尿病防治指南2020'
                })
        
        return warnings


# 全局风险评估引擎实例
_risk_engine = None

def get_risk_engine() -> RiskEngine:
    """获取全局风险评估引擎实例"""
    global _risk_engine
    if _risk_engine is None:
        _risk_engine = RiskEngine()
    return _risk_engine

