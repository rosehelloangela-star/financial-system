# backend/rag/document_processor.py
"""
文档处理器 - 处理PDF和CSV文件
"""
import logging
import PyPDF2
import pandas as pd
from typing import Dict, List, Any
import re
from pathlib import Path
 
logger = logging.getLogger(__name__)
 
 
class DocumentProcessor:
    """文档处理器"""
    
    def __init__(self):
        self.supported_formats = [".pdf", ".csv"]
    
    def process_pdf(self, file_path: str) -> Dict[str, Any]:
        """
        处理PDF文件
        
        Returns:
            {
                "text": str,
                "pages": int,
                "metadata": dict
            }
        """
        try:
            logger.info(f"📄 Processing PDF: {file_path}")
            
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                num_pages = len(pdf_reader.pages)
                
                # 提取所有文本
                text = ""
                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text += page.extract_text() + "\n\n"
                
                # 提取元数据
                metadata = pdf_reader.metadata or {}
                
                logger.info(f"✅ Extracted {len(text)} characters from {num_pages} pages")
                
                return {
                    "text": text,
                    "pages": num_pages,
                    "metadata": {
                        "title": metadata.get('/Title', 'Unknown'),
                        "author": metadata.get('/Author', 'Unknown'),
                        "subject": metadata.get('/Subject', ''),
                        "file_name": Path(file_path).name
                    }
                }
                
        except Exception as e:
            logger.error(f"❌ PDF processing failed: {e}")
            raise
    
    def process_csv(self, file_path: str) -> Dict[str, Any]:
        """
        处理CSV文件
        
        Returns:
            {
                "data": List[Dict],
                "columns": List[str],
                "rows": int,
                "summary": str
            }
        """
        try:
            logger.info(f"📊 Processing CSV: {file_path}")
            
            # 读取CSV
            df = pd.read_csv(file_path)
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 生成摘要文本
            summary = f"CSV File: {Path(file_path).name}\n"
            summary += f"Rows: {len(df)}, Columns: {len(df.columns)}\n\n"
            summary += f"Column Names: {', '.join(df.columns)}\n\n"
            
            # 添加数据预览
            summary += "Data Preview (first 5 rows):\n"
            summary += df.head().to_string()
            
            # 添加统计信息（如果有数值列）
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                summary += "\n\nNumeric Statistics:\n"
                summary += df[numeric_cols].describe().to_string()
            
            logger.info(f"✅ Processed {len(df)} rows, {len(df.columns)} columns")
            
            return {
                "data": data,
                "columns": df.columns.tolist(),
                "rows": len(df),
                "summary": summary,
                "metadata": {
                    "file_name": Path(file_path).name,
                    "num_rows": len(df),
                    "num_columns": len(df.columns)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ CSV processing failed: {e}")
            raise
 
 
document_processor = DocumentProcessor()