# backend/crewai_integration/agents/crewai_agents.py
"""
CrewAI Agent定义 - 将现有Agent包装为CrewAI Agent
"""
from crewai import Agent
from langchain_openai import ChatOpenAI
import logging
 
from backend.crewai_integration.config.crewai_settings import crewai_settings
from backend.crewai_integration.tools.financial_tools import (
    get_stock_price_tool,
    get_historical_data_tool,
    get_fundamentals_tool,
    analyze_sentiment_tool,
    search_news_tool,
    get_analyst_ratings_tool,
    generate_chart_tool
)
 
logger = logging.getLogger(__name__)
 
 
def create_llm(temperature: float = 0.7, model: str = None):
    """创建LLM实例"""
    return ChatOpenAI(
        model=model or crewai_settings.DEFAULT_LLM_MODEL,
        temperature=temperature,
        api_key=crewai_settings.OPENAI_API_KEY
    )
 
 
# ========== Agent定义 ==========
 
market_data_researcher = Agent(
    role="市场数据研究员",
    goal="收集和分析股票的实时市场数据、价格趋势和交易量信息",
    backstory=(
        "你是一位经验丰富的金融数据分析师，专注于实时市场数据分析。"
        "你擅长从各种数据源获取准确的价格信息，并识别市场趋势。"
    ),
    tools=[
        get_stock_price_tool,
        get_historical_data_tool,
        get_fundamentals_tool
    ],
    llm=create_llm(temperature=0.3),
    verbose=True,
    allow_delegation=False  # 专注于数据收集，不委托
)
 
sentiment_analyst = Agent(
    role="情感分析师",
    goal="分析新闻、社交媒体和市场情绪，评估投资者对股票的态度",
    backstory=(
        "你是一位情感分析专家，能够从新闻标题、文章内容和社交媒体中"
        "准确判断市场情绪。你的分析帮助投资者理解市场心理。"
    ),
    tools=[
        analyze_sentiment_tool,
        search_news_tool
    ],
    llm=create_llm(temperature=0.5),
    verbose=True,
    allow_delegation=False
)
 
forward_looking_analyst = Agent(
    role="前瞻性分析师",
    goal="提供股票的未来展望、分析师评级和价格目标预测",
    backstory=(
        "你是一位资深的投资分析师，专注于预测分析和估值模型。"
        "你整合各种分析师观点，提供综合性的前瞻性建议。"
    ),
    tools=[
        get_analyst_ratings_tool,
        get_fundamentals_tool
    ],
    llm=create_llm(temperature=0.6),
    verbose=True,
    allow_delegation=False
)
 
visualization_specialist = Agent(
    role="数据可视化专家",
    goal="创建清晰、有洞察力的图表和可视化，帮助理解复杂的金融数据",
    backstory=(
        "你是一位数据可视化大师，能够将复杂的金融数据转化为"
        "易于理解的图表。你的可视化帮助投资者快速把握关键信息。"
    ),
    tools=[
        generate_chart_tool,
        get_historical_data_tool
    ],
    llm=create_llm(temperature=0.4),
    verbose=True,
    allow_delegation=False
)
 
report_writer = Agent(
    role="投资报告撰写者",
    goal="整合所有分析结果，撰写全面、专业的投资研究报告",
    backstory=(
        "你是一位经验丰富的金融作家，擅长将复杂的分析转化为"
        "清晰、可操作的投资建议。你的报告受到机构投资者的信赖。"
    ),
    tools=[],  # 报告撰写者主要整合其他agent的结果
    llm=create_llm(temperature=0.7),
    verbose=True,
    allow_delegation=True  # 可以委托其他agent获取额外信息
)
 
# Hierarchical模式的管理者
manager_agent = Agent(
    role="投资研究主管",
    goal="协调整个研究团队，确保高质量的投资分析报告按时交付",
    backstory=(
        "你是一位资深的投资研究主管，管理着一个专业的分析师团队。"
        "你擅长任务分配、进度管理和质量控制。"
    ),
    tools=[],
    llm=create_llm(
        temperature=crewai_settings.MANAGER_TEMPERATURE,
        model=crewai_settings.MANAGER_LLM
    ),
    verbose=True,
    allow_delegation=True
)