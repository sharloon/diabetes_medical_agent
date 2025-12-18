"""
Flask Web应用 - 糖尿病智能诊断助手
"""
import os
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from loguru import logger

from config import LOG_DIR
from utils import setup_logger
from llm_client import get_llm_client
from db_service import get_db_service, DatabaseConnectionError, set_simulate_db_failure, get_simulate_db_failure
from rag_service import get_rag_service
from vector_store import get_vector_store, init_vector_store
from term_mapper import get_term_mapper
from risk_engine import get_risk_engine
from safety_guard import get_safety_guard
from diagnosis_agent import get_diagnosis_agent
from data_ingest import (
    PDFProcessor, ExcelProcessor, get_pdf_info, get_excel_info, 
    load_all_pdfs, load_excel_data, DATA_DIR
)
from scheduler import get_scheduler, start_scheduler

# 初始化Flask应用
app = Flask(__name__, 
           template_folder='templates',
           static_folder='static')
CORS(app)

# 设置日志
setup_logger()

# ============ 首页 ============
@app.route('/')
def index():
    """首页 - 功能菜单"""
    return render_template('index.html')

# ============ PDF知识库构建 ============
@app.route('/pdf_knowledge')
def pdf_knowledge():
    """PDF知识库页面"""
    return render_template('pdf_knowledge.html')

@app.route('/api/pdf/info')
def api_pdf_info():
    """获取PDF文档信息"""
    try:
        pdf_info = get_pdf_info()
        return jsonify({'success': True, 'data': pdf_info})
    except Exception as e:
        logger.error(f"获取PDF信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/pdf/extract/<filename>')
def api_pdf_extract(filename):
    """提取PDF文档内容"""
    try:
        pdf_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(pdf_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        processor = PDFProcessor(pdf_path)
        info = processor.get_document_info()
        toc = processor.extract_toc()
        tables = processor.extract_tables()
        
        return jsonify({
            'success': True,
            'data': {
                'info': info,
                'toc': toc,
                'tables': [{'content': t['content'][:1000], 'source': t['source']} for t in tables[:10]]
            }
        })
    except Exception as e:
        logger.error(f"提取PDF内容失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 术语映射 ============
@app.route('/term_mapping')
def term_mapping():
    """术语映射页面"""
    return render_template('term_mapping.html')

@app.route('/api/term/mappings')
def api_term_mappings():
    """获取所有术语映射"""
    try:
        mapper = get_term_mapper()
        mappings = mapper.get_mapping_table()
        return jsonify({'success': True, 'data': mappings})
    except Exception as e:
        logger.error(f"获取术语映射失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/term/normalize', methods=['POST'])
def api_term_normalize():
    """术语标准化"""
    try:
        data = request.json
        term = data.get('term', '')
        
        mapper = get_term_mapper()
        normalized = mapper.normalize(term)
        suggestions = mapper.suggest(term)
        
        return jsonify({
            'success': True,
            'data': {
                'original': term,
                'normalized': normalized,
                'suggestions': suggestions
            }
        })
    except Exception as e:
        logger.error(f"术语标准化失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ Excel数据处理 ============
@app.route('/excel_analysis')
def excel_analysis():
    """Excel数据分析页面"""
    return render_template('excel_analysis.html')

@app.route('/api/excel/info')
def api_excel_info():
    """获取Excel文件信息"""
    try:
        excel_info = get_excel_info()
        return jsonify({'success': True, 'data': excel_info})
    except Exception as e:
        logger.error(f"获取Excel信息失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/excel/stats')
def api_excel_stats():
    """获取Excel统计数据"""
    try:
        df, stats = load_excel_data()
        
        # 准备可视化数据
        vis_data = {}
        for filename, file_stats in stats.items():
            # 转换insulin_stats中的numpy类型为Python原生类型
            raw_insulin = file_stats.get('insulin_stats', {})
            insulin_stats = {
                'total_patients': int(raw_insulin.get('total_patients', 0)),
                'insulin_users': int(raw_insulin.get('insulin_users', 0)),
                'insulin_non_users': int(raw_insulin.get('insulin_non_users', 0)),
                'usage_rate': float(raw_insulin.get('usage_rate', 0.0))
            }
            
            vis_data[filename] = {
                'insulin_stats': insulin_stats,
                'gender_distribution': {str(k): int(v) for k, v in file_stats.get('gender_distribution', {}).items()},
                'age_distribution': {str(k): int(v) for k, v in file_stats.get('age_distribution', {}).items()},
                'bmi_distribution': {str(k): int(v) for k, v in file_stats.get('bmi_distribution', {}).items()}
            }
        
        return jsonify({'success': True, 'data': vis_data})
    except Exception as e:
        logger.error(f"获取Excel统计失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 多模态数据整合 ============
@app.route('/multimodal_search')
def multimodal_search():
    """多模态数据整合搜索页面"""
    return render_template('multimodal_search.html')

@app.route('/api/search', methods=['POST'])
def api_search():
    """跨源统一检索"""
    try:
        data = request.json
        query = data.get('query', '')
        date_filter = data.get('date_filter')
        
        rag_service = get_rag_service()
        results = rag_service.search_all_sources(
            query=query,
            date_filter=date_filter
        )
        
        return jsonify({'success': True, 'data': results})
    except Exception as e:
        logger.error(f"检索失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/guidelines/timeliness', methods=['POST'])
def api_guidelines_timeliness():
    """指南时效性验证"""
    try:
        data = request.json
        date_after = data.get('date_after', '2025-07-20')
        
        rag_service = get_rag_service()
        guidelines = rag_service.validate_guideline_timeliness(date_after)
        
        return jsonify({'success': True, 'data': guidelines})
    except Exception as e:
        logger.error(f"指南时效性验证失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 智能对话 ============
@app.route('/chat')
def chat_page():
    """智能对话页面"""
    return render_template('chat.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """智能对话接口"""
    try:
        data = request.json
        query = data.get('query', '')
        patient_id = data.get('patient_id')
        history = data.get('history', [])
        
        if not query:
            return jsonify({'success': False, 'error': '问题不能为空'})
        
        rag_service = get_rag_service()
        result = rag_service.chat(query=query, patient_id=patient_id, history=history)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"对话失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 临床数据查询与分析 ============
@app.route('/clinical_analysis')
def clinical_analysis():
    """临床数据查询与分析页面"""
    return render_template('clinical_analysis.html')

@app.route('/api/patient/profile/<patient_id>')
def api_patient_profile(patient_id):
    """获取患者画像"""
    try:
        agent = get_diagnosis_agent()
        profile = agent.build_patient_profile(patient_id)
        return jsonify({'success': True, 'data': profile})
    except DatabaseConnectionError as e:
        logger.error(f"获取患者画像失败 - 数据库连接异常: {e.message}")
        return jsonify({
            'success': False, 
            'error': e.message,
            'error_type': 'database_connection',
            'degraded': True,
            'fallback_message': '⚠️ 数据库连接失败\n\n'
                               '无法获取患者数据，系统已自动进入降级模式。\n\n'
                               '【可用功能】\n'
                               '• 基于知识库的医学问答\n'
                               '• PDF指南检索\n'
                               '• Excel统计分析\n\n'
                               '【不可用功能】\n'
                               '• 患者信息查询\n'
                               '• 临床数据分析\n'
                               '• 个性化诊疗决策\n\n'
                               '请联系管理员恢复数据库服务。',
            'available_features': ['pdf_search', 'excel_analysis', 'term_mapping', 'knowledge_chat'],
            'unavailable_features': ['patient_query', 'clinical_analysis', 'personalized_diagnosis']
        })
    except Exception as e:
        logger.error(f"获取患者画像失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patient/risk/<patient_id>')
def api_patient_risk(patient_id):
    """风险分层评估"""
    try:
        agent = get_diagnosis_agent()
        result = agent.assess_risk(patient_id)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"风险评估失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patient/drug-check/<patient_id>')
def api_drug_check(patient_id):
    """用药冲突检测"""
    try:
        agent = get_diagnosis_agent()
        result = agent.check_drug_conflicts(patient_id)
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"用药冲突检测失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/patients')
def api_patients():
    """获取患者列表"""
    try:
        db_service = get_db_service()
        patients = db_service.search_patients(limit=100)
        return jsonify({'success': True, 'data': patients})
    except DatabaseConnectionError as e:
        logger.error(f"获取患者列表失败 - 数据库连接异常: {e.message}")
        return jsonify({
            'success': False, 
            'error': e.message,
            'error_type': 'database_connection',
            'degraded': True,
            'fallback_message': '数据库服务暂时不可用，系统已进入降级模式。您可以使用以下功能：\n'
                               '• PDF知识库检索\n'
                               '• Excel数据分析\n'
                               '• 术语映射查询\n'
                               '• 智能对话（基于知识库）\n\n'
                               '请联系系统管理员检查数据库连接。'
        })
    except Exception as e:
        logger.error(f"获取患者列表失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 个性化诊疗决策 ============
@app.route('/diagnosis_decision')
def diagnosis_decision():
    """个性化诊疗决策页面"""
    return render_template('diagnosis_decision.html')

@app.route('/api/diagnosis/generate', methods=['POST'])
def api_diagnosis_generate():
    """生成诊断"""
    try:
        data = request.json
        symptoms = data.get('symptoms', '')
        exam_data = data.get('exam_data', {})
        patient_id = data.get('patient_id')
        
        agent = get_diagnosis_agent()
        result = agent.generate_diagnosis(
            symptoms=symptoms,
            exam_data=exam_data,
            patient_id=patient_id
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"诊断生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/treatment/generate', methods=['POST'])
def api_treatment_generate():
    """生成治疗方案"""
    try:
        data = request.json
        patient_id = data.get('patient_id')
        diagnosis = data.get('diagnosis')
        custom_profile = data.get('custom_profile')
        
        agent = get_diagnosis_agent()
        result = agent.generate_treatment_plan(
            patient_id=patient_id,
            diagnosis=diagnosis,
            custom_profile=custom_profile
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"治疗方案生成失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/treatment/adjust', methods=['POST'])
def api_treatment_adjust():
    """调整治疗方案"""
    try:
        data = request.json
        patient_id = data.get('patient_id')
        current_plan = data.get('current_plan', '')
        treatment_response = data.get('treatment_response', '')
        duration = data.get('duration', '2周')
        
        agent = get_diagnosis_agent()
        result = agent.adjust_treatment(
            patient_id=patient_id,
            current_plan=current_plan,
            treatment_response=treatment_response,
            duration=duration
        )
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"治疗方案调整失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 循证医学支持 ============
@app.route('/evidence_support')
def evidence_support():
    """循证医学支持页面"""
    return render_template('evidence_support.html')

@app.route('/api/evidence/search', methods=['POST'])
def api_evidence_search():
    """循证医学检索"""
    try:
        data = request.json
        query = data.get('query', '')
        
        rag_service = get_rag_service()
        results = rag_service.search_all_sources(query)
        
        # 生成综合建议
        answer = rag_service.generate_answer(query, results)
        
        return jsonify({
            'success': True, 
            'data': {
                'search_results': results,
                'answer': answer
            }
        })
    except Exception as e:
        logger.error(f"循证检索失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 伦理安全控制 ============
@app.route('/safety_control')
def safety_control():
    """伦理安全控制页面"""
    return render_template('safety_control.html')

@app.route('/api/safety/check', methods=['POST'])
def api_safety_check():
    """安全检查"""
    try:
        data = request.json
        patient_id = data.get('patient_id')
        custom_profile = data.get('custom_profile')
        
        if patient_id:
            db_service = get_db_service()
            profile = db_service.get_patient_full_profile(patient_id)
        elif custom_profile:
            profile = custom_profile
        else:
            return jsonify({'success': False, 'error': '请提供患者信息'})
        
        if not profile:
            return jsonify({'success': False, 'error': '未找到患者'})
        
        safety_guard = get_safety_guard()
        result = safety_guard.check_all(profile)
        report = safety_guard.generate_safety_report(profile)
        
        return jsonify({
            'success': True,
            'data': {
                'check_result': result,
                'report': report
            }
        })
    except DatabaseConnectionError as e:
        logger.error(f"安全检查失败 - 数据库连接异常: {e.message}")
        return jsonify({
            'success': False, 
            'error': e.message,
            'error_type': 'database_connection',
            'degraded': True,
            'fallback_message': '⚠️ 数据库连接失败，安全检查功能暂时不可用\n\n'
                               '【重要提示】\n'
                               '在数据库恢复之前，请人工核查以下安全要点：\n'
                               '• 孕妇禁用ACEI/ARB类药物\n'
                               '• 高血压急症(SBP≥180)需立即转诊\n'
                               '• 注意药物相互作用\n'
                               '• 老年患者需要调整剂量\n\n'
                               '如需紧急安全评估，请联系值班医师。'
        })
    except Exception as e:
        logger.error(f"安全检查失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emergency/process', methods=['POST'])
def api_emergency_process():
    """紧急情况处理"""
    try:
        data = request.json
        symptoms = data.get('symptoms', '')
        vital_signs = data.get('vital_signs', {})
        
        agent = get_diagnosis_agent()
        result = agent.process_emergency(symptoms, vital_signs)
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"紧急情况处理失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 智能体对话管理 ============
@app.route('/soap_consultation')
def soap_consultation():
    """SOAP问诊页面"""
    return render_template('soap_consultation.html')

@app.route('/api/soap/consult', methods=['POST'])
def api_soap_consult():
    """SOAP问诊"""
    try:
        data = request.json
        chief_complaint = data.get('chief_complaint', '')
        patient_id = data.get('patient_id')
        history = data.get('history', [])
        
        agent = get_diagnosis_agent()
        result = agent.soap_consultation(
            chief_complaint=chief_complaint,
            patient_id=patient_id,
            conversation_history=history
        )
        
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        logger.error(f"SOAP问诊失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 系统运维 ============
@app.route('/system_admin')
def system_admin():
    """系统运维页面"""
    return render_template('system_admin.html')

@app.route('/api/system/status')
def api_system_status():
    """获取系统状态"""
    try:
        scheduler = get_scheduler()
        vector_store = get_vector_store()
        db_service = get_db_service()
        
        # 检查数据库连接（考虑模拟模式）
        db_connected = False
        db_error = None
        try:
            if not get_simulate_db_failure():
                db_connected = db_service.test_connection()
            else:
                db_error = "数据库连接失败模拟已开启"
        except DatabaseConnectionError as e:
            db_error = str(e.message)
        except Exception as e:
            db_error = str(e)
        
        return jsonify({
            'success': True,
            'data': {
                'scheduler': scheduler.get_status(),
                'vector_store': vector_store.get_index_info(),
                'database': {
                    'connected': db_connected,
                    'simulate_failure': get_simulate_db_failure(),
                    'error': db_error
                }
            }
        })
    except Exception as e:
        logger.error(f"获取系统状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/simulate-db-failure', methods=['POST'])
def api_simulate_db_failure():
    """模拟数据库连接失败开关"""
    try:
        data = request.json
        enabled = data.get('enabled', False)
        
        set_simulate_db_failure(enabled)
        
        return jsonify({
            'success': True,
            'data': {
                'simulate_failure': enabled,
                'message': f"数据库连接失败模拟已{'开启' if enabled else '关闭'}"
            }
        })
    except Exception as e:
        logger.error(f"设置模拟状态失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/db-failure-status')
def api_db_failure_status():
    """获取数据库连接失败模拟状态"""
    return jsonify({
        'success': True,
        'data': {
            'simulate_failure': get_simulate_db_failure()
        }
    })

@app.route('/api/system/rebuild-index', methods=['POST'])
def api_rebuild_index():
    """手动重建索引"""
    try:
        scheduler = get_scheduler()
        scheduler.trigger_update()
        return jsonify({'success': True, 'message': '索引重建任务已触发'})
    except Exception as e:
        logger.error(f"触发索引重建失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/system/logs')
def api_system_logs():
    """获取系统日志"""
    try:
        log_file = os.path.join(LOG_DIR, 'medical_agent.log')
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                # 读取最后100行
                lines = f.readlines()[-100:]
                return jsonify({'success': True, 'data': ''.join(lines)})
        return jsonify({'success': True, 'data': '暂无日志'})
    except Exception as e:
        logger.error(f"获取日志失败: {e}")
        return jsonify({'success': False, 'error': str(e)})

# ============ 决策溯源与可视化 ============
@app.route('/decision_trace')
def decision_trace():
    """决策溯源页面"""
    return render_template('decision_trace.html')

# ============ 健康检查 ============
@app.route('/health')
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })

# ============ 错误处理 ============
@app.errorhandler(404)
def not_found(e):
    return jsonify({'success': False, 'error': '接口不存在'}), 404

@app.errorhandler(500)
def server_error(e):
    logger.error(f"服务器错误: {e}")
    return jsonify({'success': False, 'error': '服务器内部错误'}), 500


def init_app():
    """初始化应用"""
    logger.info("=" * 50)
    logger.info("糖尿病智能诊断助手启动中...")
    logger.info("=" * 50)
    
    # 创建必要的目录
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    # 测试数据库连接
    try:
        db_service = get_db_service()
        if db_service.test_connection():
            logger.info("✓ 数据库连接成功")
        else:
            logger.warning("✗ 数据库连接失败")
    except Exception as e:
        logger.error(f"✗ 数据库初始化失败: {e}")
    
    # 初始化向量存储
    try:
        init_vector_store()
        logger.info("✓ 向量存储初始化完成")
    except Exception as e:
        logger.warning(f"向量存储初始化警告: {e}")
    
    # 启动定时任务
    try:
        start_scheduler()
        logger.info("✓ 定时任务调度器启动")
    except Exception as e:
        logger.warning(f"定时任务启动警告: {e}")
    
    logger.info("=" * 50)
    logger.info("应用初始化完成!")
    logger.info("=" * 50)


if __name__ == '__main__':
    init_app()
    app.run(host='0.0.0.0', port=5000, debug=True)

