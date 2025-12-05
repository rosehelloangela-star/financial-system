# backend/mcp/servers/investment_research_server.py
"""
Investment Research MCP Server - 投资研究工具
提供情感分析、新闻搜索、SEC文件检索、图表生成等功能
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import base64
 
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent
 
from backend.rag.news_aggregator import NewsAggregator
from backend.rag.edgar_scraper import edgar_scraper
from backend.services.yahoo_finance import yahoo_finance
 
logger = logging.getLogger(__name__)
 
 
class InvestmentResearchMCPServer:
    """
    投资研究MCP服务器
    
    功能：
    1. 新闻聚合和情感分析
    2. SEC文件检索
    3. 图表生成
    4. 分析师评级聚合
    """
    
    def __init__(self):
        self.server = Server("investment-research-mcp")
        self.news_aggregator = NewsAggregator()
        self._register_tools()
    
    def _register_tools(self):
        """注册研究工具"""
        
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="analyze_sentiment",
                    description="分析股票新闻情感和市场情绪",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "timeframe": {
                                "type": "string",
                                "enum": ["24h", "7d", "30d"],
                                "default": "7d"
                            },
                            "include_social": {
                                "type": "boolean",
                                "default": False,
                                "description": "是否包含社交媒体数据"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="search_sec_filings",
                    description="搜索SEC文件（10-K, 10-Q, 8-K等）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "filing_type": {
                                "type": "string",
                                "enum": ["10-K", "10-Q", "8-K", "all"],
                                "default": "10-K"
                            },
                            "limit": {
                                "type": "integer",
                                "default": 5,
                                "minimum": 1,
                                "maximum": 20
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="search_news",
                    description="搜索相关新闻文章",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "sources": {
                                "type": "array",
                                "items": {"type": "string"},
                                "default": ["yahoo", "marketwatch", "seekingalpha"]
                            },
                            "limit": {
                                "type": "integer",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="generate_chart",
                    description="生成股票图表（价格走势、K线图等）",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"},
                            "chart_type": {
                                "type": "string",
                                "enum": ["line", "candlestick", "volume"],
                                "default": "line"
                            },
                            "period": {
                                "type": "string",
                                "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
                                "default": "1mo"
                            }
                        },
                        "required": ["ticker"]
                    }
                ),
                Tool(
                    name="get_analyst_consensus",
                    description="获取分析师共识和评级分布",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "ticker": {"type": "string"}
                        },
                        "required": ["ticker"]
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent | ImageContent]:
            logger.info(f"🔧 Research tool called: {name}")
            
            try:
                if name == "analyze_sentiment":
                    result = await self._analyze_sentiment(**arguments)
                elif name == "search_sec_filings":
                    result = await self._search_sec_filings(**arguments)
                elif name == "search_news":
                    result = await self._search_news(**arguments)
                elif name == "generate_chart":
                    return await self._generate_chart(**arguments)
                elif name == "get_analyst_consensus":
                    result = await self._get_analyst_consensus(**arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
                
                return [TextContent(
                    type="text",
                    text=json.dumps(result, indent=2, default=str)
                )]
                
            except Exception as e:
                logger.error(f"❌ Tool error: {e}")
                return [TextContent(
                    type="text",
                    text=json.dumps({"error": str(e)}, indent=2)
                )]
    
    # ========== 工具实现 ==========
    
    async def _analyze_sentiment(
        self,
        ticker: str,
        timeframe: str = "7d",
        include_social: bool = False
    ) -> Dict[str, Any]:
        """情感分析"""
        try:
            # 获取新闻
            news_items = await asyncio.get_event_loop().run_in_executor(
                None,
                yahoo_finance.get_news,
                ticker,
                50
            )
            
            if not news_items:
                return {
                    "ticker": ticker,
                    "sentiment": "neutral",
                    "score": 0.0,
                    "confidence": 0.0,
                    "news_count": 0
                }
            
            # 简单情感评分（实际应使用NLP模型）
            positive_keywords = ["bullish", "up", "gain", "profit", "growth", "beat", "surge"]
            negative_keywords = ["bearish", "down", "loss", "decline", "miss", "fall", "drop"]
            
            sentiment_scores = []
            for item in news_items:
                title = (item.get("title") or "").lower()
                summary = (item.get("summary") or "").lower()
                text = title + " " + summary
                
                pos_count = sum(1 for kw in positive_keywords if kw in text)
                neg_count = sum(1 for kw in negative_keywords if kw in text)
                
                if pos_count > neg_count:
                    sentiment_scores.append(1)
                elif neg_count > pos_count:
                    sentiment_scores.append(-1)
                else:
                    sentiment_scores.append(0)
            
            avg_sentiment = sum(sentiment_scores) / len(sentiment_scores)
            
            if avg_sentiment > 0.2:
                sentiment = "positive"
            elif avg_sentiment < -0.2:
                sentiment = "negative"
            else:
                sentiment = "neutral"
            
            return {
                "ticker": ticker,
                "sentiment": sentiment,
                "score": round(avg_sentiment, 2),
                "confidence": min(abs(avg_sentiment) * 2, 1.0),
                "news_count": len(news_items),
                "timeframe": timeframe,
                "positive_ratio": sum(1 for s in sentiment_scores if s > 0) / len(sentiment_scores),
                "negative_ratio": sum(1 for s in sentiment_scores if s < 0) / len(sentiment_scores),
                "recent_headlines": [item.get("title") for item in news_items[:5]],
                "_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Sentiment analysis error: {e}")
            raise
    
    async def _search_sec_filings(
        self,
        ticker: str,
        filing_type: str = "10-K",
        limit: int = 5
    ) -> Dict[str, Any]:
        """搜索SEC文件"""
        try:
            # 使用现有的EDGAR scraper
            filings = await asyncio.get_event_loop().run_in_executor(
                None,
                edgar_scraper.get_company_filings,
                ticker,
                filing_type if filing_type != "all" else None,
                limit
            )
            
            return {
                "ticker": ticker,
                "filing_type": filing_type,
                "filings": filings,
                "count": len(filings),
                "_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ SEC filings search error: {e}")
            raise
    
    async def _search_news(
        self,
        query: str,
        sources: List[str] = None,
        limit: int = 10
    ) -> Dict[str, Any]:
        """搜索新闻"""
        try:
            # 使用新闻聚合器
            articles = await self.news_aggregator.search_news(
                query=query,
                sources=sources or ["yahoo"],
                limit=limit
            )
            
            return {
                "query": query,
                "articles": articles,
                "count": len(articles),
                "sources": sources,
                "_timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ News search error: {e}")
            raise
    
    async def _generate_chart(
        self,
        ticker: str,
        chart_type: str = "line",
        period: str = "1mo"
    ) -> List[ImageContent]:
        """生成图表（返回base64编码的PNG）"""
        try:
            import matplotlib.pyplot as plt
            import io
            
            # 获取历史数据
            hist_data = await asyncio.get_event_loop().run_in_executor(
                None,
                yahoo_finance.get_historical_data,
                ticker,
                period,
                "1d"
            )
            
            if not hist_data or "data" not in hist_data:
                raise Exception("No data available for chart")
            
            # 提取价格数据
            data = hist_data["data"]
            dates = list(data.keys())
            closes = [data[d]["Close"] for d in dates]
            
            # 生成图表
            fig, ax = plt.subplots(figsize=(12, 6))
            
            if chart_type == "line":
                ax.plot(dates, closes, linewidth=2)
                ax.set_title(f"{ticker} Price Chart - {period}")
                ax.set_ylabel("Price ($)")
            
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # 转换为base64
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150)
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode()
            plt.close()
            
            return [ImageContent(
                type="image",
                data=img_base64,
                mimeType="image/png"
            )]
            
        except Exception as e:
            logger.error(f"❌ Chart generation error: {e}")
            raise
    
    async def _get_analyst_consensus(self, ticker: str) -> Dict[str, Any]:
        """获取分析师共识"""
        try:
            ratings = await asyncio.get_event_loop().run_in_executor(
                None,
                yahoo_finance.get_analyst_recommendations,
                ticker
            )
            
            return ratings or {}
            
        except Exception as e:
            logger.error(f"❌ Analyst consensus error: {e}")
            raise
    
    async def run(self):
        """运行MCP服务器"""
        logger.info("🚀 Starting Investment Research MCP Server...")
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )
 
 
async def main():
    server = InvestmentResearchMCPServer()
    await server.run()
 
 
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())