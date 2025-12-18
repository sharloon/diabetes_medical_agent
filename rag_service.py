"""
RAG服务模块 - 跨源检索与答案生成
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from loguru import logger

from vector_store import get_vector_store
from db_service import get_db_service
from term_mapper import get_term_mapper
from data_ingest import load_all_pdfs, ExcelProcessor
from llm_client import get_llm_client, MEDICAL_SYSTEM_PROMPT
from config import DATA_DIR
import os


class RAGService:
    """RAG检索服务 - 整合PDF、Excel、MySQL多源数据"""
    
    def __init__(self):
        self.vector_store = get_vector_store()
        self.db_service = get_db_service()
        self.term_mapper = get_term_mapper()
        self.llm_client = get_llm_client()
        logger.info("RAG服务初始化完成")
    
    def search_all_sources(self, query: str, top_k: int = 5, 
                           include_pdf: bool = True,
                           include_excel: bool = True,
                           include_mysql: bool = True,
                           date_filter: str = None) -> Dict:
        """
        跨源统一检索
        
        Args:
            query: 检索查询
            top_k: 每个来源返回的最大结果数
            include_pdf: 是否包含PDF结果
            include_excel: 是否包含Excel结果
            include_mysql: 是否包含MySQL结果
            date_filter: 日期过滤（用于指南时效性验证）
            
        Returns:
            Dict: 包含各来源结果的字典
        """
        logger.info(f"开始跨源检索，查询: '{query}', 日期过滤: {date_filter}")
        
        # 术语标准化和查询扩展
        normalized_query, replacements = self.term_mapper.normalize_text(query)
        expanded_query = self.term_mapper.expand_query(normalized_query)
        
        results = {
            'original_query': query,
            'normalized_query': normalized_query,
            'term_replacements': replacements,
            'pdf_results': [],
            'excel_results': [],
            'mysql_results': [],
            'total_count': 0
        }
        
        # 1. PDF/向量库检索
        if include_pdf:
            try:
                pdf_hits = self.vector_store.search(expanded_query, top_k=top_k)
                results['pdf_results'] = pdf_hits
                logger.info(f"PDF检索完成，命中{len(pdf_hits)}条")
            except Exception as e:
                logger.error(f"PDF检索失败: {e}")
        
        # 2. Excel数据检索
        if include_excel:
            try:
                excel_hits = self._search_excel(query, top_k)
                results['excel_results'] = excel_hits
                logger.info(f"Excel检索完成，命中{len(excel_hits)}条")
            except Exception as e:
                logger.error(f"Excel检索失败: {e}")
        
        # 3. MySQL数据检索
        if include_mysql:
            try:
                mysql_hits = self._search_mysql(query, date_filter, top_k)
                results['mysql_results'] = mysql_hits
                logger.info(f"MySQL检索完成，命中{len(mysql_hits)}条")
            except Exception as e:
                logger.error(f"MySQL检索失败: {e}")
        
        results['total_count'] = (len(results['pdf_results']) + 
                                   len(results['excel_results']) + 
                                   len(results['mysql_results']))
        
        return results
    
    def _search_excel(self, query: str, top_k: int) -> List[Dict]:
        """Excel数据检索"""
        hits = []
        query_lower = query.lower()
        
        # 加载Excel数据
        excel_files = [f for f in os.listdir(DATA_DIR) if f.endswith('.xlsx')]
        
        for excel_file in excel_files:
            excel_path = os.path.join(DATA_DIR, excel_file)
            processor = ExcelProcessor(excel_path)
            df = processor.load_data()
            
            if df is None or df.empty:
                continue
            
            # 简单关键词匹配检索
            for idx, row in df.iterrows():
                row_text = " ".join([str(val) for val in row.values if val is not None])
                if any(keyword in row_text.lower() for keyword in query_lower.split()):
                    hits.append({
                        'content': row_text[:500],  # 限制长度
                        'source': {
                            'type': 'excel',
                            'filename': excel_file,
                            'row': idx + 2
                        },
                        'score': 0.7
                    })
                    
                    if len(hits) >= top_k:
                        break
        
        return hits[:top_k]
    
    def _search_mysql(self, query: str, date_filter: str, top_k: int) -> List[Dict]:
        """MySQL数据检索"""
        hits = []
        
        try:
            # 检索指南推荐规则
            guidelines = self.db_service.get_guideline_recommendations(
                update_date_after=date_filter
            )
            
            for guideline in guidelines:
                # 简单关键词匹配
                content = f"{guideline.get('guideline_name', '')} {guideline.get('recommendation_content', '')}"
                if any(keyword in content for keyword in query.split()):
                    hits.append({
                        'content': f"[{guideline.get('guideline_name')}] {guideline.get('recommendation_content')}",
                        'source': {
                            'type': 'mysql',
                            'table': 'guideline_recommendations',
                            'rule_id': guideline.get('rule_id'),
                            'update_date': str(guideline.get('update_date'))
                        },
                        'evidence_level': guideline.get('recommendation_level'),
                        'score': 0.8
                    })
            
            # 如果查询包含"高血压"相关词汇，检索高血压风险评估数据
            if '高血压' in query or '血压' in query:
                risk_data = self.db_service.get_hypertension_risk_table()
                for record in risk_data[:top_k]:
                    hits.append({
                        'content': f"患者{record.get('patient_id')}高血压评估: 血压{record.get('sbp')}/{record.get('dbp')}mmHg, "
                                  f"风险等级:{record.get('risk_level')}, 危险因素:{record.get('risk_factors')}",
                        'source': {
                            'type': 'mysql',
                            'table': 'hypertension_risk_assessment',
                            'patient_id': record.get('patient_id')
                        },
                        'score': 0.6
                    })
                    
        except Exception as e:
            logger.error(f"MySQL检索异常: {e}")
        
        return hits[:top_k]
    
    def generate_answer(self, query: str, context: Dict = None, 
                        patient_context: str = None) -> Dict:
        """
        基于检索结果生成回答
        
        Args:
            query: 用户问题
            context: 检索结果上下文
            patient_context: 患者上下文信息
            
        Returns:
            Dict: 包含答案和来源引用的结果
        """
        # 如果没有提供上下文，先进行检索
        if context is None:
            context = self.search_all_sources(query)
        
        # 检查是否有检索结果
        if context['total_count'] == 0:
            # 检查是否是医疗相关问题
            medical_keywords = ['高血压', '糖尿病', '血糖', '血压', '心脏', '用药', 
                               '治疗', '诊断', '症状', '检查', '药物', '指南']
            is_medical = any(keyword in query for keyword in medical_keywords)
            
            if not is_medical:
                return {
                    'answer': "抱歉，您的问题超出了我的专业范围。我是糖尿病和高血压医疗诊断助手，"
                             "主要提供高血压、糖尿病相关的诊疗建议。请问您有这方面的问题吗？",
                    'sources': [],
                    'has_knowledge': False
                }
            else:
                return {
                    'answer': "抱歉，我暂时无法在知识库中找到与您问题相关的信息。"
                             "建议您咨询专业医生获取更准确的诊疗建议。",
                    'sources': [],
                    'has_knowledge': False
                }
        
        # 构建上下文文本
        context_parts = []
        sources = []
        
        # PDF结果
        for hit in context.get('pdf_results', []):
            context_parts.append(f"【PDF文档】{hit.get('source', {}).get('filename', '')}"
                                f"第{hit.get('source', {}).get('page', '')}页:\n{hit['content']}")
            sources.append(hit['source'])
        
        # Excel结果
        for hit in context.get('excel_results', []):
            context_parts.append(f"【Excel数据】{hit.get('source', {}).get('filename', '')}"
                                f"第{hit.get('source', {}).get('row', '')}行:\n{hit['content']}")
            sources.append(hit['source'])
        
        # MySQL结果
        for hit in context.get('mysql_results', []):
            evidence = f"(证据等级:{hit.get('evidence_level', 'N/A')})" if hit.get('evidence_level') else ""
            context_parts.append(f"【数据库】{hit.get('source', {}).get('table', '')}{evidence}:\n{hit['content']}")
            sources.append(hit['source'])
        
        context_text = "\n\n".join(context_parts)
        
        # 如果有患者上下文，加入到提示词中
        if patient_context:
            context_text = f"【患者信息】\n{patient_context}\n\n{context_text}"
        
        # 构建提示词
        prompt = f"""基于以下参考信息回答用户问题。请遵循以下要求：
1. 回答必须基于提供的参考信息，不要凭空编造
2. 对于治疗建议，请标注证据等级（如有）
3. 如果信息不足以完整回答，请明确说明
4. 涉及高风险情况时，需要特别提醒

参考信息：
{context_text}

用户问题：{query}

请给出专业、准确的回答："""
        
        # 调用LLM生成回答
        answer = self.llm_client.generate(
            prompt=prompt,
            system_prompt=MEDICAL_SYSTEM_PROMPT
        )
        
        return {
            'answer': answer,
            'sources': sources,
            'has_knowledge': True,
            'term_replacements': context.get('term_replacements', [])
        }
    
    def chat(self, query: str, history: List[Dict] = None,
             patient_id: str = None) -> Dict:
        """
        智能对话接口
        
        Args:
            query: 用户问题
            history: 对话历史
            patient_id: 患者ID（可选）
            
        Returns:
            Dict: 对话结果
        """
        logger.info(f"开始对话，问题: '{query}', 患者ID: {patient_id}")
        
        # 获取患者上下文
        patient_context = None
        if patient_id:
            try:
                profile = self.db_service.get_patient_full_profile(patient_id)
                if profile:
                    from utils import format_patient_profile
                    patient_context = format_patient_profile(profile)
            except Exception as e:
                logger.error(f"获取患者信息失败: {e}")
        
        # 检索并生成回答
        search_results = self.search_all_sources(query)
        result = self.generate_answer(query, search_results, patient_context)
        
        # 添加术语映射信息
        if search_results.get('term_replacements'):
            result['term_info'] = f"术语标准化: {', '.join([f'{r['original']}→{r['normalized']}' for r in search_results['term_replacements']])}"
        
        return result
    
    def validate_guideline_timeliness(self, update_date_after: str) -> List[Dict]:
        """
        验证指南文档时效性
        
        Args:
            update_date_after: 日期阈值（YYYY-MM-DD格式）
            
        Returns:
            List[Dict]: 符合条件的指南列表
        """
        try:
            guidelines = self.db_service.get_guideline_recommendations(
                update_date_after=update_date_after
            )
            
            logger.info(f"指南时效性验证完成，{update_date_after}之后更新的指南数: {len(guidelines)}")
            return guidelines
            
        except Exception as e:
            logger.error(f"指南时效性验证失败: {e}")
            return []


# 全局RAG服务实例
_rag_service = None

def get_rag_service() -> RAGService:
    """获取全局RAG服务实例"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service

