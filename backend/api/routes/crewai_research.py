# backend/api/routes/crewai_research.py
"""
CrewAI研究API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
 
from backend.crewai_integration.crews.investment_crew import investment_crew
 
logger = logging.getLogger(__name__)
 
router = APIRouter(prefix="/crewai", tags=["crewai"])
 
 
class CrewAIResearchRequest(BaseModel):
    ticker: str
    query: str
    process_type: Optional[str] = None  # "sequential" or "hierarchical"
 
 
class CrewAIResearchResponse(BaseModel):
    ticker: str
    query: str
    report: str
    process_type: str
    execution_time: float
    timestamp: str
    monitoring: Optional[dict] = None
 
 
@router.post("/research", response_model=CrewAIResearchResponse)
async def crewai_research(request: CrewAIResearchRequest):
    """
    使用CrewAI执行投资研究
    
    支持两种模式：
    - sequential: 任务顺序执行
    - hierarchical: 由管理者协调执行
    """
    try:
        logger.info(f"CrewAI research request: {request.ticker}")
        
        # 设置执行模式
        if request.process_type:
            investment_crew.process_type = request.process_type
        
        # 执行研究
        result = await investment_crew.execute(
            ticker=request.ticker,
            query=request.query
        )
        
        if "error" in result:
            raise HTTPException(status_code=500, detail=result["error"])
        
        return result
        
    except Exception as e:
        logger.error(f"CrewAI research failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/status")
async def get_status():
    """获取CrewAI系统状态"""
    return {
        "status": "online",
        "process_type": investment_crew.process_type,
        "monitoring_enabled": investment_crew.enable_monitoring
    }