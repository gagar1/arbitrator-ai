"""Health check endpoints."""

from fastapi import APIRouter, Depends
from typing import Dict, Any
import logging
from datetime import datetime

from ...core.config import config
from ...core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "arbitrator-ai",
        "version": "0.1.0"
    }


@router.get("/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check including system components."""
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "arbitrator-ai",
        "version": "0.1.0",
        "components": {}
    }
    
    # Check configuration
    try:
        config_validation = config.validate_config()
        health_status["components"]["configuration"] = {
            "status": "healthy" if config_validation["valid"] else "unhealthy",
            "details": config_validation
        }
    except Exception as e:
        health_status["components"]["configuration"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check data directories
    try:
        data_status = {
            "data_dir_exists": config.data_dir.exists(),
            "contracts_dir_exists": config.contracts_dir.exists(),
            "legal_docs_dir_exists": config.legal_docs_dir.exists()
        }
        health_status["components"]["data_directories"] = {
            "status": "healthy" if all(data_status.values()) else "warning",
            "details": data_status
        }
    except Exception as e:
        health_status["components"]["data_directories"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Determine overall status
    component_statuses = [comp["status"] for comp in health_status["components"].values()]
    if "unhealthy" in component_statuses:
        health_status["status"] = "unhealthy"
    elif "warning" in component_statuses:
        health_status["status"] = "warning"
    
    return health_status


@router.get("/rag")
async def rag_health_check() -> Dict[str, Any]:
    """Health check for RAG engine."""
    try:
        # This would be injected in a real implementation
        # For now, return a placeholder
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "rag_engine": {
                "status": "initialized",
                "collection_name": config.rag_config.collection_name,
                "embedding_model": config.rag_config.embedding_model
            }
        }
    except Exception as e:
        logger.error(f"RAG health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }