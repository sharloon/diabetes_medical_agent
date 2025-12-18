"""
安全预警模块 - 医学伦理和安全校验
"""
from typing import Dict, List, Optional
from loguru import logger

from config import DRUG_CONTRAINDICATIONS, EMERGENCY_THRESHOLDS


class SafetyGuard:
    """安全预警服务"""
    
    def __init__(self):
        self.contraindications = DRUG_CONTRAINDICATIONS
        self.emergency_thresholds = EMERGENCY_THRESHOLDS
        logger.info("安全预警模块初始化完成")
    
    def check_all(self, profile: Dict, recommendations: List[Dict] = None) -> Dict:
        """
        执行所有安全检查
        
        Args:
            profile: 患者档案
            recommendations: 诊疗建议列表
            
        Returns:
            Dict: 安全检查结果
        """
        logger.info(f"开始安全检查，患者ID: {profile.get('patient_id', 'N/A')}")
        
        result = {
            'is_safe': True,
            'warnings': [],
            'contraindications': [],
            'interactions': [],
            'emergency_alerts': []
        }
        
        # 1. 检查孕妇用药禁忌
        pregnancy_warnings = self._check_pregnancy_contraindications(profile, recommendations)
        result['contraindications'].extend(pregnancy_warnings)
        
        # 2. 检查高血压急症
        emergency_alerts = self._check_hypertensive_emergency(profile)
        result['emergency_alerts'].extend(emergency_alerts)
        
        # 3. 检查药物禁忌
        drug_warnings = self._check_drug_contraindications(profile)
        result['contraindications'].extend(drug_warnings)
        
        # 4. 检查药物相互作用
        interactions = self._check_drug_interactions(profile)
        result['interactions'].extend(interactions)
        
        # 5. 检查特殊人群用药
        special_warnings = self._check_special_population(profile)
        result['warnings'].extend(special_warnings)
        
        # 6. 检查低血糖/高血糖风险
        glucose_alerts = self._check_glucose_emergency(profile)
        result['emergency_alerts'].extend(glucose_alerts)
        
        # 汇总所有警告
        all_warnings = (result['warnings'] + result['contraindications'] + 
                       result['interactions'] + result['emergency_alerts'])
        
        # 判断是否安全
        critical_count = sum(1 for w in all_warnings if w.get('severity') == 'critical')
        result['is_safe'] = critical_count == 0
        
        logger.info(f"安全检查完成，共{len(all_warnings)}条警告，"
                   f"危急警告{critical_count}条，是否安全: {result['is_safe']}")
        
        return result
    
    def _check_pregnancy_contraindications(self, profile: Dict, 
                                           recommendations: List[Dict] = None) -> List[Dict]:
        """检查孕妇用药禁忌"""
        warnings = []
        
        # 检查是否为孕妇
        is_pregnant = self._is_pregnant(profile)
        if not is_pregnant:
            return warnings
        
        # 获取当前用药
        current_meds = profile.get('medications', [])
        med_names = [med.get('drug_name', '').lower() for med in current_meds]
        med_classes = [med.get('drug_class', '').upper() for med in current_meds]
        
        # 检查ACEI/ARB类药物
        acei_drugs = [d.lower() for d in self.contraindications['ACEI类']['drugs']]
        arb_drugs = [d.lower() for d in self.contraindications['ARB类']['drugs']]
        
        for med_name in med_names:
            if med_name in acei_drugs or any(acei in med_name for acei in ['普利', 'pril']):
                warnings.append({
                    'type': 'pregnancy_contraindication',
                    'severity': 'critical',
                    'drug': med_name,
                    'drug_class': 'ACEI类',
                    'message': f'⚠️ 严重警告：孕妇禁用ACEI类药物（{med_name}）！',
                    'reason': 'ACEI类药物可导致胎儿畸形、羊水过少、胎儿肾功能损害',
                    'alternative': '建议使用甲基多巴、拉贝洛尔或硝苯地平缓释片',
                    'action': '立即停用该药物，建议产科会诊',
                    'evidence': '中国高血压防治指南2023'
                })
            
            if med_name in arb_drugs or any(arb in med_name for arb in ['沙坦', 'sartan']):
                warnings.append({
                    'type': 'pregnancy_contraindication',
                    'severity': 'critical',
                    'drug': med_name,
                    'drug_class': 'ARB类',
                    'message': f'⚠️ 严重警告：孕妇禁用ARB类药物（{med_name}）！',
                    'reason': 'ARB类药物可导致胎儿畸形、羊水过少、胎儿肾功能损害',
                    'alternative': '建议使用甲基多巴、拉贝洛尔或硝苯地平缓释片',
                    'action': '立即停用该药物，建议产科会诊',
                    'evidence': '中国高血压防治指南2023'
                })
        
        # 检查药物类别
        if 'ACEI' in med_classes or 'ARB' in med_classes:
            if not any(w['drug_class'] in ['ACEI类', 'ARB类'] for w in warnings):
                warnings.append({
                    'type': 'pregnancy_contraindication',
                    'severity': 'critical',
                    'drug_class': 'ACEI/ARB',
                    'message': '⚠️ 严重警告：孕妇禁用ACEI/ARB类药物！',
                    'reason': '此类药物可导致胎儿发育异常',
                    'alternative': '建议使用甲基多巴、拉贝洛尔或硝苯地平缓释片',
                    'action': '建议产科会诊',
                    'evidence': '中国高血压防治指南2023'
                })
        
        # 检查推荐方案中是否包含禁忌药物
        if recommendations:
            for rec in recommendations:
                content = rec.get('content', '').lower()
                if 'acei' in content or 'arb' in content or '普利' in content or '沙坦' in content:
                    warnings.append({
                        'type': 'recommendation_contraindication',
                        'severity': 'critical',
                        'message': '⚠️ 警告：推荐方案中包含孕妇禁用药物！',
                        'reason': '患者为孕妇，ACEI/ARB类药物绝对禁忌',
                        'action': '请重新评估治疗方案，选择孕妇安全用药',
                        'evidence': '妊娠期高血压疾病诊治指南'
                    })
        
        return warnings
    
    def _is_pregnant(self, profile: Dict) -> bool:
        """判断患者是否为孕妇"""
        # 检查性别
        gender = profile.get('gender', '')
        if gender != '女':
            return False
        
        # 检查诊断记录中是否有妊娠相关诊断
        diagnoses = profile.get('diagnoses', [])
        pregnancy_keywords = ['妊娠', '孕', '怀孕', 'pregnancy', 'pregnant', '产前', '产后']
        
        for diag in diagnoses:
            diag_name = diag.get('diagnosis_name', '').lower()
            for keyword in pregnancy_keywords:
                if keyword in diag_name:
                    return True
        
        # 检查年龄（育龄期女性需要特别关注）
        age = profile.get('age', 0)
        if 18 <= age <= 45:
            # 可能是育龄期女性，需要进一步确认
            # 这里返回False，但可以添加警告
            pass
        
        return False
    
    def _check_hypertensive_emergency(self, profile: Dict) -> List[Dict]:
        """检查高血压急症"""
        alerts = []
        
        ha = profile.get('hypertension_assessment')
        if not ha:
            return alerts
        
        sbp = ha.get('sbp')
        dbp = ha.get('dbp')
        
        threshold = self.emergency_thresholds['hypertensive_emergency']
        
        if sbp and sbp >= threshold['sbp']:
            alert = {
                'type': 'hypertensive_emergency',
                'severity': 'critical',
                'message': f'🚨 高血压急症：收缩压 {sbp} mmHg ≥ {threshold["sbp"]} mmHg',
                'symptoms_to_check': threshold['symptoms'],
                'immediate_action': [
                    '1. 立即评估意识状态和生命体征',
                    '2. 建立静脉通路',
                    '3. 立即给予静脉降压药物（乌拉地尔、硝普钠等）',
                    '4. 目标：1小时内降低血压不超过25%',
                    '5. 紧急转诊至急诊科/心内科'
                ],
                'evidence': '中国高血压防治指南2023',
                'requires_referral': True,
                'referral_department': '急诊科/心内科'
            }
            alerts.append(alert)
        
        if dbp and dbp >= threshold['dbp']:
            if not any(a['type'] == 'hypertensive_emergency' for a in alerts):
                alerts.append({
                    'type': 'hypertensive_emergency',
                    'severity': 'critical',
                    'message': f'🚨 高血压急症：舒张压 {dbp} mmHg ≥ {threshold["dbp"]} mmHg',
                    'immediate_action': ['紧急降压治疗', '转诊至急诊科'],
                    'evidence': '中国高血压防治指南2023',
                    'requires_referral': True
                })
        
        return alerts
    
    def _check_drug_contraindications(self, profile: Dict) -> List[Dict]:
        """检查药物禁忌"""
        warnings = []
        
        current_meds = profile.get('medications', [])
        if not current_meds:
            return warnings
        
        diagnoses = profile.get('diagnoses', [])
        diag_names = [d.get('diagnosis_name', '').lower() for d in diagnoses]
        
        for med in current_meds:
            drug_name = med.get('drug_name', '')
            drug_class = med.get('drug_class', '')
            
            # 检查各类药物禁忌
            for class_name, info in self.contraindications.items():
                drugs = [d.lower() for d in info['drugs']]
                
                if drug_name.lower() in drugs or class_name in drug_class:
                    for contra in info['contraindications']:
                        contra_lower = contra.lower()
                        # 检查诊断中是否有禁忌症
                        for diag_name in diag_names:
                            if contra_lower in diag_name or diag_name in contra_lower:
                                warnings.append({
                                    'type': 'drug_contraindication',
                                    'severity': 'warning',
                                    'drug': drug_name,
                                    'drug_class': class_name,
                                    'contraindication': contra,
                                    'message': f'⚠️ 用药警告：{drug_name}（{class_name}）在{contra}患者中应慎用或禁用',
                                    'action': '请评估获益/风险比，考虑替代药物'
                                })
        
        return warnings
    
    def _check_drug_interactions(self, profile: Dict) -> List[Dict]:
        """检查药物相互作用"""
        interactions = []
        
        current_meds = profile.get('medications', [])
        if len(current_meds) < 2:
            return interactions
        
        med_classes = [med.get('drug_class', '') for med in current_meds]
        med_names = [med.get('drug_name', '') for med in current_meds]
        
        # 检查已知的相互作用
        interaction_pairs = [
            (['ACEI', 'ARB'], ['保钾利尿剂', '螺内酯'], '高钾血症风险增加'),
            (['β受体阻滞剂'], ['非二氢吡啶类CCB', '地尔硫䓬', '维拉帕米'], '严重心动过缓风险'),
            (['ACEI', 'ARB'], ['NSAIDs', '布洛芬', '双氯芬酸'], '降压效果减弱，肾功能损害风险'),
            (['利尿剂'], ['锂盐'], '锂中毒风险'),
            (['β受体阻滞剂'], ['胰岛素'], '可能掩盖低血糖症状'),
        ]
        
        for group1, group2, risk in interaction_pairs:
            has_group1 = any(g in ' '.join(med_classes + med_names) for g in group1)
            has_group2 = any(g in ' '.join(med_classes + med_names) for g in group2)
            
            if has_group1 and has_group2:
                interactions.append({
                    'type': 'drug_interaction',
                    'severity': 'warning',
                    'drugs': [group1, group2],
                    'message': f'⚠️ 药物相互作用：{"/".join(group1)} + {"/".join(group2)} → {risk}',
                    'action': '密切监测，必要时调整剂量或更换药物'
                })
        
        return interactions
    
    def _check_special_population(self, profile: Dict) -> List[Dict]:
        """检查特殊人群用药"""
        warnings = []
        
        age = profile.get('age', 0)
        
        # 老年人用药注意
        if age >= 65:
            warnings.append({
                'type': 'special_population',
                'severity': 'info',
                'population': '老年患者',
                'message': '📋 老年患者用药注意：建议从小剂量开始，缓慢增量，密切监测',
                'considerations': [
                    '肾功能可能减退，需调整药物剂量',
                    '多药联用风险增加，注意药物相互作用',
                    '跌倒风险增加，降压不宜过快',
                    '血压目标可适当放宽（<150/90 mmHg）'
                ]
            })
        
        # 肾功能不全检查
        diagnoses = profile.get('diagnoses', [])
        for diag in diagnoses:
            diag_name = diag.get('diagnosis_name', '').lower()
            if '肾' in diag_name and ('功能不全' in diag_name or '衰竭' in diag_name or '病' in diag_name):
                warnings.append({
                    'type': 'special_population',
                    'severity': 'warning',
                    'population': '肾功能不全',
                    'message': '⚠️ 肾功能不全患者用药注意',
                    'considerations': [
                        '二甲双胍慎用或禁用（eGFR<45禁用）',
                        '需调整经肾排泄药物剂量',
                        'ACEI/ARB类需监测肾功能和血钾',
                        '避免使用NSAIDs类药物'
                    ]
                })
                break
        
        return warnings
    
    def _check_glucose_emergency(self, profile: Dict) -> List[Dict]:
        """检查血糖紧急情况"""
        alerts = []
        
        da = profile.get('diabetes_assessment')
        if not da:
            return alerts
        
        fasting_glucose = da.get('fasting_glucose')
        
        # 低血糖检查
        if fasting_glucose and fasting_glucose < 3.9:
            alerts.append({
                'type': 'hypoglycemia',
                'severity': 'critical',
                'message': f'🚨 低血糖警告：血糖 {fasting_glucose} mmol/L < 3.9 mmol/L',
                'symptoms': ['出汗', '心悸', '颤抖', '饥饿感', '焦虑', '意识模糊'],
                'immediate_action': [
                    '1. 立即进食15-20g快速作用碳水化合物',
                    '2. 15分钟后复测血糖',
                    '3. 如未改善，重复进食',
                    '4. 严重低血糖（意识障碍）需急救处理'
                ]
            })
        
        # 严重高血糖检查
        if fasting_glucose and fasting_glucose > 16.7:
            alerts.append({
                'type': 'severe_hyperglycemia',
                'severity': 'warning',
                'message': f'⚠️ 严重高血糖：血糖 {fasting_glucose} mmol/L > 16.7 mmol/L',
                'risk': '糖尿病酮症酸中毒(DKA)风险',
                'symptoms_to_monitor': ['口渴多饮', '多尿', '恶心呕吐', '腹痛', '呼吸深快', '意识改变'],
                'action': '及时就医，监测酮体，必要时住院治疗'
            })
        
        return alerts
    
    def generate_safety_report(self, profile: Dict, 
                               recommendations: List[Dict] = None) -> str:
        """生成安全报告"""
        check_result = self.check_all(profile, recommendations)
        
        report_lines = ['=' * 50, '安全检查报告', '=' * 50, '']
        
        # 总体评估
        if check_result['is_safe']:
            report_lines.append('✅ 总体评估：未发现危急安全问题')
        else:
            report_lines.append('❌ 总体评估：存在需要立即处理的安全问题')
        
        report_lines.append('')
        
        # 危急警报
        if check_result['emergency_alerts']:
            report_lines.append('【危急警报】')
            for alert in check_result['emergency_alerts']:
                report_lines.append(f"  {alert['message']}")
                if 'immediate_action' in alert:
                    for action in alert['immediate_action']:
                        report_lines.append(f"    → {action}")
            report_lines.append('')
        
        # 禁忌症警告
        if check_result['contraindications']:
            report_lines.append('【禁忌症警告】')
            for contra in check_result['contraindications']:
                report_lines.append(f"  {contra['message']}")
                if 'alternative' in contra:
                    report_lines.append(f"    替代方案: {contra['alternative']}")
            report_lines.append('')
        
        # 药物相互作用
        if check_result['interactions']:
            report_lines.append('【药物相互作用】')
            for interaction in check_result['interactions']:
                report_lines.append(f"  {interaction['message']}")
            report_lines.append('')
        
        # 一般警告
        if check_result['warnings']:
            report_lines.append('【注意事项】')
            for warning in check_result['warnings']:
                report_lines.append(f"  {warning['message']}")
            report_lines.append('')
        
        if not any([check_result['emergency_alerts'], check_result['contraindications'],
                   check_result['interactions'], check_result['warnings']]):
            report_lines.append('未发现安全问题。')
        
        report_lines.append('=' * 50)
        
        return '\n'.join(report_lines)


# 全局安全预警实例
_safety_guard = None

def get_safety_guard() -> SafetyGuard:
    """获取全局安全预警实例"""
    global _safety_guard
    if _safety_guard is None:
        _safety_guard = SafetyGuard()
    return _safety_guard

