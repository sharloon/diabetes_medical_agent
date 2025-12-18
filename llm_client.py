"""
LLM客户端封装 - 调用阿里云百炼API
"""
import os
from typing import List, Dict, Optional, Generator
from openai import OpenAI
from loguru import logger

from config import DASHSCOPE_API_KEY, DASHSCOPE_BASE_URL, LLM_MODEL


class LLMClient:
    """LLM客户端，封装OpenAI SDK调用百炼API"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.base_url = base_url or DASHSCOPE_BASE_URL
        self.model = model or LLM_MODEL
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        logger.info(f"LLM客户端初始化完成，模型: {self.model}")
    
    def generate(self, prompt: str, history: List[Dict] = None, 
                 system_prompt: str = None, temperature: float = 0.7) -> str:
        """
        生成回复
        
        Args:
            prompt: 用户输入
            history: 历史对话 [{"role": "user/assistant", "content": "..."}]
            system_prompt: 系统提示词
            temperature: 温度参数
            
        Returns:
            str: 模型回复
        """
        messages = []
        
        # 添加系统提示词
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # 添加历史对话
        if history:
            messages.extend(history)
        
        # 添加当前用户输入
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info(f"调用LLM，prompt长度: {len(prompt)}, 历史消息数: {len(history or [])}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            
            response = completion.choices[0].message.content
            logger.info(f"LLM响应成功，响应长度: {len(response)}")
            return response
            
        except Exception as e:
            error_msg = f"LLM调用失败: {str(e)}"
            logger.error(error_msg)
            return f"抱歉，AI服务暂时不可用，请稍后重试。错误信息: {str(e)}"
    
    def generate_stream(self, prompt: str, history: List[Dict] = None,
                        system_prompt: str = None, temperature: float = 0.7) -> Generator[str, None, None]:
        """
        流式生成回复
        
        Yields:
            str: 模型回复片段
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        if history:
            messages.extend(history)
        
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info(f"调用LLM(流式)，prompt长度: {len(prompt)}")
            
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=True
            )
            
            for chunk in completion:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            error_msg = f"LLM流式调用失败: {str(e)}"
            logger.error(error_msg)
            yield f"抱歉，AI服务暂时不可用，请稍后重试。错误信息: {str(e)}"
    
    def chat(self, messages: List[Dict], temperature: float = 0.7) -> str:
        """
        直接使用消息列表进行对话
        
        Args:
            messages: 完整的消息列表
            temperature: 温度参数
            
        Returns:
            str: 模型回复
        """
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM chat调用失败: {str(e)}")
            return f"抱歉，AI服务暂时不可用: {str(e)}"


# 全局LLM客户端实例
_llm_client = None

def get_llm_client() -> LLMClient:
    """获取全局LLM客户端实例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client


# 医疗助手专用系统提示词
MEDICAL_SYSTEM_PROMPT = """你是一位专业的糖尿病和高血压医疗诊断助手，具备以下能力：

1. **知识储备**：熟悉《高血压诊疗指南》、《中国高血压防治指南》等权威医学文献
2. **临床推理**：能够根据患者症状、检查结果进行鉴别诊断和风险评估
3. **个性化诊疗**：能够制定个性化的治疗方案，包括药物选择、剂量调整
4. **安全意识**：始终关注药物禁忌、相互作用和高风险情况

请遵循以下原则：
- 所有建议必须基于循证医学证据
- 对于高风险情况（如高血压急症、孕妇用药禁忌）必须主动预警
- 回复时需标注证据来源和等级
- 遇到超出能力范围的问题，明确告知并建议转诊

注意：你的建议仅供参考，最终诊疗决策需由执业医师做出。"""


def generate_medical_response(prompt: str, context: str = None, 
                              history: List[Dict] = None) -> str:
    """
    生成医疗相关回复
    
    Args:
        prompt: 用户问题
        context: RAG检索的上下文信息
        history: 历史对话
        
    Returns:
        str: 医疗建议回复
    """
    llm = get_llm_client()
    
    # 构建完整提示词
    full_prompt = prompt
    if context:
        full_prompt = f"""参考信息：
{context}

用户问题：{prompt}

请基于以上参考信息回答用户问题。如果参考信息中没有相关内容，请明确说明。"""
    
    return llm.generate(
        prompt=full_prompt,
        history=history,
        system_prompt=MEDICAL_SYSTEM_PROMPT
    )

