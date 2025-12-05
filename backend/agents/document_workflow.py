# backend/agents/document_workflow.py (确保是async)
"""
文档分析工作流 - 整合知识图谱和Agent分析
"""
import logging
from typing import Dict, Any
from datetime import datetime
 
from backend.agents.document_analysis_agent import document_analysis_agent
from backend.agents.state import AgentState
 
logger = logging.getLogger(__name__)
 
 
class DocumentWorkflow:
    """文档分析工作流"""
    
    def __init__(self):
        self.doc_agent = document_analysis_agent
    
    async def analyze_document(  # ✅ 已经是async
        self,
        document_text: str,
        kg_data: Dict,
        metadata: Dict
    ) -> Dict[str, Any]:
        """
        分析文档（完整流程）
        """
        logger.info("🔄 Starting document analysis workflow...")
        
        # 创建初始状态
        state: AgentState = {
            "session_id": f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "user_query": f"Analyze document: {metadata.get('file_name', 'unknown')}",
            "document_text": document_text,
            "kg_data": kg_data,
            "metadata": metadata,
            "tickers": [],
            "executed_agents": [],
            "errors": []
        }
        
        # 执行文档分析Agent
        result_state = await self.doc_agent(state)
        
        # 构建报告
        report = self._build_report(result_state, kg_data, metadata)
        
        return {
            "status": "success",
            "report": report,
            "metadata": {
                "file_name": metadata.get("file_name"),
                "processed_at": datetime.now().isoformat(),
                "entities_count": len(kg_data.get("entities", [])),
                "relationships_count": len(kg_data.get("relationships", []))
            }
        }
    
    def _build_report(
        self,
        state: AgentState,
        kg_data: Dict,
        metadata: Dict
    ) -> str:
        """构建最终报告"""
        
        report = f"""
# 📄 Document Analysis Report
 
**File:** {metadata.get('file_name', 'Unknown')}  
**Processed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**Type:** {metadata.get('file_type', 'Unknown')}
 
---
 
## 📊 Knowledge Graph Statistics
 
- **Entities Extracted:** {len(kg_data.get('entities', []))}
- **Relationships Found:** {len(kg_data.get('relationships', []))}
 
### Top Entities by Importance
"""
        
        # 显示最重要的实体
        entities = kg_data.get("entities", [])
        sorted_entities = sorted(
            entities,
            key=lambda x: x.get("importance", 0),
            reverse=True
        )[:10]
        
        for i, ent in enumerate(sorted_entities, 1):
            importance = ent.get("importance", 0)
            report += f"{i}. **{ent['text']}** ({ent['type']}) - Importance: {importance:.1f}\n"
        
        report += "\n### Entity Types Distribution\n"
        
        # 统计实体类型
        entity_types = {}
        for ent in entities:
            ent_type = ent.get("type", "UNKNOWN")
            entity_types[ent_type] = entity_types.get(ent_type, 0) + 1
        
        for ent_type, count in sorted(entity_types.items(), key=lambda x: x[1], reverse=True):
            report += f"- **{ent_type}:** {count}\n"
        
        report += "\n---\n\n"
        
        # 添加Agent分析
        doc_analysis = state.get("document_analysis", "")
        if doc_analysis:
            report += f"## 🤖 AI Analysis\n\n{doc_analysis}\n\n---\n\n"
        
        # 添加关键关系
        report += "## 🔗 Key Relationships\n\n"
        relationships = kg_data.get("relationships", [])[:15]
        if relationships:
            for i, rel in enumerate(relationships, 1):
                source = rel.get("source", "?")
                target = rel.get("target", "?")
                relation = rel.get("relation", "related_to")
                report += f"{i}. **{source}** --[{relation}]--> **{target}**\n"
        else:
            report += "*No relationships extracted*\n"
        
        report += "\n---\n\n"
        
        # 错误信息
        errors = state.get("errors", [])
        if errors:
            report += "## ⚠️ Warnings\n\n"
            for error in errors:
                report += f"- {error}\n"
        
        return report
 
 
# 全局实例
document_workflow = DocumentWorkflow()