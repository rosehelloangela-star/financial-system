# backend/crewai_integration/tools/financial_tools.py
"""
CrewAI工具定义 - 包装现有功能为CrewAI Tools
"""
from crewai.tools import tool
from typing import Dict, Any
import asyncio
import logging
 
from backend.services.yahoo_finance import yahoo_finance
 
logger = logging.getLogger(__name__)
 
 
@tool("获取股票价格")
def get_stock_price_tool(ticker: str) -> Dict[str, Any]:
    """
    获取股票的实时价格和基本信息
    
    Args:
        ticker: 股票代码（如 AAPL, MSFT）
    
    Returns:
        包含价格、涨跌幅、市值等信息的字典
    """
    try:
        return yahoo_finance.get_stock_info(ticker)
    except Exception as e:
        logger.error(f"Error fetching stock price: {e}")
        return {"error": str(e)}
 
 
@tool("获取历史数据")
def get_historical_data_tool(ticker: str, period: str = "1mo") -> Dict[str, Any]:
    """
    获取股票的历史价格数据
    
    Args:
        ticker: 股票代码
        period: 时间周期（1d, 5d, 1mo, 3mo, 6mo, 1y）
    
    Returns:
        历史价格数据
    """
    try:
        return yahoo_finance.get_historical_data(ticker, period=period)
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return {"error": str(e)}
 
 
@tool("获取基本面数据")
def get_fundamentals_tool(ticker: str) -> Dict[str, Any]:
    """
    获取股票的基本面财务数据
    
    Args:
        ticker: 股票代码
    
    Returns:
        估值、盈利能力、财务健康等指标
    """
    try:
        return yahoo_finance.get_fundamentals(ticker)
    except Exception as e:
        logger.error(f"Error fetching fundamentals: {e}")
        return {"error": str(e)}
 
 
@tool("分析情感")
def analyze_sentiment_tool(ticker: str) -> Dict[str, Any]:
    """
    分析股票相关新闻的市场情感
    
    Args:
        ticker: 股票代码
    
    Returns:
        情感评分和分析结果
    """
    try:
        news = yahoo_finance.get_news(ticker, limit=20)
        
        # 简单情感分析
        positive_keywords = ["bullish", "up", "gain", "profit", "growth", "beat"]
        negative_keywords = ["bearish", "down", "loss", "decline", "miss", "fall"]
        
        scores = []
        for item in news:
            title = (item.get("title") or "").lower()
            pos = sum(1 for kw in positive_keywords if kw in title)
            neg = sum(1 for kw in negative_keywords if kw in title)
            scores.append(1 if pos > neg else -1 if neg > pos else 0)
        
        avg_sentiment = sum(scores) / len(scores) if scores else 0
        
        return {
            "ticker": ticker,
            "sentiment": "positive" if avg_sentiment > 0.2 else "negative" if avg_sentiment < -0.2 else "neutral",
            "score": round(avg_sentiment, 2),
            "news_count": len(news)
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {"error": str(e)}
 
 
@tool("搜索新闻")
def search_news_tool(ticker: str, limit: int = 10) -> list:
    """
    搜索股票相关新闻
    
    Args:
        ticker: 股票代码
        limit: 返回新闻数量
    
    Returns:
        新闻列表
    """
    try:
        return yahoo_finance.get_news(ticker, limit=limit)
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        return []
 
 
@tool("获取分析师评级")
def get_analyst_ratings_tool(ticker: str) -> Dict[str, Any]:
    """
    获取分析师评级和目标价
    
    Args:
        ticker: 股票代码
    
    Returns:
        分析师共识、目标价等信息
    """
    try:
        return yahoo_finance.get_analyst_recommendations(ticker)
    except Exception as e:
        logger.error(f"Error fetching analyst ratings: {e}")
        return {"error": str(e)}
 
 
@tool("生成图表")
def generate_chart_tool(ticker: str, chart_type: str = "line") -> str:
    """
    生成股票价格图表
    
    Args:
        ticker: 股票代码
        chart_type: 图表类型（line, candlestick）
    
    Returns:
        图表描述或数据
    """
    try:
        hist_data = yahoo_finance.get_historical_data(ticker, period="1mo")
        if hist_data and "summary" in hist_data:
            summary = hist_data["summary"]
            return (
                f"Generated {chart_type} chart for {ticker}: "
                f"Latest close: ${summary['latest_close']:.2f}, "
                f"High: ${summary['highest']:.2f}, "
                f"Low: ${summary['lowest']:.2f}"
            )
        return "Chart data unavailable"
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return f"Error: {str(e)}"