"""Document management endpoints."""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from pathlib import Path
import shutil
import tempfile

from ...core.rag_engine import RAGEngine
from ...core.document_processor import DocumentProcessor
from ...core.config import config

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models
class DocumentInfo(BaseModel):
    id: str
    filename: str
    document_type: str
    source: str
    upload_date: str
    size_bytes: int
    chunk_count: int


class DocumentQuery(BaseModel):
    query: str
    top_k: int = 5
    document_type: Optional[str] = None
    source_filter: Optional[str] = None


class DocumentSearchResult(BaseModel):
    documents: List[Dict[str, Any]]
    total_results: int
    query: str
    processing_time_ms: int


@router.get("/")
async def list_documents(rag_engine: RAGEngine = Depends()) -> Dict[str, Any]:
    """List all documents in the system."""
    try:
        stats = await rag_engine.get_collection_stats()
        return {
            "total_documents": stats.get("document_count", 0),
            "collection_name": stats.get("collection_name", ""),
            "embedding_model": stats.get("embedding_model", ""),
            "status": "ready"
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form("contract"),
    rag_engine: RAGEngine = Depends(),
    doc_processor: DocumentProcessor = Depends()
) -> Dict[str, Any]:
    """Upload and process a document."""
    try:
        # Validate file type
        if not file.filename:
            raise HTTPException(status_code=400, detail="No filename provided")
        
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in doc_processor.supported_formats:
            raise HTTPException(
                status_code=400, 
                detail=f"Unsupported file format: {file_extension}. Supported: {doc_processor.supported_formats}"
            )
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            shutil.copyfileobj(file.file, temp_file)
            temp_path = temp_file.name
        
        try:
            # Process the document
            documents = await doc_processor.process_file(temp_path)
            
            if not documents:
                raise HTTPException(status_code=400, detail="No content could be extracted from the file")
            
            # Add document type metadata
            for doc in documents:
                doc["type"] = document_type
                doc["original_filename"] = file.filename
            
            # Add to RAG engine
            success = await rag_engine.add_documents(documents)
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to index document")
            
            # Save to permanent location
            save_dir = config.contracts_dir if document_type == "contract" else config.legal_docs_dir
            save_path = save_dir / file.filename
            shutil.copy2(temp_path, save_path)
            
            return {
                "message": "Document uploaded and processed successfully",
                "filename": file.filename,
                "document_type": document_type,
                "chunks_created": len(documents),
                "file_size": len(await file.read()) if hasattr(file, 'read') else 0,
                "saved_path": str(save_path),
                "upload_date": datetime.utcnow().isoformat()
            }
            
        finally:
            # Clean up temporary file
            Path(temp_path).unlink(missing_ok=True)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@router.post("/search")
async def search_documents(
    query: DocumentQuery,
    rag_engine: RAGEngine = Depends()
) -> DocumentSearchResult:
    """Search documents using semantic similarity."""
    try:
        start_time = datetime.utcnow()
        
        # Build filter metadata
        filter_metadata = {}
        if query.document_type:
            filter_metadata["document_type"] = query.document_type
        if query.source_filter:
            filter_metadata["source"] = {"$regex": query.source_filter}
        
        # Perform search
        results = await rag_engine.query(
            query.query,
            top_k=query.top_k,
            filter_metadata=filter_metadata if filter_metadata else None
        )
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return DocumentSearchResult(
            documents=results,
            total_results=len(results),
            query=query.query,
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document search failed: {str(e)}")


@router.post("/process_directory")
async def process_directory(
    directory_path: str = Form(...),
    rag_engine: RAGEngine = Depends(),
    doc_processor: DocumentProcessor = Depends()
) -> Dict[str, Any]:
    """Process all documents in a directory."""
    try:
        if not Path(directory_path).exists():
            raise HTTPException(status_code=400, detail=f"Directory does not exist: {directory_path}")
        
        # Process all documents in directory
        documents = await doc_processor.process_directory(directory_path)
        
        if not documents:
            return {
                "message": "No documents found or processed",
                "directory": directory_path,
                "documents_processed": 0
            }
        
        # Add to RAG engine
        success = await rag_engine.add_documents(documents)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to index documents")
        
        return {
            "message": "Directory processed successfully",
            "directory": directory_path,
            "documents_processed": len(set(doc["source"] for doc in documents)),
            "total_chunks": len(documents),
            "processing_date": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Directory processing failed: {str(e)}")


@router.delete("/")
async def delete_all_documents(rag_engine: RAGEngine = Depends()) -> Dict[str, str]:
    """Delete all documents from the system."""
    try:
        success = await rag_engine.reset_collection()
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete documents")
        
        return {
            "message": "All documents deleted successfully",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Document deletion failed: {str(e)}")


@router.get("/stats")
async def get_document_stats(rag_engine: RAGEngine = Depends()) -> Dict[str, Any]:
    """Get document collection statistics."""
    try:
        stats = await rag_engine.get_collection_stats()
        
        # Add file system stats
        contracts_count = len(list(config.contracts_dir.glob("*"))) if config.contracts_dir.exists() else 0
        legal_docs_count = len(list(config.legal_docs_dir.glob("*"))) if config.legal_docs_dir.exists() else 0
        
        stats.update({
            "files_on_disk": {
                "contracts": contracts_count,
                "legal_docs": legal_docs_count,
                "total": contracts_count + legal_docs_count
            },
            "directories": {
                "contracts_dir": str(config.contracts_dir),
                "legal_docs_dir": str(config.legal_docs_dir)
            },
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting document stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get document stats: {str(e)}")