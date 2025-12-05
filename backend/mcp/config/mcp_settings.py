# backend/mcp/config/mcp_settings.py
"""
MCP Server configuration and settings.
"""
from typing import List
import os
 
 
class MCPSettings:
    """MCP服务器配置"""
    
    # 服务器配置
    FINANCIAL_DATA_MCP_HOST: str = "localhost"
    FINANCIAL_DATA_MCP_PORT: int = 8001
    RESEARCH_MCP_HOST: str = "localhost"
    RESEARCH_MCP_PORT: int = 8002
    
    # 数据源优先级
    DATA_SOURCE_PRIORITY: List[str] = ["yahoo", "alpha_vantage"]
    
    # 缓存配置
    MCP_CACHE_TTL: int = 300  # 5 minutes
    MCP_ENABLE_CACHE: bool = True
    
    # 重试配置
    MCP_MAX_RETRIES: int = 3
    MCP_RETRY_DELAY: float = 1.0
    
    # API密钥
    ALPHA_VANTAGE_API_KEY: str = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    
    # 是否启用MCP（开关，方便切换）
    MCP_ENABLED: bool = os.getenv("MCP_ENABLED", "false").lower() == "true"
 
 
mcp_settings = MCPSettings()