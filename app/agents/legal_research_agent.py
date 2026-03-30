"""Legal research agent for finding precedents and regulations."""

from typing import Dict, Any, List
import logging
from .base_agent import BaseAgent
from ..core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)


class LegalResearchAgent(BaseAgent):
    """Agent specialized in legal research and precedent analysis."""
    
    def __init__(self, model_config: Dict[str, Any], rag_engine: RAGEngine):
        super().__init__("LegalResearchAgent", model_config)
        self.rag_engine = rag_engine
    
    def get_system_prompt(self) -> str:
        """Return system prompt for legal research agent."""
        return """
        You are a legal research specialist with expertise in:
        1. Finding relevant legal precedents
        2. Analyzing case law and statutes
        3. Identifying applicable regulations
        4. Summarizing legal principles
        5. Cross-referencing jurisdictional differences
        
        Provide accurate, well-cited legal research with clear explanations
        of how precedents apply to current situations.
        """
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process legal research request."""
        try:
            query = input_data.get("query", "")
            jurisdiction = input_data.get("jurisdiction", "general")
            case_type = input_data.get("case_type", "commercial")
            
            # Search for relevant legal documents
            legal_precedents = await self.rag_engine.query(
                f"{query} {jurisdiction} {case_type} precedent case law",
                top_k=10
            )
            
            # Add to conversation history
            self.add_to_history("user", query, {
                "jurisdiction": jurisdiction,
                "case_type": case_type
            })
            
            response = {
                "agent": self.name,
                "query": query,
                "jurisdiction": jurisdiction,
                "precedents": legal_precedents,
                "summary": "Comprehensive legal research summary",
                "recommendations": "Legal strategy recommendations",
                "timestamp": self.created_at.isoformat()
            }
            
            self.add_to_history("assistant", str(response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in legal research: {str(e)}")
            return {
                "error": "Failed to process legal research request",
                "details": str(e)
            }