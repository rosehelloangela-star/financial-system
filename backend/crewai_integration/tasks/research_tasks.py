# backend/crewai_integration/tasks/research_tasks.py
"""
CrewAI任务定义
"""
from crewai import Task
from typing import List, Dict, Any
import logging
 
from backend.crewai_integration.agents.crewai_agents import (
    market_data_researcher,
    sentiment_analyst,
    forward_looking_analyst,
    visualization_specialist,
    report_writer
)
 
logger = logging.getLogger(__name__)
 
 
def create_research_tasks(ticker: str, query: str) -> List[Task]:
    """
    创建投资研究任务流
    
    Args:
        ticker: 股票代码
        query: 用户查询
    
    Returns:
        任务列表
    """
    
    # Task 1: 市场数据收集（异步）
    market_data_task = Task(
        description=(
            f"收集 {ticker} 的完整市场数据：\n"
            f"1. 当前价格、涨跌幅、交易量\n"
            f"2. 52周高低点和趋势\n"
            f"3. 基本面指标（P/E, P/B, 市值等）\n"
            f"4. 同行业对比数据\n"
            f"用户查询：{query}"
        ),
        expected_output="详细的市场数据报告，包含所有关键指标和趋势分析",
        agent=market_data_researcher,
        async_execution=True,  # 异步执行
    )
    
    # Task 2: 情感分析（异步，独立于Task 1）
    sentiment_task = Task(
        description=(
            f"分析 {ticker} 的市场情感：\n"
            f"1. 收集最近的新闻报道\n"
            f"2. 分析新闻情感倾向\n"
            f"3. 评估市场心理和投资者情绪\n"
            f"4. 识别关键事件和影响\n"
            f"用户查询：{query}"
        ),
        expected_output="市场情感分析报告，包含情感评分和关键新闻摘要",
        agent=sentiment_analyst,
        async_execution=True,  # 异步执行
    )
    
    # Task 3: 前瞻性分析（异步，独立执行）
    forward_looking_task = Task(
        description=(
            f"提供 {ticker} 的前瞻性分析：\n"
            f"1. 分析师评级和目标价\n"
            f"2. 上涨/下跌潜力评估\n"
            f"3. 行业趋势和增长前景\n"
            f"4. 风险因素评估\n"
            f"用户查询：{query}"
        ),
        expected_output="前瞻性分析报告，包含评级共识和价格目标",
        agent=forward_looking_analyst,
        async_execution=True,  # 异步执行
    )
    
    # Task 4: 可视化生成（依赖Task 1）
    visualization_task = Task(
        description=(
            f"为 {ticker} 创建数据可视化：\n"
            f"1. 价格走势图\n"
            f"2. 交易量分析\n"
            f"3. 关键指标对比\n"
            f"4. 趋势说明"
        ),
        expected_output="可视化描述和图表数据说明",
        agent=visualization_specialist,
        context=[market_data_task],  # 依赖市场数据任务
        async_execution=False,  # 顺序执行，因为依赖其他任务
    )
    
    # Task 5: 报告生成（依赖所有前面的任务）
    report_task = Task(
        description=(
            f"整合所有分析结果，为 {ticker} 撰写综合投资研究报告：\n"
            f"1. 执行摘要\n"
            f"2. 市场数据分析\n"
            f"3. 情感和新闻分析\n"
            f"4. 前瞻性评估\n"
            f"5. 投资建议\n"
            f"6. 风险提示\n\n"
            f"用户原始查询：{query}"
        ),
        expected_output=(
            "专业的投资研究报告，结构清晰，包含所有关键分析和明确的投资建议"
        ),
        agent=report_writer,
        context=[
            market_data_task,
            sentiment_task,
            forward_looking_task,
            visualization_task
        ],  # 依赖所有前面的任务
        async_execution=False,  # 最后执行
    )
    
    return [
        market_data_task,
        sentiment_task,
        forward_looking_task,
        visualization_task,
        report_task
    ]