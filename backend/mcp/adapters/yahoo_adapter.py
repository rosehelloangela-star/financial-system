# backend/mcp/adapters/yahoo_adapter.py
"""
Yahoo Finance 数据源适配器
"""
import logging
from typing import Dict, Optional, Any
import asyncio
 
from backend.services.yahoo_finance import yahoo_finance
 
logger = logging.getLogger(__name__)
 
 
class YahooFinanceAdapter:
    """
    Yahoo Finance适配器 - 包装现有服务
    """
    
    def __init__(self):
        self.service = yahoo_finance
    
    async def get_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取股票价格（异步包装）"""
        try:
            loop = asyncio.get_event_loop()
            stock_info = await loop.run_in_executor(
                None,
                self.service.get_stock_info,
                ticker
            )
            
            if not stock_info:
                return None
            
            # 标准化输出
            return {
                "ticker": stock_info.get("ticker"),
                "name": stock_info.get("name"),
                "current_price": stock_info.get("current_price"),
                "previous_close": stock_info.get("previous_close"),
                "change_percent": stock_info.get("regular_market_change_percent"),
                "volume": stock_info.get("volume"),
                "market_cap": stock_info.get("market_cap"),
                "pe_ratio": stock_info.get("pe_ratio"),
                "52_week_high": stock_info.get("52_week_high"),
                "52_week_low": stock_info.get("52_week_low"),
                "sector": stock_info.get("sector"),
                "industry": stock_info.get("industry"),
            }
            
        except Exception as e:
            logger.error(f"❌ Yahoo adapter error for {ticker}: {e}")
            raise
    
    async def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """获取历史数据"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.service.get_historical_data,
                ticker,
                period,
                interval
            )
        except Exception as e:
            logger.error(f"❌ Yahoo historical error: {e}")
            raise
    
    async def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取基本面数据"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.service.get_fundamentals,
                ticker
            )
        except Exception as e:
            logger.error(f"❌ Yahoo fundamentals error: {e}")
            raise
    
    async def get_peer_comparison(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取同行对比"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.service.get_peer_valuation_comparison,
                ticker
            )
        except Exception as e:
            logger.error(f"❌ Yahoo peer comparison error: {e}")
            raise
    
    async def get_analyst_ratings(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取分析师评级"""
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                self.service.get_analyst_recommendations,
                ticker
            )
        except Exception as e:
            logger.error(f"❌ Yahoo analyst ratings error: {e}")
            raise
 
 
# 全局单例
yahoo_adapter = YahooFinanceAdapter()