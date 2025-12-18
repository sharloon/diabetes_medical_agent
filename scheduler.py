"""
定时任务调度模块 - 自动更新RAG索引
"""
import os
import threading
from datetime import datetime
from typing import Callable, Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

from config import RAG_CONFIG, DATA_DIR, KNOWLEDGE_BASE_DIR
from vector_store import get_vector_store
from data_ingest import load_all_pdfs


class IndexScheduler:
    """索引更新调度器"""
    
    def __init__(self, interval_seconds: int = None):
        self.interval = interval_seconds or RAG_CONFIG.get('index_update_interval', 120)
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.last_update_time = None
        self.update_count = 0
        self._lock = threading.Lock()
        
        logger.info(f"索引调度器初始化，更新间隔: {self.interval}秒")
    
    def start(self):
        """启动调度器"""
        if self.is_running:
            logger.warning("调度器已在运行中")
            return
        
        try:
            # 添加定时任务
            self.scheduler.add_job(
                self._update_index_job,
                trigger=IntervalTrigger(seconds=self.interval),
                id='index_update_job',
                name='RAG索引自动更新',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            logger.info(f"索引调度器已启动，每{self.interval}秒更新一次")
            
            # 立即执行一次索引构建
            self._update_index_job()
            
        except Exception as e:
            logger.error(f"启动调度器失败: {e}")
    
    def stop(self):
        """停止调度器"""
        if not self.is_running:
            return
        
        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("索引调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}")
    
    def _update_index_job(self):
        """索引更新任务"""
        with self._lock:
            start_time = datetime.now()
            logger.info(f"开始执行索引更新任务，时间: {start_time.isoformat()}")
            
            try:
                # 检查是否有新文件
                new_files = self._check_for_updates()
                
                if new_files or self.update_count == 0:
                    # 重建索引
                    success = self._rebuild_index()
                    
                    if success:
                        self.last_update_time = datetime.now()
                        self.update_count += 1
                        
                        duration = (self.last_update_time - start_time).total_seconds()
                        logger.info(f"索引更新成功，耗时: {duration:.2f}秒，"
                                   f"累计更新次数: {self.update_count}")
                        
                        # 记录更新日志
                        self._log_update(success=True, duration=duration, 
                                        new_files=new_files)
                    else:
                        logger.error("索引更新失败")
                        self._log_update(success=False)
                else:
                    logger.info("未检测到新文件，跳过索引更新")
                    
            except Exception as e:
                logger.error(f"索引更新任务执行失败: {e}")
                self._log_update(success=False, error=str(e))
    
    def _check_for_updates(self) -> list:
        """检查是否有新文件需要索引"""
        new_files = []
        
        if not self.last_update_time:
            # 首次运行，所有文件都需要索引
            for f in os.listdir(DATA_DIR):
                if f.endswith(('.pdf', '.xlsx', '.xls')):
                    new_files.append(f)
            return new_files
        
        # 检查文件修改时间
        for f in os.listdir(DATA_DIR):
            if f.endswith(('.pdf', '.xlsx', '.xls')):
                file_path = os.path.join(DATA_DIR, f)
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime > self.last_update_time:
                    new_files.append(f)
                    logger.info(f"检测到更新文件: {f}")
        
        return new_files
    
    def _rebuild_index(self) -> bool:
        """重建向量索引"""
        try:
            vector_store = get_vector_store()
            
            # 加载所有PDF文档
            chunks = load_all_pdfs()
            
            if not chunks:
                logger.warning("没有找到可索引的文档")
                return False
            
            # 构建索引
            success = vector_store.build_index_from_chunks(chunks)
            
            return success
            
        except Exception as e:
            logger.error(f"重建索引失败: {e}")
            return False
    
    def _log_update(self, success: bool, duration: float = None, 
                    new_files: list = None, error: str = None):
        """记录更新日志"""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'success': success,
            'duration': duration,
            'new_files': new_files,
            'error': error,
            'update_count': self.update_count
        }
        
        log_file = os.path.join(KNOWLEDGE_BASE_DIR, 'update_log.txt')
        
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                status = "成功" if success else "失败"
                line = f"[{log_entry['timestamp']}] 索引更新{status}"
                if duration:
                    line += f", 耗时: {duration:.2f}秒"
                if new_files:
                    line += f", 新文件: {', '.join(new_files)}"
                if error:
                    line += f", 错误: {error}"
                f.write(line + "\n")
        except Exception as e:
            logger.error(f"写入更新日志失败: {e}")
    
    def get_status(self) -> dict:
        """获取调度器状态"""
        return {
            'is_running': self.is_running,
            'interval_seconds': self.interval,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'update_count': self.update_count,
            'next_run_time': self._get_next_run_time()
        }
    
    def _get_next_run_time(self) -> Optional[str]:
        """获取下次运行时间"""
        if not self.is_running:
            return None
        
        try:
            job = self.scheduler.get_job('index_update_job')
            if job and job.next_run_time:
                return job.next_run_time.isoformat()
        except:
            pass
        return None
    
    def trigger_update(self):
        """手动触发索引更新"""
        logger.info("手动触发索引更新")
        threading.Thread(target=self._update_index_job).start()


# 全局调度器实例
_scheduler = None

def get_scheduler() -> IndexScheduler:
    """获取全局调度器实例"""
    global _scheduler
    if _scheduler is None:
        _scheduler = IndexScheduler()
    return _scheduler


def start_scheduler():
    """启动索引调度器"""
    scheduler = get_scheduler()
    scheduler.start()
    return scheduler


def stop_scheduler():
    """停止索引调度器"""
    scheduler = get_scheduler()
    scheduler.stop()

