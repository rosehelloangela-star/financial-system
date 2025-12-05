"""
LangGraph workflow definition for multi-agent research system.
Uses LangGraph 1.0+ API with parallel execution support.
"""
import logging
from langgraph.graph import StateGraph
from langgraph.constants import START, END
from langgraph.types import Send
from typing import Literal
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough
from langchain_openai import ChatOpenAI  # 新增导入

from backend.agents.state import AgentState, create_initial_state
from backend.agents.router_agent import router_agent
from backend.agents.market_data_agent import market_data_agent
from backend.agents.sentiment_agent import sentiment_agent
from backend.agents.forward_looking_agent import forward_looking_agent
from backend.agents.visualization_agent import visualization_agent
from backend.agents.report_agent import report_agent
from backend.rag.pipeline import rag_pipeline
from backend.memory.conversation import conversation_memory
from backend.config.settings import settings  # 修改导入方式

logger = logging.getLogger(__name__)

# 使用settings中的配置初始化LLM
llm = ChatOpenAI(
    model=settings.openai_model,
    api_key=settings.openai_api_key,
    temperature=0
)

# ================== 三条LangChain链的定义（使用LCEL方式） ==================

# 链1: 输入验证链 - 使用LCEL
validation_prompt = ChatPromptTemplate.from_template("""
请验证以下投资研究查询的合理性。查询: "{query}"

请分析：
1. 是否包含明确的投资研究相关问题
2. 是否包含股票代码或公司名称
3. 查询意图是否清晰

只需回复"VALID"（有效）或"INVALID"（无效），不要额外解释。
""")

validation_chain = (
    {"query": RunnablePassthrough()} 
    | validation_prompt 
    | llm 
    | RunnableLambda(lambda x: x.content.strip())
    | RunnableLambda(lambda x: {"validation_result": x, "is_query_valid": x == "VALID"})
)

# 链2: 查询优化链 - 使用LCEL
query_optimization_prompt = ChatPromptTemplate.from_template("""
优化以下投资研究查询，使其更专业和明确：

原始查询: "{query}"
识别的股票代码: {tickers}

请提供一个更专业、更具体的优化版本，用于投资研究分析。
只需返回优化后的查询，不要额外解释。
""")

query_optimization_chain = (
    {"query": RunnablePassthrough(), "tickers": RunnablePassthrough()}
    | query_optimization_prompt
    | llm
    | RunnableLambda(lambda x: x.content.strip())
    | RunnableLambda(lambda x: {"optimized_query": x, "final_query": x})
)

# 链3: 报告质量检查链 - 使用LCEL
quality_check_prompt = ChatPromptTemplate.from_template("""
检查以下投资研究报告的质量：

用户原始查询: "{original_query}"
生成的研究报告: "{report}"

请评估报告是否：
1. 完整回答了查询问题
2. 包含必要的财务数据和分析
3. 结构清晰专业

只需回复"PASS"（通过）或"FAIL"（不通过），不要额外解释。
""")

quality_check_chain = (
    {"original_query": RunnablePassthrough(), "report": RunnablePassthrough()}
    | quality_check_prompt
    | llm
    | RunnableLambda(lambda x: x.content.strip())
    | RunnableLambda(lambda x: {"quality_check_result": x, "is_quality_passed": x == "PASS"})
)

# ================== 三个新的节点函数（使用LCEL链） ==================

async def validation_node(state: AgentState) -> AgentState:
    """
    使用LCEL链验证输入查询的合理性
    """
    query = state.get("user_query", "")
    
    if not query:
        return {
            "validation_result": "INVALID",
            "validation_reason": "Empty query",
            "is_query_valid": False
        }
    
    try:
        result = await validation_chain.ainvoke(query)
        logger.info(f"Input validation result: {result.get('validation_result')}")
        return result
        
    except Exception as e:
        logger.error(f"Validation chain failed: {e}")
        return {
            "validation_result": "INVALID",
            "validation_reason": f"Validation error: {str(e)}",
            "is_query_valid": False
        }


async def query_optimization_node(state: AgentState) -> AgentState:
    """
    使用LCEL链优化用户查询
    """
    query = state.get("user_query", "")
    tickers = state.get("tickers", [])
    
    # 只有在查询有效时才进行优化
    if not state.get("is_query_valid", False):
        logger.info("Query is invalid, skipping optimization")
        return {"optimized_query": query, "final_query": query}
    
    try:
        result = await query_optimization_chain.ainvoke({"query": query, "tickers": tickers})
        logger.info(f"Query optimized: '{query}' -> '{result.get('optimized_query')}'")
        return result
        
    except Exception as e:
        logger.error(f"Query optimization chain failed: {e}")
        # 出错时使用原查询
        return {
            "optimized_query": query,
            "final_query": query
        }


async def quality_check_node(state: AgentState) -> AgentState:
    """
    使用LCEL链检查最终报告质量
    """
    original_query = state.get("user_query", "")
    report = state.get("report", "")
    
    if not report:
        logger.warning("No report to quality check")
        return {
            "quality_check_result": "FAIL",
            "quality_reason": "No report generated",
            "is_quality_passed": False
        }
    
    try:
        result = await quality_check_chain.ainvoke({
            "original_query": original_query, 
            "report": report
        })
        logger.info(f"Report quality check: {result.get('quality_check_result')}")
        return result
        
    except Exception as e:
        logger.error(f"Quality check chain failed: {e}")
        return {
            "quality_check_result": "FAIL",
            "quality_reason": f"Quality check error: {str(e)}",
            "is_quality_passed": False
        }


# ================== 原有的辅助节点函数（保持不变） ==================

async def memory_loader(state: AgentState) -> AgentState:
    """
    Load conversation history from MongoDB.

    Args:
        state: Current state

    Returns:
        State with conversation history loaded
    """
    session_id = state.get("session_id")

    try:
        # Load conversation history (returns empty list if session doesn't exist)
        messages = await conversation_memory.get_conversation(session_id, limit=10)

        logger.info(f"Loaded {len(messages)} historical messages for session {session_id}")

        # Only update if we got messages, otherwise keep existing (empty) history
        if messages:
            return {"conversation_history": messages}
        else:
            return {}  # No updates needed

    except Exception as e:
        logger.warning(f"Failed to load conversation history: {e}")
        return {}  # Return empty dict, no updates


async def rag_retrieval(state: AgentState) -> AgentState:
    """
    Retrieve relevant documents from RAG pipeline.

    Args:
        state: Current state

    Returns:
        State with retrieved_context populated
    """
    # 使用优化后的查询（如果存在），否则使用原查询
    query = state.get("final_query", state.get("user_query", ""))
    tickers = state.get("tickers", [])

    if not query:
        logger.warning("No query specified, skipping RAG retrieval")
        return {
            "retrieved_context": [],
            "executed_agents": ["rag_retrieval"]
        }

    try:
        # Retrieve context with or without ticker
        # If tickers present, use first one for metadata filtering
        # Otherwise, rely on semantic search across all documents
        ticker = tickers[0] if tickers else None

        if ticker:
            logger.info(f"Retrieving context for ticker: {ticker}")
            results = await rag_pipeline.retrieve_context(
                query=query,
                ticker=ticker,
                top_k=5
            )
        else:
            logger.info("No tickers specified, using semantic search across all documents")
            results = await rag_pipeline.retrieve_context(
                query=query,
                top_k=5
            )

        # Convert to RetrievedContext format
        retrieved = []
        for r in results:
            retrieved.append({
                "text": r.get("text", ""),
                "source": r.get("metadata", {}).get("source", "unknown"),
                "ticker": r.get("metadata", {}).get("ticker", ticker or "N/A"),
                "similarity": r.get("similarity", 0.0),
                "metadata": r.get("metadata", {})
            })

        logger.info(f"Retrieved {len(retrieved)} context documents")

        # Return only the field we're updating (for parallel execution)
        return {
            "retrieved_context": retrieved,
            "executed_agents": ["rag_retrieval"]
        }

    except Exception as e:
        logger.error(f"RAG retrieval failed: {e}")
        # Track error (use dict for operator.or_ merging)
        return {
            "retrieved_context": [],
            "executed_agents": ["rag_retrieval"],
            "agent_errors": {"rag_retrieval": str(e)},
            "errors": [f"rag_retrieval error: {str(e)}"]
        }


async def memory_saver(state: AgentState) -> AgentState:
    """
    Save final report to conversation history.

    Args:
        state: Current state with report

    Returns:
        Empty dict (no state updates needed)
    """
    session_id = state.get("session_id")
    report = state.get("report")

    if not report:
        logger.warning("No report to save")
        return {}

    try:
        # Save user query
        await conversation_memory.save_message(
            session_id, "user", state.get("user_query", "")
        )

        # Save assistant response
        await conversation_memory.save_message(
            session_id, "assistant", report
        )

        logger.info(f"Saved conversation to session {session_id}")

    except Exception as e:
        logger.error(f"Failed to save conversation: {e}")

    return {}  # No state updates needed


# ================== 原有的路由逻辑（稍作修改） ==================

def route_to_agents(state: AgentState) -> list[Send]:
    """
    Dynamic router that sends to multiple agents in parallel.

    Uses LangGraph 1.0+ Send API for parallel execution.
    Each agent should be sent to exactly once to avoid concurrent updates.

    Args:
        state: Current state after router analysis

    Returns:
        List of Send objects for parallel execution
    """
    sends = []
    sent_to = set()  # Track which agents we've already queued
    tickers = state.get("tickers", [])
    has_tickers = bool(tickers)

    # 如果查询无效，跳过所有代理执行
    if not state.get("is_query_valid", True):
        logger.warning("Query is invalid, skipping agent execution")
        return sends

    # Get explicit routing flags from router
    should_fetch_market = state.get("should_fetch_market_data", False)
    should_analyze_sentiment = state.get("should_analyze_sentiment", False)
    should_retrieve_context = state.get("should_retrieve_context", False)

    # 1. RAG retrieval - only if explicitly enabled by router
    if should_retrieve_context:
        sends.append(Send("rag_retrieval", state))
        sent_to.add("rag_retrieval")
        logger.debug("RAG retrieval: explicitly enabled by router")
    elif not has_tickers:
        # Fallback: if no tickers found, use RAG for semantic search
        sends.append(Send("rag_retrieval", state))
        sent_to.add("rag_retrieval")
        logger.debug("RAG retrieval: fallback (no tickers found)")

    # 2. Market data agent - only if has tickers and router enabled
    if should_fetch_market and has_tickers:
        sends.append(Send("market_data", state))
        sent_to.add("market_data")
        logger.debug("Market data agent: enabled by router")

    # 3. Sentiment agent - only if has tickers and router enabled
    if should_analyze_sentiment and has_tickers:
        sends.append(Send("sentiment", state))
        sent_to.add("sentiment")
        logger.debug("Sentiment agent: enabled by router")

    # 4. Forward-looking agent - run if market data is being fetched
    #    (needs market data for analyst consensus and forward guidance)
    if should_fetch_market and has_tickers:
        sends.append(Send("forward_looking", state))
        sent_to.add("forward_looking")
        logger.debug("Forward-looking agent: enabled (market data requested)")

    # NOTE: visualization is NOT in parallel execution
    # It runs after aggregator to access peer_valuation data from market_data_agent

    # Fallback: if router didn't enable any agents but we have tickers,
    # default to comprehensive research (market + sentiment)
    if has_tickers and not should_fetch_market and not should_analyze_sentiment:
        logger.debug("No agents explicitly enabled, using fallback: market + sentiment")
        if "market_data" not in sent_to:
            sends.append(Send("market_data", state))
            sent_to.add("market_data")
        if "sentiment" not in sent_to:
            sends.append(Send("sentiment", state))
            sent_to.add("sentiment")
        if "forward_looking" not in sent_to:
            sends.append(Send("forward_looking", state))
            sent_to.add("forward_looking")

    logger.info(f"Routing to {len(sent_to)} agents in parallel: {sent_to}")

    return sends


def aggregate_results(state: AgentState) -> AgentState:
    """
    Aggregates results from parallel agent execution.

    This node collects all outputs before sending to visualization and report generator.

    Args:
        state: State with partial results from parallel agents

    Returns:
        Empty dict (no state updates, just synchronization point)
    """
    logger.info("Aggregating results from parallel agents")

    # Log what we have
    has_market = state.get("market_data") is not None
    has_sentiment = state.get("sentiment_analysis") is not None
    has_context = state.get("retrieved_context") is not None
    has_analyst = state.get("analyst_consensus") is not None
    has_peer = state.get("peer_valuation") is not None

    logger.info(
        f"Results: market_data={has_market}, "
        f"sentiment={has_sentiment}, analyst_consensus={has_analyst}, "
        f"context={has_context}, peer_valuation={has_peer}"
    )

    return {}  # No state updates, just a synchronization point


# ================== 图构建函数（保持不变） ==================

def create_research_graph():
    """
    Create the LangGraph workflow for investment research.

    新的流程：
        START
          ↓
        validation (LangChain LCEL链1 - 输入验证)
          ↓
        query_optimization (LangChain LCEL链2 - 查询优化)  
          ↓
        memory_loader
          ↓
        router
          ↓
        [parallel: market_data, sentiment, forward_looking, rag_retrieval]
          ↓
        aggregator
          ↓
        visualization (sequential - needs peer_valuation from market_data)
          ↓
        report
          ↓
        quality_check (LangChain LCEL链3 - 质量检查)
          ↓
        memory_saver
          ↓
        END

    Returns:
        Compiled StateGraph
    """
    # Create graph with AgentState
    workflow = StateGraph(AgentState)

    # 添加三个新的LangChain LCEL链节点
    workflow.add_node("validation", validation_node)
    workflow.add_node("query_optimization", query_optimization_node)
    workflow.add_node("quality_check", quality_check_node)

    # 添加原有节点
    workflow.add_node("memory_loader", memory_loader)
    workflow.add_node("router", router_agent)
    workflow.add_node("market_data", market_data_agent)
    workflow.add_node("sentiment", sentiment_agent)
    workflow.add_node("forward_looking", forward_looking_agent)
    workflow.add_node("visualization", visualization_agent)
    workflow.add_node("rag_retrieval", rag_retrieval)
    workflow.add_node("aggregator", aggregate_results)
    workflow.add_node("report", report_agent)
    workflow.add_node("memory_saver", memory_saver)

    # 定义新的边（包含三个LangChain LCEL链节点）
    workflow.add_edge(START, "validation")
    workflow.add_edge("validation", "query_optimization")
    workflow.add_edge("query_optimization", "memory_loader")
    workflow.add_edge("memory_loader", "router")

    # Conditional parallel routing (visualization is NOT included here)
    workflow.add_conditional_edges(
        "router",
        route_to_agents,
        ["market_data", "sentiment", "forward_looking", "rag_retrieval"]
    )

    # All parallel paths converge to aggregator
    workflow.add_edge("market_data", "aggregator")
    workflow.add_edge("sentiment", "aggregator")
    workflow.add_edge("forward_looking", "aggregator")
    workflow.add_edge("rag_retrieval", "aggregator")

    # Sequential flow after aggregation
    workflow.add_edge("aggregator", "visualization")
    workflow.add_edge("visualization", "report")
    workflow.add_edge("report", "quality_check")  # 新增质量检查
    workflow.add_edge("quality_check", "memory_saver")
    workflow.add_edge("memory_saver", END)

    # Compile the graph
    return workflow.compile()


# Create singleton instance
research_graph = create_research_graph()


# ================== 原有的便利函数（保持不变） ==================

async def run_research_query(
    session_id: str,
    user_query: str
) -> AgentState:
    """
    Run a research query through the complete agent workflow.

    Args:
        session_id: Unique session identifier
        user_query: User's research question

    Returns:
        Final AgentState with report
    """
    logger.info(f"Starting research query: {user_query[:50]}...")

    # Create initial state
    initial_state = create_initial_state(session_id, user_query)

    # Run the graph
    final_state = await research_graph.ainvoke(initial_state)

    logger.info("Research query completed")

    return final_state