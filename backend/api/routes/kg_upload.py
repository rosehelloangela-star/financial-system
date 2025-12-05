# backend/api/routes/kg_upload.py (完全替换)
"""
知识图谱上传API - 增强版
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import shutil
from pathlib import Path
import logging
from typing import Optional
 
from backend.rag.kg_generator import kg_generator
from backend.agents.document_workflow import document_workflow
from backend.rag.document_processor import document_processor
 
logger = logging.getLogger(__name__)
 
router = APIRouter(prefix="/kg", tags=["knowledge-graph"])
 
# 上传目录
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
 
# 报告目录
REPORTS_DIR = Path("document_reports")
REPORTS_DIR.mkdir(exist_ok=True)
 
 
# backend/api/routes/kg_upload.py (修改upload_and_analyze函数)
 
@router.post("/upload")
async def upload_and_analyze(
    file: UploadFile = File(...),
    generate_report: bool = True,
    generate_kg: bool = True
):
    """
    🆕 增强版：上传文件并生成知识图谱 + AI分析报告
    """
    try:
        # 验证文件类型
        if not file.filename.endswith(('.pdf', '.csv')):
            raise HTTPException(
                status_code=400,
                detail="Only PDF and CSV files are supported"
            )
        
        logger.info(f"📤 Processing file: {file.filename}")
        
        # 保存上传文件
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        result = {
            "filename": file.filename,
            "file_path": str(file_path)
        }
        
        # 1. 生成知识图谱
        kg_result = None
        if generate_kg:
            logger.info("🏗️ Generating knowledge graph...")
            # 🆕 直接await（不用asyncio.run）
            kg_result = await kg_generator.generate_from_file(str(file_path))
            result["knowledge_graph"] = kg_result
        
        # 2. 生成AI分析报告
        analysis_result = None
        if generate_report:
            logger.info("🤖 Generating AI analysis report...")
            
            # 提取文档内容
            if file.filename.endswith('.pdf'):
                doc_data = document_processor.process_pdf(str(file_path))
                document_text = doc_data["text"]
                metadata = doc_data["metadata"]
            else:  # CSV
                doc_data = document_processor.process_csv(str(file_path))
                document_text = doc_data["summary"]
                metadata = doc_data["metadata"]
            
            # 获取知识图谱数据（如果生成了）
            kg_data = {}
            if kg_result:
                import json
                json_path = kg_result["output_files"]["json_path"]
                with open(json_path, 'r') as f:
                    kg_json = json.load(f)
                    kg_data = {
                        "entities": kg_json.get("entities", []),
                        "relationships": kg_json.get("relationships", [])
                    }
            
            # 运行分析工作流
            analysis_result = await document_workflow.analyze_document(
                document_text=document_text,
                kg_data=kg_data,
                metadata=metadata
            )
            
            # 保存报告
            report_path = REPORTS_DIR / f"{Path(file.filename).stem}_report.md"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(analysis_result["report"])
            
            analysis_result["report_path"] = str(report_path)
            result["analysis_report"] = analysis_result
        
        # 3. 整理输出文件
        result["files"] = {}
        if kg_result:
            result["files"]["html"] = kg_result["output_files"]["html_path"]
            result["files"]["json"] = kg_result["output_files"]["json_path"]
            result["files"]["graphml"] = kg_result["output_files"]["graphml_path"]
        if analysis_result:
            result["files"]["report"] = analysis_result["report_path"]
        
        logger.info(f"✅ Processing complete for {file.filename}")
        
        return {
            "status": "success",
            "message": "File processed successfully",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"❌ Processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.post("/upload-quick")
async def upload_quick_analysis(file: UploadFile = File(...)):
    """快速分析（仅AI报告，不生成知识图谱）"""
    return await upload_and_analyze(file, generate_report=True, generate_kg=False)
 
 
@router.post("/upload-kg-only")
async def upload_kg_only(file: UploadFile = File(...)):
    """仅生成知识图谱（不生成AI报告）"""
    return await upload_and_analyze(file, generate_report=False, generate_kg=True)
 
 
@router.get("/download/{filename}")
async def download_file(filename: str, type: str = "html"):
    """
    下载生成的文件
    
    Args:
        filename: 原始文件名（不含扩展名）
        type: 文件类型 (html, json, graphml, report)
    """
    try:
        if type == "report":
            # 下载分析报告
            report_path = REPORTS_DIR / f"{filename}_report.md"
            if not report_path.exists():
                raise HTTPException(status_code=404, detail="Report not found")
            
            return FileResponse(
                path=report_path,
                filename=f"{filename}_report.md",
                media_type="text/markdown"
            )
        else:
            # 下载知识图谱文件
            kg_dir = Path("knowledge_graphs")
            pattern = f"{filename}_*.{type}"
            files = list(kg_dir.glob(pattern))
            
            if not files:
                raise HTTPException(
                    status_code=404,
                    detail=f"No {type} file found"
                )
            
            latest_file = max(files, key=lambda p: p.stat().st_mtime)
            
            return FileResponse(
                path=latest_file,
                filename=latest_file.name
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Download failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/list")
async def list_all_documents():
    """列出所有已处理的文档"""
    try:
        documents = []
        
        # 从知识图谱目录读取
        kg_dir = Path("knowledge_graphs")
        for json_file in kg_dir.glob("*.json"):
            import json
            with open(json_file, 'r') as f:
                data = json.load(f)
                
                file_stem = json_file.stem.rsplit('_', 2)[0]  # 移除时间戳
                
                # 检查是否有分析报告
                report_path = REPORTS_DIR / f"{file_stem}_report.md"
                has_report = report_path.exists()
                
                documents.append({
                    "filename": file_stem,
                    "created_at": data.get("created_at"),
                    "entities": data.get("stats", {}).get("num_entities"),
                    "relationships": data.get("stats", {}).get("num_relationships"),
                    "has_kg": True,
                    "has_report": has_report,
                    "files": {
                        "json": str(json_file),
                        "html": str(json_file.with_suffix('.html')),
                        "report": str(report_path) if has_report else None
                    }
                })
        
        return {
            "count": len(documents),
            "documents": documents
        }
        
    except Exception as e:
        logger.error(f"❌ List failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.get("/report/{filename}")
async def get_report(filename: str):
    """
    获取分析报告内容（返回Markdown）
    """
    try:
        report_path = REPORTS_DIR / f"{filename}_report.md"
        
        if not report_path.exists():
            raise HTTPException(status_code=404, detail="Report not found")
        
        with open(report_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return {
            "filename": filename,
            "content": content,
            "path": str(report_path)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Get report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
 
 
@router.delete("/delete/{filename}")
async def delete_document(filename: str):
    """
    删除文档及其所有相关文件
    """
    try:
        deleted_files = []
        
        # 删除上传的原始文件
        upload_file = UPLOAD_DIR / filename
        if upload_file.exists():
            upload_file.unlink()
            deleted_files.append(str(upload_file))
        
        # 删除知识图谱文件
        kg_dir = Path("knowledge_graphs")
        file_stem = Path(filename).stem
        for kg_file in kg_dir.glob(f"{file_stem}_*"):
            kg_file.unlink()
            deleted_files.append(str(kg_file))
        
        # 删除分析报告
        report_file = REPORTS_DIR / f"{file_stem}_report.md"
        if report_file.exists():
            report_file.unlink()
            deleted_files.append(str(report_file))
        
        return {
            "status": "success",
            "message": f"Deleted {len(deleted_files)} files",
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        logger.error(f"❌ Delete failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))