# backend/rag/kg_enhancer.py (新文件)
"""
知识图谱增强器 - 清理和丰富提取的图谱
"""
import logging
from typing import Dict, List, Any
from collections import Counter
 
logger = logging.getLogger(__name__)
 
 
class KGEnhancer:
    """知识图谱增强器"""
    
    def __init__(self):
        # 停用词（过滤无用实体）
        self.stopwords = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
            'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was',
            'are', 'were', 'been', 'be', 'have', 'has', 'had', 'do',
            'does', 'did', 'will', 'would', 'should', 'could', 'may',
            'might', 'must', 'can', 'this', 'that', 'these', 'those'
        }
    
    def enhance(self, kg_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        增强知识图谱
        
        1. 清理无效实体
        2. 合并相似实体
        3. 计算重要性分数
        4. 添加统计信息
        """
        logger.info("🔧 Enhancing knowledge graph...")
        
        entities = kg_data.get("entities", [])
        relationships = kg_data.get("relationships", [])
        
        # 1. 清理实体
        cleaned_entities = self._clean_entities(entities)
        
        # 2. 清理关系
        cleaned_relationships = self._clean_relationships(relationships, cleaned_entities)
        
        # 3. 计算实体重要性
        entity_importance = self._calculate_importance(cleaned_entities, cleaned_relationships)
        
        # 4. 添加重要性分数
        for entity in cleaned_entities:
            entity_text = entity["text"]
            entity["importance"] = entity_importance.get(entity_text, 1.0)
        
        # 5. 排序（按重要性）
        cleaned_entities.sort(key=lambda x: x.get("importance", 0), reverse=True)
        
        # 6. 统计信息
        stats = self._calculate_statistics(cleaned_entities, cleaned_relationships)
        
        logger.info(f"✅ Enhanced: {len(cleaned_entities)} entities, {len(cleaned_relationships)} relationships")
        
        return {
            "entities": cleaned_entities,
            "relationships": cleaned_relationships,
            "statistics": stats
        }
    
    def _clean_entities(self, entities: List[Dict]) -> List[Dict]:
        """清理实体"""
        cleaned = []
        
        for entity in entities:
            text = entity.get("text", "").strip()
            
            # 跳过空实体
            if not text:
                continue
            
            # 跳过过短的实体
            if len(text) < 2:
                continue
            
            # 跳过停用词
            if text.lower() in self.stopwords:
                continue
            
            # 跳过纯数字（没有上下文的）
            if text.replace('.', '').replace(',', '').replace('$', '').isdigit() and not entity.get("context"):
                continue
            
            cleaned.append(entity)
        
        return cleaned
    
    def _clean_relationships(self, relationships: List[Dict], valid_entities: List[Dict]) -> List[Dict]:
        """清理关系（确保source和target都存在）"""
        # 创建有效实体集合
        valid_entity_texts = {e["text"] for e in valid_entities}
        
        cleaned = []
        for rel in relationships:
            source = rel.get("source", "").strip()
            target = rel.get("target", "").strip()
            
            # 检查source和target是否在有效实体中
            if source in valid_entity_texts and target in valid_entity_texts:
                cleaned.append(rel)
        
        return cleaned
    
    def _calculate_importance(self, entities: List[Dict], relationships: List[Dict]) -> Dict[str, float]:
        """计算实体重要性（基于连接数）"""
        importance = Counter()
        
        # 统计每个实体在关系中出现的次数
        for rel in relationships:
            source = rel.get("source", "")
            target = rel.get("target", "")
            
            importance[source] += 1
            importance[target] += 1
        
        # 归一化（转换为0-10的分数）
        if importance:
            max_count = max(importance.values())
            return {
                entity: min(10, (count / max_count) * 10)
                for entity, count in importance.items()
            }
        
        return {}
    
    def _calculate_statistics(self, entities: List[Dict], relationships: List[Dict]) -> Dict:
        """计算统计信息"""
        # 实体类型分布
        entity_types = Counter(e.get("type", "UNKNOWN") for e in entities)
        
        # 关系类型分布
        relation_types = Counter(r.get("relation", "unknown") for r in relationships)
        
        # 最重要的实体
        top_entities = sorted(
            entities,
            key=lambda x: x.get("importance", 0),
            reverse=True
        )[:10]
        
        return {
            "total_entities": len(entities),
            "total_relationships": len(relationships),
            "entity_types": dict(entity_types),
            "relation_types": dict(relation_types),
            "top_entities": [
                {
                    "text": e["text"],
                    "type": e["type"],
                    "importance": e.get("importance", 0)
                }
                for e in top_entities
            ]
        }
 
 
# 全局实例
kg_enhancer = KGEnhancer()