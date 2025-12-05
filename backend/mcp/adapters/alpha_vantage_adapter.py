# backend/mcp/adapters/alpha_vantage_adapter.py
"""
Alpha Vantage 数据源适配器
作为Yahoo Finance的备用数据源
"""
import logging
from typing import Dict, Optional, Any
import aiohttp
from backend.mcp.config.mcp_settings import mcp_settings
 
logger = logging.getLogger(__name__)
 
 
class AlphaVantageAdapter:
    """
    Alpha Vantage适配器
    免费API，每分钟5次请求限制
    """
    
    BASE_URL = "https://www.alphavantage.co/query"
    
    def __init__(self):
        self.api_key = mcp_settings.ALPHA_VANTAGE_API_KEY
    
    async def get_stock_price(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取股票价格"""
        if not self.api_key:
            logger.warning("Alpha Vantage API key not configured")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self.api_key
                }
                
                async with session.get(self.BASE_URL, params=params) as resp:
                    if resp.status != 200:
                        raise Exception(f"HTTP {resp.status}")
                    
                    data = await resp.json()
                    quote = data.get("Global Quote", {})
                    
                    if not quote:
                        return None
                    
                    # 标准化格式
                    return {
                        "ticker": ticker.upper(),
                        "current_price": float(quote.get("05. price", 0)),
                        "change_percent": float(quote.get("10. change percent", "0").rstrip("%")),
                        "volume": int(quote.get("06. volume", 0)),
                        "previous_close": float(quote.get("08. previous close", 0)),
                        "52_week_high": float(quote.get("03. high", 0)),
                        "52_week_low": float(quote.get("04. low", 0)),
                    }
                    
        except Exception as e:
            logger.error(f"❌ Alpha Vantage error for {ticker}: {e}")
            raise
    
    async def get_historical_data(
        self,
        ticker: str,
        period: str = "1mo",
        interval: str = "1d"
    ) -> Optional[Dict[str, Any]]:
        """获取历史数据"""
        if not self.api_key:
            return None
        
        # Alpha Vantage使用不同的时间序列函数
        function_map = {
            "1d": "TIME_SERIES_INTRADAY",
            "1wk": "TIME_SERIES_WEEKLY",
            "1mo": "TIME_SERIES_MONTHLY"
        }
        
        function = function_map.get(interval, "TIME_SERIES_DAILY")
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "function": function,
                    "symbol": ticker,
                    "apikey": self.api_key,
                    "outputsize": "compact" if period in ["1d", "5d"] else "full"
                }
                
                if interval in ["1m", "5m", "15m"]:
                    params["interval"] = interval
                
                async with session.get(self.BASE_URL, params=params) as resp:
                    data = await resp.json()
                    
                    # 提取时间序列数据
                    time_series_key = [k for k in data.keys() if "Time Series" in k]
                    if not time_series_key:
                        return None
                    
                    time_series = data[time_series_key[0]]
                    
                    return {
                        "ticker": ticker,
                        "period": period,
                        "interval": interval,
                        "data": time_series
                    }
                    
        except Exception as e:
            logger.error(f"❌ Alpha Vantage historical error: {e}")
            raise
    
    async def get_fundamentals(self, ticker: str) -> Optional[Dict[str, Any]]:
        """获取基本面数据"""
        if not self.api_key:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {
                    "function": "OVERVIEW",
                    "symbol": ticker,
                    "apikey": self.api_key
                }
                
                async with session.get(self.BASE_URL, params=params) as resp:
                    data = await resp.json()
                    
                    if not data or "Symbol" not in data:
                        return None
                    
                    # 标准化格式
                    return {
                        "ticker": ticker,
                        "valuation": {
                            "market_cap": int(data.get("MarketCapitalization", 0)),
                            "pe_ratio": float(data.get("PERatio", 0)),
                            "peg_ratio": float(data.get("PEGRatio", 0)),
                            "price_to_book": float(data.get("PriceToBookRatio", 0)),
                            "price_to_sales": float(data.get("PriceToSalesRatioTTM", 0))
                        },
                        "profitability": {
                            "profit_margin": float(data.get("ProfitMargin", 0)),
                            "operating_margin": float(data.get("OperatingMarginTTM", 0)),
                            "return_on_assets": float(data.get("ReturnOnAssetsTTM", 0)),
                            "return_on_equity": float(data.get("ReturnOnEquityTTM", 0))
                        },
                        "financial_health": {
                            "debt_to_equity": float(data.get("DebtToEquity", 0)),
                            "current_ratio": float(data.get("CurrentRatio", 0)),
                        }
                    }
                    
        except Exception as e:
            logger.error(f"❌ Alpha Vantage fundamentals error: {e}")
            raise