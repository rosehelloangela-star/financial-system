# backend/mcp/client/mcp_client.py
"""
简化的MCP客户端 - 内部路由版本
不需要启动独立的MCP服务器，直接调用适配器
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import time
 
from backend.mcp.adapters.yahoo_adapter import yahoo_adapter
from backend.mcp.config.mcp_settings import mcp_settings
 
logger = logging.getLogger(__name__)
 
 
class SimpleMCPClient:
    """
    简化的MCP客户端 - 内部实现版
    
    优势：
    1. 不需要启动独立进程
    2. 保持MCP的接口标准
    3. 支持智能路由和缓存
    4. 易于调试
    """
    
    def __init__(self):
        self.adapters = {
            "yahoo": yahoo_adapter
        }
        self.cache: Dict[str, tuple] = {}
        self.connected = False
    
    async def connect(self):
        """模拟连接（实际上是初始化）"""
        if self.connected:
            return
        
        logger.info("🔌 Initializing MCP client (internal mode)...")
        
        # 预热缓存或其他初始化
        self.connected = True
        logger.info("✅ MCP client ready")
    
    async def call_tool(
        self,
        server: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        调用MCP工具
        
        Args:
            server: 服务器名称 ("financial_data" 或 "research")
            tool_name: 工具名称
            arguments: 参数
        """
        if not self.connected:
            await self.connect()
        
        logger.info(f"🔧 MCP Tool: {server}/{tool_name}")
        
        try:
            # 路由到对应的工具
            if server == "financial_data":
                return await self._call_financial_tool(tool_name, arguments)
            elif server == "research":
                return await self._call_research_tool(tool_name, arguments)
            else:
                raise ValueError(f"Unknown server: {server}")
                
        except Exception as e:
            logger.error(f"❌ MCP tool call failed: {e}")
            raise
    
    async def _call_financial_tool(self, tool_name: str, args: Dict) -> Any:
        """调用金融数据工具"""
        ticker = args.get("ticker")
        source = args.get("source", "auto")
        
        # 检查缓存
        cache_key = f"{tool_name}:{ticker}:{source}"
        cached = self._get_cache(cache_key)
        if cached:
            logger.info(f"📦 Cache hit: {cache_key}")
            return cached
        
        # 选择数据源（目前只有Yahoo）
        adapter = self.adapters.get("yahoo")
        
        # 调用对应方法
        if tool_name == "get_stock_price":
            result = await adapter.get_stock_price(ticker)
        elif tool_name == "get_historical_data":
            period = args.get("period", "1mo")
            interval = args.get("interval", "1d")
            result = await adapter.get_historical_data(ticker, period, interval)
        elif tool_name == "get_fundamentals":
            result = await adapter.get_fundamentals(ticker)
        elif tool_name == "get_peer_comparison":
            result = await adapter.get_peer_comparison(ticker)
        elif tool_name == "get_analyst_ratings":
            result = await adapter.get_analyst_ratings(ticker)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # 添加元数据
        if result:
            result["_source"] = "yahoo"
            result["_timestamp"] = datetime.utcnow().isoformat()
            result["_via_mcp"] = True
        
        # 缓存结果
        self._set_cache(cache_key, result)
        
        return result
    
    async def _call_research_tool(self, tool_name: str, args: Dict) -> Any:
        """调用研究工具（暂未实现）"""
        logger.warning(f"Research tool {tool_name} not yet implemented")
        return {"error": "Not implemented"}
    
    def _get_cache(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not mcp_settings.MCP_ENABLE_CACHE:
            return None
        
        if key in self.cache:
            data, timestamp = self.cache[key]
            age = time.time() - timestamp
            
            if age < mcp_settings.MCP_CACHE_TTL:
                return data
            else:
                del self.cache[key]
        
        return None
    
    def _set_cache(self, key: str, data: Any):
        """设置缓存"""
        if mcp_settings.MCP_ENABLE_CACHE and data:
            self.cache[key] = (data, time.time())
    
    async def close(self):
        """关闭连接"""
        self.connected = False
        self.cache.clear()
        logger.info("✅ MCP client closed")
 
 
# 全局单例
mcp_client = SimpleMCPClient()