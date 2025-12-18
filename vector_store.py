"""
向量存储模块 - 基于LlamaIndex的向量索引
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

from llama_index.core import (
    SimpleDirectoryReader, 
    VectorStoreIndex, 
    StorageContext, 
    load_index_from_storage,
    Document,
    Settings
)
from llama_index.embeddings.dashscope import DashScopeEmbedding, DashScopeTextEmbeddingModels
from llama_index.llms.openai_like import OpenAILike

from config import (
    DATA_DIR, 
    RAG_CONFIG, 
    DASHSCOPE_API_KEY, 
    DASHSCOPE_BASE_URL,
    LLM_MODEL
)


class VectorStore:
    """向量存储服务"""
    
    def __init__(self, persist_dir: str = None):
        self.persist_dir = persist_dir or RAG_CONFIG['persist_dir']
        self.index = None
        self.last_update_time = None
        
        # 设置环境变量（DashScopeEmbedding需要）
        os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY
        
        # 初始化embedding模型 - 显式传入api_key
        self.embed_model = DashScopeEmbedding(
            model_name=DashScopeTextEmbeddingModels.TEXT_EMBEDDING_V2,
            api_key=DASHSCOPE_API_KEY
        )
        
        # 初始化LLM
        self.llm = OpenAILike(
            model=LLM_MODEL,
            api_base=DASHSCOPE_BASE_URL,
            api_key=DASHSCOPE_API_KEY,
            is_chat_model=True
        )
        
        # 设置全局配置
        Settings.embed_model = self.embed_model
        Settings.llm = self.llm
        
        logger.info(f"向量存储初始化完成，持久化目录: {self.persist_dir}")
    
    def build_index(self, documents: List[Document] = None, document_path: str = None) -> bool:
        """
        构建向量索引
        
        Args:
            documents: Document对象列表
            document_path: 文档目录路径
            
        Returns:
            bool: 是否成功
        """
        try:
            if documents:
                # 从Document列表构建
                self.index = VectorStoreIndex.from_documents(
                    documents,
                    embed_model=self.embed_model
                )
            elif document_path:
                # 从目录加载文档
                docs = SimpleDirectoryReader(document_path).load_data()
                self.index = VectorStoreIndex.from_documents(
                    docs,
                    embed_model=self.embed_model
                )
            else:
                # 默认从DATA_DIR加载
                docs = SimpleDirectoryReader(DATA_DIR).load_data()
                self.index = VectorStoreIndex.from_documents(
                    docs,
                    embed_model=self.embed_model
                )
            
            # 持久化索引
            self._persist_index()
            self.last_update_time = datetime.now()
            
            logger.info(f"向量索引构建成功，更新时间: {self.last_update_time}")
            return True
            
        except Exception as e:
            logger.error(f"向量索引构建失败: {e}")
            return False
    
    def build_index_from_chunks(self, chunks: List[Dict]) -> bool:
        """
        从检索块构建索引
        
        Args:
            chunks: 检索块列表 [{'content': str, 'source': dict}, ...]
            
        Returns:
            bool: 是否成功
        """
        try:
            documents = []
            for chunk in chunks:
                # 构建元数据
                metadata = {
                    'source_type': chunk.get('source', {}).get('type', 'unknown'),
                    'filename': chunk.get('source', {}).get('filename', ''),
                    'page': str(chunk.get('source', {}).get('page', '')),
                    'row': str(chunk.get('source', {}).get('row', ''))
                }
                
                doc = Document(
                    text=chunk['content'],
                    metadata=metadata
                )
                documents.append(doc)
            
            return self.build_index(documents=documents)
            
        except Exception as e:
            logger.error(f"从检索块构建索引失败: {e}")
            return False
    
    def load_index(self) -> bool:
        """
        加载已有索引
        
        Returns:
            bool: 是否成功
        """
        try:
            if not os.path.exists(self.persist_dir):
                logger.warning(f"索引目录不存在: {self.persist_dir}")
                return False
            
            storage_context = StorageContext.from_defaults(persist_dir=self.persist_dir)
            self.index = load_index_from_storage(
                storage_context, 
                embed_model=self.embed_model
            )
            
            # 获取索引更新时间
            index_file = os.path.join(self.persist_dir, 'docstore.json')
            if os.path.exists(index_file):
                self.last_update_time = datetime.fromtimestamp(os.path.getmtime(index_file))
            
            logger.info(f"索引加载成功，最后更新时间: {self.last_update_time}")
            return True
            
        except Exception as e:
            logger.error(f"索引加载失败: {e}")
            return False
    
    def _persist_index(self):
        """持久化索引"""
        if self.index:
            os.makedirs(self.persist_dir, exist_ok=True)
            self.index.storage_context.persist(self.persist_dir)
            logger.info(f"索引已持久化到: {self.persist_dir}")
    
    def search(self, query: str, top_k: int = None) -> List[Dict]:
        """
        检索相关文档
        
        Args:
            query: 检索查询
            top_k: 返回结果数
            
        Returns:
            List[Dict]: 检索结果列表
        """
        if self.index is None:
            logger.warning("索引未初始化，尝试加载")
            if not self.load_index():
                return []
        
        top_k = top_k or RAG_CONFIG['top_k']
        
        try:
            retriever = self.index.as_retriever(similarity_top_k=top_k)
            nodes = retriever.retrieve(query)
            
            results = []
            for node in nodes:
                result = {
                    'content': node.node.text,
                    'score': node.score,
                    'source': {
                        'type': node.node.metadata.get('source_type', 'unknown'),
                        'filename': node.node.metadata.get('filename', ''),
                        'page': node.node.metadata.get('page', ''),
                        'row': node.node.metadata.get('row', '')
                    }
                }
                results.append(result)
            
            logger.info(f"检索完成，查询: '{query[:50]}...', 结果数: {len(results)}")
            return results
            
        except Exception as e:
            logger.error(f"检索失败: {e}")
            return []
    
    def get_query_engine(self, streaming: bool = True):
        """
        获取查询引擎
        
        Args:
            streaming: 是否流式输出
            
        Returns:
            QueryEngine: 查询引擎
        """
        if self.index is None:
            if not self.load_index():
                return None
        
        return self.index.as_query_engine(
            streaming=streaming,
            llm=self.llm
        )
    
    def query(self, question: str) -> str:
        """
        执行RAG查询
        
        Args:
            question: 问题
            
        Returns:
            str: 回答
        """
        query_engine = self.get_query_engine(streaming=False)
        if query_engine is None:
            return "知识库未初始化，请先构建索引。"
        
        try:
            response = query_engine.query(question)
            return str(response)
        except Exception as e:
            logger.error(f"RAG查询失败: {e}")
            return f"查询失败: {str(e)}"
    
    def get_index_info(self) -> Dict:
        """获取索引信息"""
        info = {
            'persist_dir': self.persist_dir,
            'is_loaded': self.index is not None,
            'last_update_time': self.last_update_time.isoformat() if self.last_update_time else None,
            'doc_count': 0
        }
        
        if self.index:
            try:
                info['doc_count'] = len(self.index.docstore.docs)
            except:
                pass
        
        return info
    
    def refresh_index(self) -> bool:
        """刷新索引（重新构建）"""
        logger.info("开始刷新索引...")
        return self.build_index()


# 全局向量存储实例
_vector_store = None

def get_vector_store() -> VectorStore:
    """获取全局向量存储实例"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def init_vector_store(force_rebuild: bool = False) -> bool:
    """
    初始化向量存储
    
    Args:
        force_rebuild: 是否强制重建索引
        
    Returns:
        bool: 是否成功
    """
    store = get_vector_store()
    
    if force_rebuild:
        logger.info("强制重建索引")
        return store.build_index()
    
    # 尝试加载现有索引
    if store.load_index():
        return True
    
    # 如果加载失败，构建新索引
    logger.info("现有索引不存在或加载失败，开始构建新索引")
    return store.build_index()

