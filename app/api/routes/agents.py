"""Agent management and interaction endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

from ...agents.arbitrator_agent import ArbitratorAgent
from ...agents.legal_research_agent import LegalResearchAgent
from ...agents.negotiation_agent import NegotiationAgent
from ...core.rag_engine import RAGEngine
from ...core.config import config

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models for request/response
class ArbitrationRequest(BaseModel):
    dispute_details: str
    contract_id: Optional[str] = None
    parties: List[str] = []
    dispute_type: str = "commercial"
    urgency: str = "normal"


class LegalResearchRequest(BaseModel):
    query: str
    jurisdiction: str = "general"
    case_type: str = "commercial"
    date_range: Optional[Dict[str, str]] = None


class NegotiationRequest(BaseModel):
    parties: List[str]
    dispute_summary: str
    desired_outcomes: Dict[str, Any] = {}
    negotiation_style: str = "collaborative"


class AgentResponse(BaseModel):
    agent: str
    response: Dict[str, Any]
    timestamp: str
    processing_time_ms: Optional[int] = None


# Agent instances (would be managed by dependency injection in production)
_agent_instances = {}


def get_agent_instance(agent_type: str, rag_engine: RAGEngine):
    """Get or create agent instance."""
    if agent_type not in _agent_instances:
        model_config = config.get_model_config("anthropic")  # Default to Anthropic
        
        if agent_type == "arbitrator":
            _agent_instances[agent_type] = ArbitratorAgent(model_config.__dict__, rag_engine)
        elif agent_type == "legal_research":
            _agent_instances[agent_type] = LegalResearchAgent(model_config.__dict__, rag_engine)
        elif agent_type == "negotiation":
            _agent_instances[agent_type] = NegotiationAgent(model_config.__dict__)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown agent type: {agent_type}")
    
    return _agent_instances[agent_type]


@router.get("/")
async def list_agents() -> Dict[str, Any]:
    """List available agents and their capabilities."""
    return {
        "agents": [
            {
                "name": "arbitrator",
                "description": "Expert arbitrator for dispute resolution",
                "capabilities": [
                    "Contract analysis",
                    "Dispute resolution",
                    "Legal precedent analysis",
                    "Fair decision making"
                ],
                "endpoint": "/agents/arbitrator/process"
            },
            {
                "name": "legal_research",
                "description": "Legal research specialist",
                "capabilities": [
                    "Case law research",
                    "Precedent analysis",
                    "Regulatory compliance",
                    "Jurisdiction analysis"
                ],
                "endpoint": "/agents/legal_research/process"
            },
            {
                "name": "negotiation",
                "description": "Negotiation facilitation expert",
                "capabilities": [
                    "Settlement facilitation",
                    "Win-win solutions",
                    "Negotiation strategy",
                    "Conflict resolution"
                ],
                "endpoint": "/agents/negotiation/process"
            }
        ],
        "total_agents": 3
    }


@router.post("/arbitrator/process")
async def process_arbitration(
    request: ArbitrationRequest,
    rag_engine: RAGEngine = Depends()
) -> AgentResponse:
    """Process arbitration request."""
    try:
        start_time = datetime.utcnow()
        
        agent = get_agent_instance("arbitrator", rag_engine)
        
        input_data = {
            "dispute_details": request.dispute_details,
            "contract_id": request.contract_id,
            "parties": request.parties,
            "dispute_type": request.dispute_type,
            "urgency": request.urgency
        }
        
        response = await agent.process(input_data)
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            agent="arbitrator",
            response=response,
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing arbitration request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Arbitration processing failed: {str(e)}")


@router.post("/legal_research/process")
async def process_legal_research(
    request: LegalResearchRequest,
    rag_engine: RAGEngine = Depends()
) -> AgentResponse:
    """Process legal research request."""
    try:
        start_time = datetime.utcnow()
        
        agent = get_agent_instance("legal_research", rag_engine)
        
        input_data = {
            "query": request.query,
            "jurisdiction": request.jurisdiction,
            "case_type": request.case_type,
            "date_range": request.date_range
        }
        
        response = await agent.process(input_data)
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            agent="legal_research",
            response=response,
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing legal research request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Legal research processing failed: {str(e)}")


@router.post("/negotiation/process")
async def process_negotiation(
    request: NegotiationRequest
) -> AgentResponse:
    """Process negotiation facilitation request."""
    try:
        start_time = datetime.utcnow()
        
        # Negotiation agent doesn't need RAG engine
        agent = get_agent_instance("negotiation", None)
        
        input_data = {
            "parties": request.parties,
            "dispute_summary": request.dispute_summary,
            "desired_outcomes": request.desired_outcomes,
            "negotiation_style": request.negotiation_style
        }
        
        response = await agent.process(input_data)
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return AgentResponse(
            agent="negotiation",
            response=response,
            timestamp=datetime.utcnow().isoformat(),
            processing_time_ms=processing_time
        )
        
    except Exception as e:
        logger.error(f"Error processing negotiation request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Negotiation processing failed: {str(e)}")


@router.get("/arbitrator/history")
async def get_arbitrator_history(rag_engine: RAGEngine = Depends()) -> Dict[str, Any]:
    """Get arbitrator agent conversation history."""
    try:
        agent = get_agent_instance("arbitrator", rag_engine)
        return {
            "agent": "arbitrator",
            "history": agent.conversation_history,
            "total_conversations": len(agent.conversation_history)
        }
    except Exception as e:
        logger.error(f"Error retrieving arbitrator history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve history: {str(e)}")


@router.delete("/arbitrator/history")
async def clear_arbitrator_history(rag_engine: RAGEngine = Depends()) -> Dict[str, str]:
    """Clear arbitrator agent conversation history."""
    try:
        agent = get_agent_instance("arbitrator", rag_engine)
        agent.clear_history()
        return {"message": "Arbitrator conversation history cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing arbitrator history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to clear history: {str(e)}")


@router.get("/status")
async def get_agents_status() -> Dict[str, Any]:
    """Get status of all agent instances."""
    status = {
        "active_agents": len(_agent_instances),
        "agents": {}
    }
    
    for agent_type, agent in _agent_instances.items():
        status["agents"][agent_type] = {
            "name": agent.name,
            "created_at": agent.created_at.isoformat(),
            "conversation_count": len(agent.conversation_history),
            "model_config": agent.model_config
        }
    
    return status