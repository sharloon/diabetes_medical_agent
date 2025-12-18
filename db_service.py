"""
MySQL数据库服务模块
"""
import pymysql
from pymysql.cursors import DictCursor
from typing import List, Dict, Optional, Any
from contextlib import contextmanager
from loguru import logger
import time

from config import MYSQL_CONFIG


# 全局模拟开关
_simulate_db_failure = False


def set_simulate_db_failure(enabled: bool):
    """设置是否模拟数据库连接失败"""
    global _simulate_db_failure
    _simulate_db_failure = enabled
    logger.warning(f"数据库连接失败模拟已{'开启' if enabled else '关闭'}")


def get_simulate_db_failure() -> bool:
    """获取数据库连接失败模拟状态"""
    return _simulate_db_failure


class DatabaseConnectionError(Exception):
    """数据库连接异常"""
    def __init__(self, message: str = "数据库连接失败", original_error: Exception = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class DatabaseService:
    """MySQL数据库服务"""
    
    def __init__(self, config: dict = None):
        self.config = config or MYSQL_CONFIG
        self._connection = None
        logger.info(f"数据库服务初始化，连接到: {self.config['host']}:{self.config['port']}")
    
    @contextmanager
    def get_connection(self):
        """获取数据库连接（上下文管理器）"""
        # 检查是否模拟数据库连接失败
        if _simulate_db_failure:
            logger.error("【模拟】数据库连接失败 - 模拟模式已开启")
            raise DatabaseConnectionError(
                message="数据库连接失败：无法连接到MySQL服务器 (模拟模式)",
                original_error=Exception("Connection refused - simulated failure")
            )
        
        connection = None
        try:
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=DictCursor
            )
            yield connection
        except pymysql.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise DatabaseConnectionError(
                message=f"数据库连接失败：{str(e)}",
                original_error=e
            )
        finally:
            if connection:
                connection.close()
    
    def execute_query(self, sql: str, params: tuple = None) -> List[Dict]:
        """执行查询SQL"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"SQL查询执行成功，耗时: {execution_time}ms, SQL: {sql[:200]}...")
            return results
            
        except DatabaseConnectionError:
            # 重新抛出连接错误，让上层处理
            raise
        except pymysql.Error as e:
            logger.error(f"SQL查询失败: {e}, SQL: {sql}")
            raise
    
    def execute_update(self, sql: str, params: tuple = None) -> int:
        """执行更新SQL，返回影响行数"""
        start_time = time.time()
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    affected_rows = cursor.execute(sql, params)
                    conn.commit()
                    
            execution_time = int((time.time() - start_time) * 1000)
            logger.info(f"SQL更新执行成功，影响行数: {affected_rows}, 耗时: {execution_time}ms")
            return affected_rows
            
        except pymysql.Error as e:
            logger.error(f"SQL更新失败: {e}, SQL: {sql}")
            raise
    
    def get_patient_info(self, patient_id: str) -> Optional[Dict]:
        """获取患者基本信息"""
        sql = """
        SELECT patient_id, name, gender, age, height_cm, weight_kg, bmi, phone, address, 
               create_time, update_time
        FROM patient_info 
        WHERE patient_id = %s
        """
        results = self.execute_query(sql, (patient_id,))
        return results[0] if results else None
    
    def get_patient_diagnoses(self, patient_id: str) -> List[Dict]:
        """获取患者诊断记录"""
        sql = """
        SELECT diag_id, diagnosis_date, diagnosis_code, diagnosis_name, 
               diagnosis_type, severity_level, icd10_code
        FROM diagnosis_records 
        WHERE patient_id = %s
        ORDER BY diagnosis_date DESC
        """
        return self.execute_query(sql, (patient_id,))
    
    def get_patient_medications(self, patient_id: str) -> List[Dict]:
        """获取患者用药记录"""
        sql = """
        SELECT med_id, medication_date, drug_name, drug_class, dosage, 
               frequency, duration, prescribing_doctor, is_insulin
        FROM medication_records 
        WHERE patient_id = %s
        ORDER BY medication_date DESC
        """
        return self.execute_query(sql, (patient_id,))
    
    def get_patient_lab_results(self, patient_id: str) -> List[Dict]:
        """获取患者检验结果"""
        sql = """
        SELECT result_id, test_date, test_type, test_item, result_value, 
               unit, reference_range, is_abnormal, test_notes
        FROM lab_results 
        WHERE patient_id = %s
        ORDER BY test_date DESC
        """
        return self.execute_query(sql, (patient_id,))
    
    def get_hypertension_assessment(self, patient_id: str) -> Optional[Dict]:
        """获取高血压风险评估"""
        sql = """
        SELECT assessment_id, assessment_date, sbp, dbp, heart_rate,
               risk_factors, target_organs_damage, clinical_conditions,
               risk_level, follow_up_plan
        FROM hypertension_risk_assessment 
        WHERE patient_id = %s
        ORDER BY assessment_date DESC
        LIMIT 1
        """
        results = self.execute_query(sql, (patient_id,))
        return results[0] if results else None
    
    def get_diabetes_assessment(self, patient_id: str) -> Optional[Dict]:
        """获取糖尿病控制评估"""
        sql = """
        SELECT assessment_id, assessment_date, fasting_glucose, postprandial_glucose,
               hba1c, insulin_usage, insulin_type, insulin_dosage, 
               control_status, complications
        FROM diabetes_control_assessment 
        WHERE patient_id = %s
        ORDER BY assessment_date DESC
        LIMIT 1
        """
        results = self.execute_query(sql, (patient_id,))
        return results[0] if results else None
    
    def get_patient_full_profile(self, patient_id: str) -> Optional[Dict]:
        """获取患者完整档案"""
        logger.info(f"获取患者完整档案，patient_id: {patient_id}")
        
        patient_info = self.get_patient_info(patient_id)
        if not patient_info:
            logger.warning(f"未找到患者: {patient_id}")
            return None
        
        profile = {
            **patient_info,
            'diagnoses': self.get_patient_diagnoses(patient_id),
            'medications': self.get_patient_medications(patient_id),
            'lab_results': self.get_patient_lab_results(patient_id),
            'hypertension_assessment': self.get_hypertension_assessment(patient_id),
            'diabetes_assessment': self.get_diabetes_assessment(patient_id)
        }
        
        logger.info(f"患者档案获取成功，包含 {len(profile.get('diagnoses', []))} 条诊断, "
                   f"{len(profile.get('medications', []))} 条用药记录")
        
        return profile
    
    def get_guideline_recommendations(self, disease_type: str = None, 
                                      update_date_after: str = None) -> List[Dict]:
        """获取指南推荐规则"""
        sql = """
        SELECT rule_id, guideline_name, disease_type, patient_condition,
               recommendation_level, recommendation_content, evidence_source, update_date
        FROM guideline_recommendations
        WHERE is_active = TRUE
        """
        params = []
        
        if disease_type:
            sql += " AND disease_type = %s"
            params.append(disease_type)
        
        if update_date_after:
            sql += " AND update_date >= %s"
            params.append(update_date_after)
        
        sql += " ORDER BY update_date DESC"
        
        return self.execute_query(sql, tuple(params) if params else None)
    
    def get_hypertension_risk_table(self) -> List[Dict]:
        """获取高血压风险评估表"""
        sql = """
        SELECT assessment_id, patient_id, assessment_date, sbp, dbp, 
               risk_factors, risk_level, follow_up_plan
        FROM hypertension_risk_assessment
        ORDER BY assessment_date DESC
        """
        return self.execute_query(sql)
    
    def search_patients(self, keyword: str = None, risk_level: str = None, 
                       limit: int = 50) -> List[Dict]:
        """搜索患者"""
        sql = """
        SELECT DISTINCT p.patient_id, p.name, p.gender, p.age, p.bmi,
               h.sbp, h.dbp, h.risk_level as hypertension_risk,
               d.hba1c, d.control_status as diabetes_status
        FROM patient_info p
        LEFT JOIN hypertension_risk_assessment h ON p.patient_id = h.patient_id
        LEFT JOIN diabetes_control_assessment d ON p.patient_id = d.patient_id
        WHERE 1=1
        """
        params = []
        
        if keyword:
            sql += " AND (p.name LIKE %s OR p.patient_id LIKE %s)"
            params.extend([f"%{keyword}%", f"%{keyword}%"])
        
        if risk_level:
            sql += " AND h.risk_level = %s"
            params.append(risk_level)
        
        sql += f" LIMIT {limit}"
        
        return self.execute_query(sql, tuple(params) if params else None)
    
    def get_all_patient_ids(self) -> List[str]:
        """获取所有患者ID"""
        sql = "SELECT patient_id FROM patient_info"
        results = self.execute_query(sql)
        return [r['patient_id'] for r in results]
    
    def log_operation(self, operation_type: str, operation_details: str,
                      patient_id: str = None, execution_time_ms: int = None,
                      status: str = '成功'):
        """记录系统日志"""
        sql = """
        INSERT INTO system_logs (operation_type, operation_details, patient_id, 
                                execution_time_ms, status)
        VALUES (%s, %s, %s, %s, %s)
        """
        try:
            self.execute_update(sql, (operation_type, operation_details, patient_id, 
                                      execution_time_ms, status))
        except Exception as e:
            logger.error(f"记录系统日志失败: {e}")
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False


# 全局数据库服务实例
_db_service = None

def get_db_service() -> DatabaseService:
    """获取全局数据库服务实例"""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service

