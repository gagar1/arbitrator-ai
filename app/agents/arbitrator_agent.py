"""Main arbitrator agent for dispute resolution."""

from typing import Dict, Any
import logging
from .base_agent import BaseAgent
from ..core.rag_engine import RAGEngine
from ..tools.contract_analyzer import ContractAnalyzer

logger = logging.getLogger(__name__)


class ArbitratorAgent(BaseAgent):
    """Agent specialized in arbitration and dispute resolution."""
    
    def __init__(self, model_config: Dict[str, Any], rag_engine: RAGEngine):
        super().__init__("ArbitratorAgent", model_config)
        self.rag_engine = rag_engine
        self.contract_analyzer = ContractAnalyzer()
    
    def get_system_prompt(self) -> str:
        """Return system prompt for arbitrator agent."""
        return """
        You are an expert arbitrator specializing in commercial dispute resolution.
        Your role is to:
        1. Analyze contract terms and conditions
        2. Identify relevant legal precedents
        3. Provide fair and balanced arbitration decisions
        4. Consider all parties' perspectives
        5. Apply relevant laws and regulations
        
        Always maintain neutrality and provide clear reasoning for your decisions.
        Use the provided contract documents and legal knowledge to support your analysis.
        """
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process arbitration request."""
        try:
            dispute_details = input_data.get("dispute_details", "")
            contract_id = input_data.get("contract_id")
            
            # Retrieve relevant contract information
            contract_context = await self.rag_engine.query(
                f"contract {contract_id} terms conditions",
                top_k=5
            )
            
            # Analyze contract terms
            contract_analysis = await self.contract_analyzer.analyze_terms(
                contract_id, dispute_details
            )
            
            # Add to conversation history
            self.add_to_history("user", dispute_details, {"contract_id": contract_id})
            
            # Generate arbitration response
            response = {
                "agent": self.name,
                "analysis": contract_analysis,
                "relevant_clauses": contract_context,
                "recommendation": "Detailed arbitration decision based on contract analysis",
                "reasoning": "Step-by-step legal reasoning",
                "timestamp": self.created_at.isoformat()
            }
            
            self.add_to_history("assistant", str(response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in arbitrator processing: {str(e)}")
            return {
                "error": "Failed to process arbitration request",
                "details": str(e)
            }