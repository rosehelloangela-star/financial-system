# backend/rag/kg_generator.py (修改)
"""
知识图谱生成器主流程
"""
import logging
from pathlib import Path
from typing import Dict
 
from backend.rag.document_processor import document_processor
from backend.rag.kg_extractor import kg_extractor
from backend.rag.kg_visualizer import kg_visualizer
from backend.rag.kg_enhancer import kg_enhancer
 
logger = logging.getLogger(__name__)
 
 
class KnowledgeGraphGenerator:
    """知识图谱生成器"""
    
    def __init__(self):
        self.processor = document_processor
        self.extractor = kg_extractor
        self.visualizer = kg_visualizer
        self.enhancer = kg_enhancer
    
    async def generate_from_file(self, file_path: str) -> Dict:  # 🆕 改为async
        """
        从文件生成知识图谱
        
        Args:
            file_path: PDF或CSV文件路径
        
        Returns:
            {
                "status": "success",
                "file_type": str,
                "entities_count": int,
                "relationships_count": int,
                "output_files": Dict
            }
        """
        logger.info(f"🚀 Starting knowledge graph generation for: {file_path}")
        
        file_path_obj = Path(file_path)
        
        if not file_path_obj.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        file_ext = file_path_obj.suffix.lower()
        
        # 1. 处理文档
        if file_ext == ".pdf":
            doc_data = self.processor.process_pdf(file_path)
            text = doc_data["text"]
            metadata = doc_data["metadata"]
            
            # 2. 🆕 直接await（不用asyncio.run）
            kg_data = await self.extractor.extract_from_text(text)
            
        elif file_ext == ".csv":
            doc_data = self.processor.process_csv(file_path)
            metadata = doc_data["metadata"]
            
            # 2. 🆕 直接await
            kg_data = await self.extractor.extract_from_csv(doc_data["data"])
            
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")
        
        # 3. 增强知识图谱
        enhanced_kg = self.enhancer.enhance(kg_data)
        
        # 4. 可视化和保存
        output_files = self.visualizer.save_graph(
            entities=enhanced_kg["entities"],
            relationships=enhanced_kg["relationships"],
            filename=file_path_obj.stem,
            metadata={
                **metadata,
                "statistics": enhanced_kg.get("statistics", {})
            }
        )
        
        logger.info(f"✅ Knowledge graph generated successfully!")
        
        return {
            "status": "success",
            "file_type": file_ext,
            "entities_count": len(enhanced_kg["entities"]),
            "relationships_count": len(enhanced_kg["relationships"]),
            "statistics": enhanced_kg.get("statistics", {}),
            "output_files": output_files,
            "metadata": metadata
        }
 
 
# 全局实例
kg_generator = KnowledgeGraphGenerator()