# backend/agents/market_data_agent.py
"""
Market Data Agent - 支持MCP和传统模式
"""
from typing import List
import asyncio
import os
import logging
 
from backend.agents.base_agent import BaseAgent
from backend.agents.state import AgentState, MarketData, PeerValuation
 
# 配置logger
logger = logging.getLogger(__name__)

# 根据配置选择数据源
USE_MCP = os.getenv("MCP_ENABLED", "false").lower() == "true"

if USE_MCP:
    from backend.mcp.client.mcp_client import mcp_client
    logger.info("🔌 Market Data Agent using MCP mode")
else:
    from backend.services.yahoo_finance import yahoo_finance
    logger.info("📡 Market Data Agent using direct mode")
 
 
class MarketDataAgent(BaseAgent):
    """
    获取市场数据
    支持两种模式：
    1. MCP模式（MCP_ENABLED=true）：通过MCP客户端
    2. 直接模式（默认）：直接调用Yahoo Finance
    """
 
    def __init__(self):
        super().__init__("market_data")
        self.use_mcp = USE_MCP
        
        if self.use_mcp:
            self.mcp_client = mcp_client
        else:
            self.yahoo = yahoo_finance
 
    async def execute(self, state: AgentState) -> AgentState:
        """获取市场数据"""
        tickers = state.get("tickers", [])
 
        if not tickers:
            self.logger.warning("No tickers to fetch market data for")
            return state
 
        market_data_list = []
        peer_valuation_list = []
 
        for ticker in tickers:
            self.logger.info(f"Fetching market data for {ticker} (MCP: {self.use_mcp})")
 
            try:
                if self.use_mcp:
                    # MCP模式
                    data, peer_data = await asyncio.gather(
                        self._fetch_via_mcp(ticker),
                        self._fetch_peer_via_mcp(ticker),
                        return_exceptions=True
                    )
                else:
                    # 直接模式（保持原有逻辑）
                    data, peer_data = await asyncio.gather(
                        self._fetch_ticker_data_async(ticker),
                        self._fetch_peer_valuation_async(ticker),
                        return_exceptions=True
                    )
 
                # 处理结果（统一逻辑）
                if isinstance(data, Exception):
                    self.logger.error(f"Market data error for {ticker}: {data}")
                elif isinstance(data, dict) and data:
                    market_data_list.append(data)
 
                if isinstance(peer_data, Exception):
                    self.logger.error(f"Peer valuation error for {ticker}: {peer_data}")
                elif isinstance(peer_data, dict) and peer_data:
                    peer_valuation_list.append(peer_data)
 
            except Exception as e:
                self.logger.error(f"Failed to fetch data for {ticker}: {e}")
                continue
 
        return {
            "market_data": market_data_list,
            "peer_valuation": peer_valuation_list
        }
 
    # ========== MCP模式方法 ==========
    
    async def _fetch_via_mcp(self, ticker: str) -> MarketData:
        """通过MCP获取数据"""
        data = await self.mcp_client.call_tool(
            server="financial_data",
            tool_name="get_stock_price",
            arguments={"ticker": ticker, "source": "auto"}
        )
        
        return self._convert_mcp_to_market_data(data)
    
    async def _fetch_peer_via_mcp(self, ticker: str) -> PeerValuation:
        """通过MCP获取同行数据"""
        data = await self.mcp_client.call_tool(
            server="financial_data",
            tool_name="get_peer_comparison",
            arguments={"ticker": ticker}
        )
        
        return self._convert_mcp_to_peer_valuation(data)
    
    def _convert_mcp_to_market_data(self, data: dict) -> MarketData:
        """转换MCP数据格式"""
        current_price = data.get("current_price")
        week_52_high = data.get("52_week_high")
        week_52_low = data.get("52_week_low")
 
        # 计算趋势指标
        week_52_position = None
        distance_from_high = None
        distance_from_low = None
        trend_signal = None
 
        if current_price and week_52_high and week_52_low and week_52_high > week_52_low:
            week_52_position = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100
            distance_from_high = ((current_price - week_52_high) / week_52_high) * 100
            distance_from_low = ((current_price - week_52_low) / week_52_low) * 100
 
            if week_52_position >= 80:
                trend_signal = "near_high"
            elif week_52_position <= 20:
                trend_signal = "near_low"
            else:
                trend_signal = "mid_range"
 
        return MarketData(
            ticker=data.get("ticker"),
            current_price=current_price,
            change_percent=round(data.get("change_percent", 0), 2),
            volume=data.get("volume"),
            market_cap=data.get("market_cap"),
            pe_ratio=data.get("pe_ratio"),
            day_high=week_52_high,
            day_low=week_52_low,
            year_high=week_52_high,
            year_low=week_52_low,
            week_52_position=round(week_52_position, 1) if week_52_position else None,
            distance_from_high=round(distance_from_high, 1) if distance_from_high else None,
            distance_from_low=round(distance_from_low, 1) if distance_from_low else None,
            trend_signal=trend_signal
        )
    
    def _convert_mcp_to_peer_valuation(self, data: dict) -> PeerValuation:
        """转换同行数据格式"""
        return PeerValuation(
            ticker=data.get("ticker"),
            sector=data.get("sector"),
            industry=data.get("industry"),
            pe_ratio=data.get("pe_ratio"),
            price_to_book=data.get("price_to_book"),
            price_to_sales=data.get("price_to_sales"),
            sector_avg_pe=data.get("sector_avg_pe"),
            sector_avg_pb=data.get("sector_avg_pb"),
            sector_avg_ps=data.get("sector_avg_ps"),
            pe_premium_discount=data.get("pe_premium_discount"),
            pb_premium_discount=data.get("pb_premium_discount"),
            ps_premium_discount=data.get("ps_premium_discount"),
            peer_count=data.get("peer_count", 0)
        )
 
    # ========== 直接模式方法（保持原有代码） ==========
    
    def _fetch_ticker_data(self, ticker: str) -> MarketData:
        """直接模式：获取股票数据"""
        stock_info = self.yahoo.get_stock_info(ticker)
        
        if not stock_info:
            return None
        
        # ... 保持你原来的实现
        current_price = stock_info.get("current_price")
        change_percent = stock_info.get("regular_market_change_percent")
        
        # 计算52周指标
        week_52_high = stock_info.get("52_week_high")
        week_52_low = stock_info.get("52_week_low")
        
        week_52_position = None
        distance_from_high = None
        distance_from_low = None
        trend_signal = None
        
        if current_price and week_52_high and week_52_low and week_52_high > week_52_low:
            week_52_position = ((current_price - week_52_low) / (week_52_high - week_52_low)) * 100
            distance_from_high = ((current_price - week_52_high) / week_52_high) * 100
            distance_from_low = ((current_price - week_52_low) / week_52_low) * 100
            
            if week_52_position >= 80:
                trend_signal = "near_high"
            elif week_52_position <= 20:
                trend_signal = "near_low"
            else:
                trend_signal = "mid_range"
        
        return MarketData(
            ticker=ticker,
            current_price=current_price,
            change_percent=round(change_percent, 2) if change_percent else None,
            volume=stock_info.get("volume"),
            market_cap=stock_info.get("market_cap"),
            pe_ratio=stock_info.get("pe_ratio"),
            day_high=week_52_high,
            day_low=week_52_low,
            year_high=week_52_high,
            year_low=week_52_low,
            week_52_position=round(week_52_position, 1) if week_52_position else None,
            distance_from_high=round(distance_from_high, 1) if distance_from_high else None,
            distance_from_low=round(distance_from_low, 1) if distance_from_low else None,
            trend_signal=trend_signal
        )
    
    def _fetch_peer_valuation(self, ticker: str) -> PeerValuation:
        """直接模式：获取同行对比"""
        peer_data = self.yahoo.get_peer_valuation_comparison(ticker)
        
        if not peer_data:
            return None
        
        return PeerValuation(
            ticker=peer_data.get("ticker"),
            sector=peer_data.get("sector"),
            industry=peer_data.get("industry"),
            pe_ratio=peer_data.get("pe_ratio"),
            price_to_book=peer_data.get("price_to_book"),
            price_to_sales=peer_data.get("price_to_sales"),
            sector_avg_pe=peer_data.get("sector_avg_pe"),
            sector_avg_pb=peer_data.get("sector_avg_pb"),
            sector_avg_ps=peer_data.get("sector_avg_ps"),
            pe_premium_discount=peer_data.get("pe_premium_discount"),
            pb_premium_discount=peer_data.get("pb_premium_discount"),
            ps_premium_discount=peer_data.get("ps_premium_discount"),
            peer_count=peer_data.get("peer_count", 0)
        )
    
    async def _fetch_ticker_data_async(self, ticker: str) -> MarketData:
        """异步包装"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_ticker_data, ticker)
    
    async def _fetch_peer_valuation_async(self, ticker: str) -> PeerValuation:
        """异步包装"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_peer_valuation, ticker)
    
# 创建并导出 market_data_agent 实例
market_data_agent = MarketDataAgent()