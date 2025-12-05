# backend/crewai_integration/crews/investment_crew.py
"""
CrewAI Crew定义 - 投资研究团队
"""
from crewai import Crew, Process
from typing import Dict, Any
import logging
import time
from datetime import datetime
 
from backend.crewai_integration.agents.crewai_agents import (
    market_data_researcher,
    sentiment_analyst,
    forward_looking_analyst,
    visualization_specialist,
    report_writer,
    manager_agent
)
from backend.crewai_integration.tasks.research_tasks import create_research_tasks
from backend.crewai_integration.config.crewai_settings import crewai_settings
from backend.crewai_integration.monitoring.task_monitor import TaskMonitor
 
logger = logging.getLogger(__name__)
 
 
class InvestmentResearchCrew:
    """
    投资研究Crew
    
    支持两种执行模式：
    1. Sequential（顺序）：任务按顺序执行
    2. Hierarchical（层级）：由manager协调任务分配
    """
    
    def __init__(
        self,
        process_type: str = None,
        enable_monitoring: bool = True
    ):
        """
        初始化Crew
        
        Args:
            process_type: 执行模式（sequential或hierarchical）
            enable_monitoring: 是否启用监控
        """
        self.process_type = process_type or crewai_settings.PROCESS_TYPE
        self.enable_monitoring = enable_monitoring and crewai_settings.ENABLE_MONITORING
        self.monitor = TaskMonitor() if self.enable_monitoring else None
    
    def create_crew(self, ticker: str, query: str) -> Crew:
        """
        创建Crew实例
        
        Args:
            ticker: 股票代码
            query: 用户查询
        
        Returns:
            配置好的Crew
        """
        # 创建任务
        tasks = create_research_tasks(ticker, query)
        
        # 根据模式创建Crew
        if self.process_type == "hierarchical":
            logger.info("🏗️  Creating Hierarchical Crew with Manager")
            crew = Crew(
                agents=[
                    market_data_researcher,
                    sentiment_analyst,
                    forward_looking_analyst,
                    visualization_specialist,
                    report_writer
                ],
                tasks=tasks,
                process=Process.hierarchical,
                manager_agent=manager_agent,
                verbose=True
            )
        else:  # sequential
            logger.info("📋 Creating Sequential Crew")
            crew = Crew(
                agents=[
                    market_data_researcher,
                    sentiment_analyst,
                    forward_looking_analyst,
                    visualization_specialist,
                    report_writer
                ],
                tasks=tasks,
                process=Process.sequential,
                verbose=True
            )
        
        return crew
    
    async def execute(
        self,
        ticker: str,
        query: str
    ) -> Dict[str, Any]:
        """
        执行投资研究任务
        
        Args:
            ticker: 股票代码
            query: 用户查询
        
        Returns:
            研究结果
        """
        logger.info(f"🚀 Starting Investment Research Crew for {ticker}")
        logger.info(f"📊 Process Type: {self.process_type}")
        logger.info(f"📝 Query: {query}")
        
        start_time = time.time()
        
        # 创建Crew
        crew = self.create_crew(ticker, query)
        
        # 开始监控
        if self.monitor:
            self.monitor.start_execution(ticker, query)
        
        try:
            # 执行Crew
            logger.info("⚙️  Executing Crew...")
            result = crew.kickoff()
            
            execution_time = time.time() - start_time
            
            # 记录监控数据
            if self.monitor:
                self.monitor.record_task_completion(
                    task_name="crew_execution",
                    success=True,
                    duration=execution_time
                )
            
            logger.info(f"✅ Crew execution completed in {execution_time:.2f}s")
            
            # 构建返回结果
            return {
                "ticker": ticker,
                "query": query,
                "report": str(result),
                "process_type": self.process_type,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
                "monitoring": self.monitor.get_summary() if self.monitor else None
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            logger.error(f"❌ Crew execution failed: {e}")
            
            if self.monitor:
                self.monitor.record_task_completion(
                    task_name="crew_execution",
                    success=False,
                    duration=execution_time,
                    error=str(e)
                )
            
            return {
                "ticker": ticker,
                "query": query,
                "error": str(e),
                "process_type": self.process_type,
                "execution_time": execution_time,
                "timestamp": datetime.utcnow().isoformat(),
                "monitoring": self.monitor.get_summary() if self.monitor else None
            }
 
 
# 全局实例
investment_crew = InvestmentResearchCrew()