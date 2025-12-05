"""
知识图谱提取器 - 使用LLM进行智能提取
"""
import logging
import json
from typing import Dict, List, Any, Tuple
import aiohttp
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
 
from backend.config.settings import settings
 
logger = logging.getLogger(__name__)


class KnowledgeGraphExtractor:
    """基于LLM的知识图谱提取器"""
    
    def __init__(self):
        # 使用硅基流动API配置
        self.api_url = "https://api.siliconflow.cn/v1/chat/completions"
        self.api_key = settings.siliconflow_api_key
        self.model = settings.siliconflow_model or "Qwen/Qwen2.5-72B-Instruct"
        
        # 定义实体类型（针对金融文档）
        self.entity_types = [
            "COMPANY",       # 公司名称
            "PERSON",        # 人物（CEO、高管）
            "METRIC",        # 财务指标（revenue, profit等）
            "NUMBER",        # 数值
            "DATE",          # 日期
            "PRODUCT",       # 产品/服务
            "LOCATION",      # 地点
            "EVENT",         # 事件（并购、发布等）
        ]
        
        # 定义关系类型
        self.relation_types = [
            "IS_CEO_OF",
            "HAS_REVENUE",
            "ACQUIRED",
            "LAUNCHED",
            "LOCATED_IN",
            "COMPETES_WITH",
            "OWNS",
            "INCREASED_BY",
            "DECREASED_BY",
            "ANNOUNCED"
        ]
    
    async def extract_from_text(self, text: str, chunk_size: int = 3000) -> Dict[str, Any]:
        """
        使用LLM从文本提取知识图谱
        
        Args:
            text: 输入文本
            chunk_size: 分块大小（避免超过token限制）
        
        Returns:
            {
                "entities": List[Dict],
                "relationships": List[Dict]
            }
        """
        logger.info("🧠 Extracting knowledge graph using LLM...")
        
        # 如果文本太长，分块处理
        chunks = self._split_text(text, chunk_size)
        logger.info(f"Split into {len(chunks)} chunks")
        
        all_entities = []
        all_relationships = []
        
        # 并发处理多个块（限制并发数）
        for i in range(0, len(chunks), 3):  # 每次处理3个块
            batch = chunks[i:i+3]
            
            tasks = [self._extract_from_chunk(chunk, idx + i) for idx, chunk in enumerate(batch)]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    logger.error(f"Chunk extraction failed: {result}")
                    continue
                
                all_entities.extend(result["entities"])
                all_relationships.extend(result["relationships"])
        
        # 去重和合并
        entities = self._deduplicate_entities(all_entities)
        relationships = self._deduplicate_relationships(all_relationships)
        
        logger.info(f"✅ Extracted {len(entities)} unique entities, {len(relationships)} unique relationships")
        
        return {
            "entities": entities,
            "relationships": relationships
        }
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError))
    )
    async def _extract_from_chunk(self, text: str, chunk_id: int) -> Dict:
        """从单个文本块提取"""
        
        prompt = f"""
You are a knowledge graph extraction expert for financial documents.

Extract entities and relationships from the following text.

**Entity Types to Extract:**
- COMPANY: Company names
- PERSON: Names of executives, CEOs, etc.
- METRIC: Financial metrics (revenue, profit, EPS, etc.)
- NUMBER: Numerical values with context
- DATE: Dates and time periods
- PRODUCT: Products or services
- LOCATION: Cities, countries, regions
- EVENT: Significant events (acquisitions, launches, etc.)

**Relationship Types to Extract:**
- IS_CEO_OF: Person is CEO of Company
- HAS_REVENUE: Company has revenue of Number
- ACQUIRED: Company acquired Company
- LAUNCHED: Company launched Product
- LOCATED_IN: Company located in Location
- ANNOUNCED: Company announced Event
- INCREASED_BY / DECREASED_BY: Metric changed by Number

**TEXT:**
{text[:2500]}

**OUTPUT FORMAT (JSON):**
{{
  "entities": [
    {{"text": "Apple Inc", "type": "COMPANY"}},
    {{"text": "Tim Cook", "type": "PERSON"}},
    {{"text": "$95.3 billion", "type": "NUMBER", "context": "revenue"}}
  ],
  "relationships": [
    {{"source": "Tim Cook", "target": "Apple Inc", "relation": "IS_CEO_OF"}},
    {{"source": "Apple Inc", "target": "$95.3 billion", "relation": "HAS_REVENUE"}}
  ]
}}

Extract ONLY clear, factual information. Focus on the most important entities and relationships.
Return valid JSON only, no additional text.
"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a knowledge graph extraction expert. Return only valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.1,  # 低温度提高准确性
            "max_tokens": 2000,
            "stream": False,
            "response_format": {"type": "json_object"}  # 强制JSON输出
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.api_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"API request failed: {response.status} - {error_text}")
                        return {"entities": [], "relationships": []}
                    
                    result_data = await response.json()
                    
                    if "choices" not in result_data or not result_data["choices"]:
                        logger.error(f"No choices in response: {result_data}")
                        return {"entities": [], "relationships": []}
                    
                    result_text = result_data["choices"][0]["message"]["content"]
                    result = json.loads(result_text)
                    
                    # 验证格式
                    if "entities" not in result:
                        result["entities"] = []
                    if "relationships" not in result:
                        result["relationships"] = []
                    
                    logger.info(f"Chunk {chunk_id}: {len(result['entities'])} entities, {len(result['relationships'])} relationships")
                    
                    return result
                    
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise
        except asyncio.TimeoutError:
            logger.error("Request timeout")
            return {"entities": [], "relationships": []}
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {"entities": [], "relationships": []}
        except Exception as e:
            logger.error(f"LLM extraction failed: {e}")
            return {"entities": [], "relationships": []}
    
    def _split_text(self, text: str, chunk_size: int) -> List[str]:
        """智能分割文本"""
        # 按段落分割
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            if len(current_chunk) + len(para) < chunk_size:
                current_chunk += para + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _deduplicate_entities(self, entities: List[Dict]) -> List[Dict]:
        """去重实体（基于文本相似度）"""
        seen = {}
        unique = []
        
        for entity in entities:
            text = entity.get("text", "").strip().lower()
            entity_type = entity.get("type", "")
            
            if not text:
                continue
            
            # 使用 (text, type) 作为键
            key = (text, entity_type)
            
            if key not in seen:
                seen[key] = True
                # 保留原始格式
                unique.append({
                    "text": entity.get("text", "").strip(),
                    "type": entity_type,
                    "context": entity.get("context", "")
                })
        
        return unique
    
    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """去重关系"""
        seen = set()
        unique = []
        
        for rel in relationships:
            source = rel.get("source", "").strip().lower()
            target = rel.get("target", "").strip().lower()
            relation = rel.get("relation", "").strip()
            
            if not source or not target or not relation:
                continue
            
            key = (source, relation, target)
            
            if key not in seen:
                seen.add(key)
                unique.append({
                    "source": rel.get("source", "").strip(),
                    "target": rel.get("target", "").strip(),
                    "relation": relation,
                    "context": rel.get("context", "")
                })
        
        return unique
    
    async def extract_from_csv(self, csv_data: List[Dict]) -> Dict:
        """
        使用LLM从CSV提取知识图谱
        """
        logger.info("📊 Extracting knowledge graph from CSV using LLM...")
        
        # 将CSV转换为自然语言描述
        text_description = self._csv_to_text(csv_data)
        
        # 使用LLM提取
        result = await self.extract_from_text(text_description)
        
        # 额外提取列之间的关系
        csv_relationships = self._extract_csv_column_relationships(csv_data)
        result["relationships"].extend(csv_relationships)
        
        return result
    
    def _csv_to_text(self, csv_data: List[Dict], max_rows: int = 50) -> str:
        """将CSV转换为文本描述"""
        if not csv_data:
            return ""
        
        text = "CSV Data Analysis:\n\n"
        
        # 限制行数
        sample_data = csv_data[:max_rows]
        
        # 列名
        columns = list(sample_data[0].keys()) if sample_data else []
        text += f"Columns: {', '.join(columns)}\n\n"
        
        # 转换每行为句子
        for i, row in enumerate(sample_data):
            row_text = f"Row {i+1}: "
            facts = []
            for key, value in row.items():
                if value and str(value).strip():
                    facts.append(f"{key} is {value}")
            
            if facts:
                row_text += ", ".join(facts) + "."
                text += row_text + "\n"
        
        return text
    
    def _extract_csv_column_relationships(self, csv_data: List[Dict]) -> List[Dict]:
        """从CSV列提取关系"""
        if not csv_data:
            return []
        
        relationships = []
        columns = list(csv_data[0].keys())
        
        # 为每一行创建列之间的关系
        for row in csv_data[:20]:  # 限制行数
            # 找到主键列（通常是第一列或包含name/id的列）
            primary_key = None
            for col in columns:
                if 'name' in col.lower() or 'company' in col.lower() or 'id' in col.lower():
                    primary_key = col
                    break
            
            if not primary_key:
                primary_key = columns[0]
            
            primary_value = row.get(primary_key)
            if not primary_value:
                continue
            
            # 创建关系
            for col in columns:
                if col != primary_key and row.get(col):
                    relationships.append({
                        "source": str(primary_value),
                        "target": str(row[col]),
                        "relation": f"HAS_{col.upper()}",
                        "context": f"CSV column relationship"
                    })
        
        return relationships


# 全局实例
kg_extractor = KnowledgeGraphExtractor()