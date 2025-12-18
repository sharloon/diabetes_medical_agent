"""
诊疗决策智能体 - 核心临床推理引擎
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from loguru import logger

from llm_client import get_llm_client, MEDICAL_SYSTEM_PROMPT
from db_service import get_db_service
from rag_service import get_rag_service
from risk_engine import get_risk_engine
from safety_guard import get_safety_guard
from term_mapper import get_term_mapper
from utils import format_patient_profile


class DiagnosisAgent:
    """诊疗决策智能体"""
    
    def __init__(self):
        self.llm_client = get_llm_client()
        self.db_service = get_db_service()
        self.rag_service = get_rag_service()
        self.risk_engine = get_risk_engine()
        self.safety_guard = get_safety_guard()
        self.term_mapper = get_term_mapper()
        
        logger.info("诊疗决策智能体初始化完成")
    
    def build_patient_profile(self, patient_id: str) -> Dict:
        """
        构建患者画像
        
        Args:
            patient_id: 患者ID
            
        Returns:
            Dict: 完整患者画像
        """
        logger.info(f"开始构建患者画像，患者ID: {patient_id}")
        
        try:
            profile = self.db_service.get_patient_full_profile(patient_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': f'未找到患者ID: {patient_id}',
                    'patient_id': patient_id
                }
            
            # 添加风险评估
            risk_assessment = self.risk_engine.assess_patient(profile)
            profile['risk_assessment'] = risk_assessment
            
            # 添加安全检查
            safety_check = self.safety_guard.check_all(profile)
            profile['safety_check'] = safety_check
            
            # 格式化输出
            profile['formatted_text'] = format_patient_profile(profile)
            profile['success'] = True
            
            logger.info(f"患者画像构建完成，风险等级: {risk_assessment.get('overall_risk_level')}")
            return profile
            
        except Exception as e:
            logger.error(f"构建患者画像失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'patient_id': patient_id
            }
    
    def assess_risk(self, patient_id: str) -> Dict:
        """
        风险分层评估
        
        Args:
            patient_id: 患者ID
            
        Returns:
            Dict: 风险评估结果，包含风险等级和随访计划
        """
        logger.info(f"开始风险分层评估，患者ID: {patient_id}")
        
        try:
            profile = self.db_service.get_patient_full_profile(patient_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': f'未找到患者: {patient_id}'
                }
            
            # 执行风险评估
            assessment = self.risk_engine.assess_patient(profile)
            
            # 查询相关指南推荐
            rag_results = self.rag_service.search_all_sources(
                f"高血压风险评估 {assessment.get('overall_risk_level', '')}",
                top_k=3
            )
            
            # 使用LLM生成评估解读
            prompt = f"""基于以下患者风险评估结果，请生成详细的评估解读和建议：

患者信息：
{format_patient_profile(profile)}

风险评估结果：
- 总体风险等级: {assessment.get('overall_risk_level')}
- 高血压风险: {assessment.get('hypertension_risk', {}).get('risk_level', 'N/A')}
- 糖尿病风险: {assessment.get('diabetes_risk', {}).get('risk_level', 'N/A')}
- 危险因素: {', '.join(assessment.get('risk_factors', []))}

请提供：
1. 风险评估逻辑解释
2. 具体的随访计划
3. 需要监测的指标
4. 注意事项"""
            
            interpretation = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'patient_id': patient_id,
                'assessment': assessment,
                'interpretation': interpretation,
                'rag_sources': [hit.get('source') for hit in rag_results.get('pdf_results', [])[:3]]
            }
            
            logger.info(f"风险评估完成，结果: {assessment.get('overall_risk_level')}")
            return result
            
        except Exception as e:
            logger.error(f"风险评估失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_drug_conflicts(self, patient_id: str) -> Dict:
        """
        用药冲突检测
        
        Args:
            patient_id: 患者ID
            
        Returns:
            Dict: 用药冲突检测结果
        """
        logger.info(f"开始用药冲突检测，患者ID: {patient_id}")
        
        try:
            profile = self.db_service.get_patient_full_profile(patient_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': f'未找到患者: {patient_id}'
                }
            
            # 执行安全检查
            safety_result = self.safety_guard.check_all(profile)
            
            # 获取相关药物知识
            medications = profile.get('medications', [])
            drug_names = [m.get('drug_name', '') for m in medications]
            
            if drug_names:
                rag_query = f"药物相互作用 禁忌 {' '.join(drug_names[:5])}"
                rag_results = self.rag_service.search_all_sources(rag_query, top_k=3)
            else:
                rag_results = {'pdf_results': []}
            
            # 使用LLM生成详细分析
            prompt = f"""请分析以下患者的用药情况，检测可能的药物冲突和禁忌：

患者信息：
- 年龄: {profile.get('age')}岁
- 性别: {profile.get('gender')}
- 诊断: {', '.join([d.get('diagnosis_name', '') for d in profile.get('diagnoses', [])])}

当前用药：
{chr(10).join([f"- {m.get('drug_name', '')} {m.get('dosage', '')} {m.get('frequency', '')}" for m in medications])}

系统检测到的问题：
禁忌症: {len(safety_result.get('contraindications', []))}条
药物相互作用: {len(safety_result.get('interactions', []))}条

请提供：
1. 用药安全性评估
2. 潜在的药物相互作用分析
3. 改进建议（如有）"""
            
            analysis = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'patient_id': patient_id,
                'current_medications': medications,
                'safety_check': safety_result,
                'analysis': analysis,
                'has_conflicts': len(safety_result.get('contraindications', [])) > 0 or 
                               len(safety_result.get('interactions', [])) > 0,
                'rag_sources': [hit.get('source') for hit in rag_results.get('pdf_results', [])[:3]]
            }
            
            logger.info(f"用药冲突检测完成，发现{len(safety_result.get('contraindications', []))}条禁忌，"
                       f"{len(safety_result.get('interactions', []))}条相互作用")
            return result
            
        except Exception as e:
            logger.error(f"用药冲突检测失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_diagnosis(self, symptoms: str, exam_data: Dict = None,
                          patient_id: str = None) -> Dict:
        """
        诊断推理 - 生成鉴别诊断列表
        
        Args:
            symptoms: 症状描述
            exam_data: 检查数据
            patient_id: 患者ID（可选）
            
        Returns:
            Dict: 鉴别诊断结果
        """
        logger.info(f"开始诊断推理，症状: {symptoms[:50]}...")
        
        try:
            # 获取患者背景信息
            patient_context = ""
            if patient_id:
                profile = self.db_service.get_patient_full_profile(patient_id)
                if profile:
                    patient_context = format_patient_profile(profile)
            
            # 术语标准化
            normalized_symptoms, replacements = self.term_mapper.normalize_text(symptoms)
            
            # RAG检索相关知识
            rag_results = self.rag_service.search_all_sources(
                f"鉴别诊断 {normalized_symptoms}",
                top_k=5
            )
            
            # 构建上下文
            context_parts = []
            for hit in rag_results.get('pdf_results', [])[:3]:
                context_parts.append(hit.get('content', ''))
            
            rag_context = "\n\n".join(context_parts) if context_parts else "暂无相关参考信息"
            
            # 构建检查数据描述
            exam_desc = ""
            if exam_data:
                exam_items = []
                if exam_data.get('sbp') and exam_data.get('dbp'):
                    exam_items.append(f"血压: {exam_data['sbp']}/{exam_data['dbp']} mmHg")
                if exam_data.get('hba1c'):
                    exam_items.append(f"HbA1c: {exam_data['hba1c']}%")
                if exam_data.get('fasting_glucose'):
                    exam_items.append(f"空腹血糖: {exam_data['fasting_glucose']} mmol/L")
                if exam_data.get('bmi'):
                    exam_items.append(f"BMI: {exam_data['bmi']}")
                exam_desc = "\n".join(exam_items)
            
            # 使用LLM生成鉴别诊断
            prompt = f"""请基于以下信息进行诊断推理，生成鉴别诊断列表：

【主诉/症状】
{normalized_symptoms}

【检查数据】
{exam_desc if exam_desc else '暂无'}

【患者背景】
{patient_context if patient_context else '暂无'}

【参考资料】
{rag_context}

请提供：
1. 至少3个鉴别诊断，按可能性从高到低排序
2. 每个诊断的概率估计（高/中/低）
3. 支持该诊断的依据
4. 完整的推理路径

输出格式：
## 鉴别诊断列表

### 1. [诊断名称] - 可能性: [高/中/低]
- 支持依据: ...
- 不支持依据: ...

### 2. [诊断名称] - 可能性: [高/中/低]
...

## 推理路径
1. 首先分析主要症状...
2. 结合检查结果...
3. 考虑到患者背景...
4. 综合判断..."""
            
            diagnosis_result = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'input': {
                    'symptoms': symptoms,
                    'normalized_symptoms': normalized_symptoms,
                    'exam_data': exam_data,
                    'patient_id': patient_id
                },
                'diagnosis_result': diagnosis_result,
                'term_mappings': replacements,
                'sources': [hit.get('source') for hit in rag_results.get('pdf_results', [])[:5]]
            }
            
            logger.info("诊断推理完成")
            return result
            
        except Exception as e:
            logger.error(f"诊断推理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def generate_treatment_plan(self, patient_id: str = None, 
                                diagnosis: str = None,
                                custom_profile: Dict = None) -> Dict:
        """
        生成个性化治疗方案
        
        Args:
            patient_id: 患者ID
            diagnosis: 诊断
            custom_profile: 自定义患者信息
            
        Returns:
            Dict: 治疗方案
        """
        logger.info(f"开始生成治疗方案，患者ID: {patient_id}, 诊断: {diagnosis}")
        
        try:
            # 获取或构建患者档案
            if patient_id:
                profile = self.db_service.get_patient_full_profile(patient_id)
            elif custom_profile:
                profile = custom_profile
            else:
                return {
                    'success': False,
                    'error': '请提供患者ID或患者信息'
                }
            
            if not profile:
                return {
                    'success': False,
                    'error': f'未找到患者: {patient_id}'
                }
            
            # 风险评估
            risk_assessment = self.risk_engine.assess_patient(profile)
            
            # 安全检查
            safety_check = self.safety_guard.check_all(profile)
            
            # RAG检索治疗指南
            search_query = f"治疗方案 {diagnosis or ''} {risk_assessment.get('overall_risk_level', '')}"
            rag_results = self.rag_service.search_all_sources(search_query, top_k=5)
            
            # 构建参考上下文
            context_parts = []
            for hit in rag_results.get('pdf_results', []):
                source = hit.get('source', {})
                context_parts.append(f"[{source.get('filename', '')} P{source.get('page', '')}] {hit.get('content', '')[:500]}")
            
            for hit in rag_results.get('mysql_results', []):
                if hit.get('evidence_level'):
                    context_parts.append(f"[指南推荐 {hit.get('evidence_level')}] {hit.get('content', '')}")
            
            rag_context = "\n\n".join(context_parts) if context_parts else "暂无相关参考信息"
            
            # 安全警告
            safety_warnings = ""
            if safety_check.get('emergency_alerts'):
                safety_warnings += "\n⚠️ 紧急警报:\n" + "\n".join([a['message'] for a in safety_check['emergency_alerts']])
            if safety_check.get('contraindications'):
                safety_warnings += "\n⚠️ 禁忌症:\n" + "\n".join([c['message'] for c in safety_check['contraindications']])
            
            # 使用LLM生成治疗方案
            prompt = f"""请为以下患者制定个性化治疗方案：

【患者信息】
{format_patient_profile(profile)}

【风险评估】
- 总体风险等级: {risk_assessment.get('overall_risk_level')}
- 危险因素: {', '.join(risk_assessment.get('risk_factors', []))}

【诊断】
{diagnosis or '高血压/糖尿病'}

【安全注意事项】
{safety_warnings if safety_warnings else '暂无特殊警告'}

【参考指南】
{rag_context}

请提供完整的治疗方案，包括：

## 一、治疗目标
- 血压目标: 
- 血糖目标:
- 其他目标:

## 二、药物治疗
1. 药物名称 | 剂量 | 频次 | 证据等级 | 选择依据
2. ...

## 三、生活方式干预
1. 饮食建议
2. 运动建议
3. 其他

## 四、随访计划
- 下次随访时间:
- 监测指标:
- 复查项目:

## 五、注意事项
- 用药注意
- 警示症状

请确保所有建议标注证据等级（如ⅠA、ⅡB等），并注明出处。"""
            
            treatment_plan = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'patient_id': patient_id,
                'diagnosis': diagnosis,
                'risk_assessment': risk_assessment,
                'safety_check': safety_check,
                'treatment_plan': treatment_plan,
                'sources': [
                    {'type': hit.get('source', {}).get('type'), 
                     'ref': f"{hit.get('source', {}).get('filename', '')} P{hit.get('source', {}).get('page', '')}"}
                    for hit in rag_results.get('pdf_results', [])[:5]
                ]
            }
            
            logger.info("治疗方案生成完成")
            return result
            
        except Exception as e:
            logger.error(f"治疗方案生成失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def adjust_treatment(self, patient_id: str, current_plan: str,
                        treatment_response: str, duration: str = "2周") -> Dict:
        """
        动态调整治疗方案
        
        Args:
            patient_id: 患者ID
            current_plan: 当前治疗方案
            treatment_response: 治疗反应描述
            duration: 治疗持续时间
            
        Returns:
            Dict: 调整后的方案
        """
        logger.info(f"开始调整治疗方案，患者ID: {patient_id}")
        
        try:
            profile = self.db_service.get_patient_full_profile(patient_id)
            
            if not profile:
                return {
                    'success': False,
                    'error': f'未找到患者: {patient_id}'
                }
            
            # RAG检索相关信息
            rag_results = self.rag_service.search_all_sources(
                f"治疗效果不佳 方案调整 {treatment_response}",
                top_k=3
            )
            
            # 使用LLM生成调整方案
            prompt = f"""患者治疗{duration}后效果不佳，请重新评估并调整方案：

【患者信息】
{format_patient_profile(profile)}

【当前治疗方案】
{current_plan}

【治疗反应】
{treatment_response}

【治疗持续时间】
{duration}

请提供：

## 一、疗效评估
- 目标达成情况分析
- 效果不佳的可能原因

## 二、方案调整
1. 具体调整内容（药物、剂量等）
2. 调整依据
3. 证据等级

## 三、调整逻辑说明
- 为什么需要这样调整
- 预期效果

## 四、新的随访计划
- 下次评估时间
- 关注指标

请确保所有调整都有循证依据支持。"""
            
            adjusted_plan = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'patient_id': patient_id,
                'original_plan': current_plan,
                'treatment_response': treatment_response,
                'duration': duration,
                'adjusted_plan': adjusted_plan,
                'sources': [hit.get('source') for hit in rag_results.get('pdf_results', [])[:3]]
            }
            
            logger.info("治疗方案调整完成")
            return result
            
        except Exception as e:
            logger.error(f"治疗方案调整失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def soap_consultation(self, chief_complaint: str, 
                         patient_id: str = None,
                         conversation_history: List[Dict] = None) -> Dict:
        """
        SOAP格式结构化问诊
        
        Args:
            chief_complaint: 主诉
            patient_id: 患者ID（可选）
            conversation_history: 对话历史
            
        Returns:
            Dict: SOAP问诊结果或追问
        """
        logger.info(f"开始SOAP问诊，主诉: {chief_complaint[:30]}...")
        
        try:
            # 获取患者背景
            patient_context = ""
            if patient_id:
                profile = self.db_service.get_patient_full_profile(patient_id)
                if profile:
                    patient_context = format_patient_profile(profile)
            
            # 分析主诉是否信息完整
            prompt = f"""你是一位经验丰富的临床医生，正在对患者进行问诊。

患者主诉: {chief_complaint}

患者背景信息:
{patient_context if patient_context else '暂无'}

对话历史:
{self._format_conversation_history(conversation_history) if conversation_history else '无'}

请按照SOAP格式进行问诊。如果信息不足以完成评估，请提出需要澄清的问题。

【信息完整性检查】
对于"头晕"等症状，需要了解：
- 症状特点（性质、持续时间、频率）
- 伴随症状（头痛、恶心、视物模糊等）
- 诱发/缓解因素
- 血压等生命体征数值
- 既往病史、用药史

如果以上关键信息缺失，请提出具体问题。如果信息足够，请生成完整的SOAP记录。

请回复格式：
如果需要追问：
[NEED_MORE_INFO]
问题：[具体问题列表]

如果信息足够：
[SOAP_COMPLETE]
S (Subjective 主观资料):
O (Objective 客观资料):
A (Assessment 评估):
P (Plan 计划):"""
            
            response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            # 解析响应
            if '[NEED_MORE_INFO]' in response:
                # 需要追问
                questions_part = response.split('[NEED_MORE_INFO]')[1]
                result = {
                    'success': True,
                    'status': 'need_clarification',
                    'questions': questions_part.strip(),
                    'chief_complaint': chief_complaint
                }
            else:
                # SOAP记录完成
                soap_content = response
                if '[SOAP_COMPLETE]' in response:
                    soap_content = response.split('[SOAP_COMPLETE]')[1]
                
                result = {
                    'success': True,
                    'status': 'complete',
                    'soap_record': soap_content.strip(),
                    'chief_complaint': chief_complaint
                }
            
            logger.info(f"SOAP问诊完成，状态: {result.get('status')}")
            return result
            
        except Exception as e:
            logger.error(f"SOAP问诊失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _format_conversation_history(self, history: List[Dict]) -> str:
        """格式化对话历史"""
        if not history:
            return ""
        
        lines = []
        for msg in history[-10:]:  # 只保留最近10条
            role = "医生" if msg.get('role') == 'assistant' else "患者"
            lines.append(f"{role}: {msg.get('content', '')}")
        
        return "\n".join(lines)
    
    def process_emergency(self, symptoms: str, vital_signs: Dict) -> Dict:
        """
        处理紧急情况（高血压急症等）
        
        Args:
            symptoms: 症状描述
            vital_signs: 生命体征 {sbp, dbp, heart_rate, etc.}
            
        Returns:
            Dict: 急救建议
        """
        logger.info(f"处理紧急情况，症状: {symptoms[:50]}...")
        
        try:
            # 检查是否为高血压急症
            sbp = vital_signs.get('sbp', 0)
            dbp = vital_signs.get('dbp', 0)
            
            is_emergency = sbp >= 180 or dbp >= 120
            emergency_symptoms = ['头痛', '呕吐', '视物模糊', '意识障碍', '胸痛']
            has_danger_symptoms = any(s in symptoms for s in emergency_symptoms)
            
            # RAG检索急救指南
            rag_results = self.rag_service.search_all_sources(
                "高血压急症 紧急处理 静脉降压",
                top_k=3
            )
            
            # 构建提示
            prompt = f"""紧急评估请求：

【症状】
{symptoms}

【生命体征】
- 血压: {sbp}/{dbp} mmHg
- 心率: {vital_signs.get('heart_rate', 'N/A')} 次/分

【初步判断】
- 是否高血压急症: {'是' if is_emergency else '否'}
- 是否有危险症状: {'是' if has_danger_symptoms else '否'}

请提供：
1. 紧急程度判断（危急/紧急/一般）
2. 是否需要转诊
3. 立即需要采取的措施
4. 相关指南依据（2023版）"""
            
            emergency_response = self.llm_client.generate(
                prompt=prompt,
                system_prompt=MEDICAL_SYSTEM_PROMPT
            )
            
            result = {
                'success': True,
                'is_emergency': is_emergency,
                'has_danger_symptoms': has_danger_symptoms,
                'vital_signs': vital_signs,
                'symptoms': symptoms,
                'response': emergency_response,
                'sources': [hit.get('source') for hit in rag_results.get('pdf_results', [])[:3]],
                'requires_referral': is_emergency and has_danger_symptoms,
                'referral_department': '急诊科' if is_emergency else None
            }
            
            if is_emergency:
                result['immediate_actions'] = [
                    '1. 保持患者安静，取半卧位',
                    '2. 立即建立静脉通路',
                    '3. 给予静脉降压药物（遵医嘱）',
                    '4. 目标：1小时内降压不超过25%',
                    '5. 紧急转诊至急诊科'
                ]
            
            logger.info(f"紧急情况处理完成，是否急症: {is_emergency}")
            return result
            
        except Exception as e:
            logger.error(f"紧急情况处理失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# 全局诊疗智能体实例
_diagnosis_agent = None

def get_diagnosis_agent() -> DiagnosisAgent:
    """获取全局诊疗智能体实例"""
    global _diagnosis_agent
    if _diagnosis_agent is None:
        _diagnosis_agent = DiagnosisAgent()
    return _diagnosis_agent

