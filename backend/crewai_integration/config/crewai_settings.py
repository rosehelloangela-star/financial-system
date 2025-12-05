# backend/crewai_integration/config/crewai_settings.py
"""
CrewAI配置
"""
from typing import Literal
import os
 
 
class CrewAISettings:
    """CrewAI配置"""
    
    # 执行模式
    PROCESS_TYPE: Literal["sequential", "hierarchical"] = "hierarchical"
    
    # 异步设置
    ENABLE_ASYNC: bool = True
    MAX_CONCURRENT_TASKS: int = 3
    
    # 管理者设置（hierarchical模式）
    MANAGER_LLM: str = "gpt-4"
    MANAGER_TEMPERATURE: float = 0.7
    
    # 任务超时
    TASK_TIMEOUT: int = 300  # 5分钟
    
    # 监控设置
    ENABLE_MONITORING: bool = True
    LOG_TASK_EXECUTION: bool = True
    
    # LLM配置
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    DEFAULT_LLM_MODEL: str = "gpt-3.5-turbo"
 
 
crewai_settings = CrewAISettings()