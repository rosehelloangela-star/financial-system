# backend/agents/document_analysis_agent.py
"""
文档分析Agent - 分析上传的PDF/CSV文档
"""
import logging
import aiohttp
from typing import Dict, Any
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential

from backend.agents.base_agent import BaseAgent
from backend.agents.state import AgentState
from backend.config.settings import settings

logger = logging.getLogger(__name__)


class DocumentAnalysisAgent(BaseAgent):
    """
    文档分析Agent
    
    功能：
    1. 分析文档内容
    2. 提取关键信息
    3. 生成摘要和洞察
    """
    
    def __init__(self):
        super().__init__("document_analysis")
        # 硅基流动API配置
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.api_key = settings.siliconflow_api_key  # 需要在settings中添加配置
        self.model = "Qwen/Qwen2.5-72B-Instruct"  # 或者您选择的模型
        
    async def execute(self, state: AgentState) -> AgentState:
        """分析文档"""
        document_text = state.get("document_text", "")
        kg_data = state.get("kg_data", {})
        
        if not document_text:
            self.logger.warning("No document text to analyze")
            return state
        
        self._add_reasoning_step("Starting document analysis")
        
        try:
            # 生成文档分析
            analysis = await self._analyze_document(document_text, kg_data)
            
            self._add_reasoning_step(f"Generated document analysis with {len(analysis)} characters")
            
            return {
                "document_analysis": analysis
            }
            
        except Exception as e:
            self.logger.error(f"Document analysis failed: {e}")
            return {
                "document_analysis": "",
                "errors": [f"Document analysis error: {str(e)}"]
            }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def _analyze_document(self, text: str, kg_data: Dict) -> str:
        """使用硅基流动API分析文档"""
        
        # 构建提示
        entities_summary = self._summarize_entities(kg_data.get("entities", []))
        relationships_summary = self._summarize_relationships(kg_data.get("relationships", []))
        
        prompt = f"""
You are a financial document analyst. Analyze the following document and provide insights.

DOCUMENT CONTENT (first 4000 characters):
{text[:4000]}

EXTRACTED KNOWLEDGE GRAPH:
Entities: {entities_summary}
Relationships: {relationships_summary}

Please provide:
1. **Document Summary** - What is this document about?
2. **Key Findings** - What are the most important points?
3. **Financial Metrics** - Extract any financial numbers and their context
4. **Entities Mentioned** - Companies, people, dates, locations
5. **Insights** - What insights can be drawn from this document?
6. **Recommendations** - Any actionable recommendations

Format your response in clear markdown with headers.
"""
        
        # 准备请求数据
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are an expert financial analyst specializing in document analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "stream": False,
            "max_tokens": 4096,
            "enable_thinking": False,
            "thinking_budget": 4096,
            "min_p": 0.05,
            "stop": [],
            "temperature": 0.3,  # 降低temperature以获得更确定性的分析
            "top_p": 0.9,
            "top_k": 50,
            "frequency_penalty": 0.1,
            "n": 1,
            "response_format": { "type": "text" }
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            # 使用aiohttp发送异步请求
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)  # 设置60秒超时
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        self.logger.error(f"API request failed: {response.status} - {error_text}")
                        return f"API request failed with status {response.status}"
                    
                    result = await response.json()
                    
                    if "choices" not in result or not result["choices"]:
                        self.logger.error(f"No choices in response: {result}")
                        return "Failed to generate analysis: invalid response format"
                    
                    analysis = result["choices"][0]["message"]["content"]
                    return analysis
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"HTTP client error: {e}")
            raise
        except asyncio.TimeoutError:
            self.logger.error("Request timeout")
            return "Analysis timeout: request took too long"
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            raise
    
    def _summarize_entities(self, entities: list) -> str:
        """总结实体"""
        if not entities:
            return "None found"
        
        entity_types = {}
        for ent in entities[:50]:  # 限制数量
            ent_type = ent.get("type", "UNKNOWN")
            if ent_type not in entity_types:
                entity_types[ent_type] = []
            entity_types[ent_type].append(ent.get("text", ""))
        
        summary = []
        for ent_type, items in entity_types.items():
            summary.append(f"{ent_type}: {', '.join(items[:5])}")
        
        return "; ".join(summary)
    
    def _summarize_relationships(self, relationships: list) -> str:
        """总结关系"""
        if not relationships:
            return "None found"
        
        relation_types = {}
        for rel in relationships[:30]:
            rel_type = rel.get("relation", "unknown")
            if rel_type not in relation_types:
                relation_types[rel_type] = 0
            relation_types[rel_type] += 1
        
        summary = [f"{rel}: {count}" for rel, count in relation_types.items()]
        return ", ".join(summary)


# 创建实例
document_analysis_agent = DocumentAnalysisAgent()