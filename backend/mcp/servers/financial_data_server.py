# backend/mcp/servers/financial_data_server.py
"""
Financial Data MCP Server - 统一金融数据访问接口
提供标准化的股票数据、市场数据、基本面数据访问
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
 
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
 
from backend.mcp.adapters.yahoo_adapter import YahooFinanceAdapter
from backend.mcp.adapters.alpha_vantage_adapter import AlphaVantageAdapter
from backend.mcp.config.mcp_settings import mcp_settings
 
logger = logging.getLogger(__name__)
 
 
class FinancialDataMCPServer:
    """
    金融数据MCP服务器
    
    功能：
    1. 统一多个数据源（Yahoo Finance, Alpha Vantage等）
    2. 智能路由和故障转移
    3. 数据缓存和性能优化
    4. 标准化错误处理
    """
    
    def __init__(self):
        self.server = Server("financial-data-mcp")
        self.adapters: Dict[str, Any] = {
            "yahoo": YahooFinanceAdapter(),
            "alpha_vantage": AlphaVantageAdapter(),
        }
        self.cache: Dict[str, tuple] = {}  # {cache_key: (data, timestamp)}
        self._register_tools()
        
    def _register_tools(self):
        """注册所有可用工具"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            """列出所有可用工具"""
            return [
                Tool(
                    name="get_stock_price",
                    description="获取股票实时价格和基本信息",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {
                                "type": "string",
                                "description": "股票代码（如 AAPL, MSFT）"
                            },
                            "source": {
                                "type": "string",
                                "enum": ["auto", "yahoo", "alpha_vantage"],
                                "default": "auto",
                                "description": "数据源选择（auto=自动选择最佳）"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="get_historical_data",
                    description="获取股票历史价格数据",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
                                "default": "1mo"
                            },
                            "interval": {
                                "type": "string",
                                "enum": ["1m", "5m", "15m", "1h", "1d", "1wk", "1mo"],
                                "default": "1d"
                            },
                            "source": {
                                "type": "string",
                                "enum": ["auto", "yahoo", "alpha_vantage"],
                                "default": "auto"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="get_fundamentals",
                    description="获取股票基本面数据（估值、盈利能力、财务健康等）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "source": {
                                "type": "string",
                                "enum": ["auto", "yahoo", "alpha_vantage"],
                                "default": "auto"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="get_peer_comparison",
                    description="获取同行业公司估值对比",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "source": {
                                "type": "string",
                                "enum": ["auto", "yahoo"],
                                "default": "auto"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="get_market_indices",
                    description="获取主要市场指数（S&P 500, NASDAQ, DOW等）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "indices": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["^GSPC", "^IXIC", "^DJI"]
                            }
                        }
                    }
                ),
                Tool(
                    name="get_analyst_ratings",
                    description="获取分析师评级和目标价",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "source": {
                                "type": "string",
                                "enum": ["auto", "yahoo"],
                                "default": "auto"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            """执行工具调用"""
            logger.info(f"🔧 Tool called: {name} with args: {arguments}")
            
            try:
                # 路由到对应的处理函数
                if name == "get_stock_price":
                    result = await self._get_stock_price(**arguments)
                elif name == "get_historical_data":
                    result = await self._get_historical_data(**arguments)
                elif name == "get_fundamentals":
                    result = await self._get_fundamentals(**arguments)
                elif name == "get_peer_comparison":
                    result = await self._get_peer_comparison(**arguments)
                elif name == "get_market_indices":
                    result = await self._get_market_indices(**arguments)
                elif name == "get_analyst_ratings":
                    result = await self._get_analyst_ratings(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                # 返回结果
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                logger.error(f"❌ Tool execution failed: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({
                        "error": str(e),
                        "tool": name,
                        "arguments": arguments
                    }, indent=2)
                )]
    
    # ========== 工具实现方法 ==========
    
    async def _get_stock_price(
        self, 
        ticker: str, 
        source: str = "auto"
    ) -> Dict[str, Any]:
        """
        获取股票实时价格
        
        智能路由策略：
        1. auto模式：按优先级尝试各数据源
        2. 指定源：直接调用特定数据源
        3. 故障转移：某个源失败自动切换
        """
        cache_key = f"stock_price:{ticker}:{source}"
        
        # 检查缓存
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            logger.info(f"📦 Cache hit: {cache_key}")
            return cached_data
        
        # 确定数据源列表
        if source == "auto":
            sources = mcp_settings.DATA_SOURCE_PRIORITY
        else:
            sources = [source]
        
        # 尝试各数据源
        last_error = None
        for src in sources:
            try:
                adapter = self.adapters.get(src)
                if not adapter:
                    continue
                
                logger.info(f"📡 Fetching from {src}: {ticker}")
                data = await adapter.get_stock_price(ticker)
                
                if data:
                    # 添加元数据
                    data["_source"] = src
                    data["_timestamp"] = datetime.utcnow().isoformat()
                    
                    # 缓存结果
                    self._set_cache(cache_key, data)
                    
                    return data
                    
            except Exception as e:
                logger.warning(f"⚠️ {src} failed for {ticker}: {e}")
                last_error = e
                continue
        
        # 所有源都失败
        raise Exception(f"All data sources failed for {ticker}. Last error: {last_error}")
    
    async def _get_historical_data(
        self, 
        ticker: str,
        period: str = "1mo",
        interval: str = "1d",
        source: str = "auto"
    ) -> Dict[str, Any]:
        """获取历史数据"""
        cache_key = f"historical:{ticker}:{period}:{interval}:{source}"
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        sources = [source] if source != "auto" else mcp_settings.DATA_SOURCE_PRIORITY
        
        for src in sources:
            try:
                adapter = self.adapters.get(src)
                if not adapter:
                    continue
                
                data = await adapter.get_historical_data(ticker, period, interval)
                if data:
                    data["_source"] = src
                    data["_timestamp"] = datetime.utcnow().isoformat()
                    self._set_cache(cache_key, data)
                    return data
                    
            except Exception as e:
                logger.warning(f"⚠️ {src} historical data failed: {e}")
                continue
        
        raise Exception(f"Failed to fetch historical data for {ticker}")
    
    async def _get_fundamentals(
        self,
        ticker: str,
        source: str = "auto"
    ) -> Dict[str, Any]:
        """获取基本面数据"""
        cache_key = f"fundamentals:{ticker}:{source}"
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        sources = [source] if source != "auto" else mcp_settings.DATA_SOURCE_PRIORITY
        
        for src in sources:
            try:
                adapter = self.adapters.get(src)
                if not adapter:
                    continue
                
                data = await adapter.get_fundamentals(ticker)
                if data:
                    data["_source"] = src
                    data["_timestamp"] = datetime.utcnow().isoformat()
                    self._set_cache(cache_key, data)
                    return data
                    
            except Exception as e:
                logger.warning(f"⚠️ {src} fundamentals failed: {e}")
                continue
        
        raise Exception(f"Failed to fetch fundamentals for {ticker}")
    
    async def _get_peer_comparison(
        self,
        ticker: str,
        source: str = "auto"
    ) -> Dict[str, Any]:
        """获取同行对比"""
        cache_key = f"peer_comparison:{ticker}:{source}"
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # 目前只有Yahoo支持
        adapter = self.adapters.get("yahoo")
        data = await adapter.get_peer_comparison(ticker)
        
        if data:
            data["_source"] = "yahoo"
            data["_timestamp"] = datetime.utcnow().isoformat()
            self._set_cache(cache_key, data)
            return data
        
        raise Exception(f"Failed to fetch peer comparison for {ticker}")
    
    async def _get_market_indices(
        self,
        indices: List[str] = None
    ) -> Dict[str, Any]:
        """获取市场指数"""
        if indices is None:
            indices = ["^GSPC", "^IXIC", "^DJI"]  # S&P 500, NASDAQ, DOW
        
        cache_key = f"market_indices:{':'.join(sorted(indices))}"
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        # 并行获取所有指数
        adapter = self.adapters.get("yahoo")
        
        tasks = [adapter.get_stock_price(idx) for idx in indices]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        indices_data = {}
        for idx, result in zip(indices, results):
            if isinstance(result, Exception):
                logger.warning(f"⚠️ Failed to fetch {idx}: {result}")
                continue
            indices_data[idx] = result
        
        data = {
            "indices": indices_data,
            "_timestamp": datetime.utcnow().isoformat(),
            "_source": "yahoo"
        }
        
        self._set_cache(cache_key, data)
        return data
    
    async def _get_analyst_ratings(
        self,
        ticker: str,
        source: str = "auto"
    ) -> Dict[str, Any]:
        """获取分析师评级"""
        cache_key = f"analyst_ratings:{ticker}:{source}"
        
        cached_data = self._get_from_cache(cache_key)
        if cached_data:
            return cached_data
        
        adapter = self.adapters.get("yahoo")
        data = await adapter.get_analyst_ratings(ticker)
        
        if data:
            data["_source"] = "yahoo"
            data["_timestamp"] = datetime.utcnow().isoformat()
            self._set_cache(cache_key, data)
            return data
        
        raise Exception(f"Failed to fetch analyst ratings for {ticker}")
    
    # ========== 缓存辅助方法 ==========
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """从缓存获取数据"""
        if not mcp_settings.MCP_ENABLE_CACHE:
            return None
        
        if cache_key in self.cache:
            data, timestamp = self.cache[cache_key]
            age = datetime.utcnow().timestamp() - timestamp
            
            if age < mcp_settings.MCP_CACHE_TTL:
                return data
            else:
                del self.cache[cache_key]
        
        return None
    
    def _set_cache(self, cache_key: str, data: Dict):
        """设置缓存"""
        if mcp_settings.MCP_ENABLE_CACHE:
            self.cache[cache_key] = (data, datetime.utcnow().timestamp())
    
    async def run(self):
        """运行MCP服务器（stdio模式）"""
        logger.info("🚀 Starting Financial Data MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
 
 
# 主函数
async def main():
    server = FinancialDataMCPServer()
    await server.run()
 
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())