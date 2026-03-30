"""Negotiation agent for settlement discussions."""

from typing import Dict, Any, List
import logging
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class NegotiationAgent(BaseAgent):
    """Agent specialized in negotiation and settlement facilitation."""
    
    def __init__(self, model_config: Dict[str, Any]):
        super().__init__("NegotiationAgent", model_config)
        self.negotiation_strategies = [
            "collaborative",
            "competitive",
            "accommodating",
            "compromising",
            "avoiding"
        ]
    
    def get_system_prompt(self) -> str:
        """Return system prompt for negotiation agent."""
        return """
        You are a skilled negotiation facilitator with expertise in:
        1. Identifying common ground between parties
        2. Proposing creative settlement solutions
        3. Managing negotiation dynamics
        4. Facilitating productive discussions
        5. Drafting settlement agreements
        
        Focus on win-win outcomes and maintain neutrality while
        helping parties reach mutually beneficial agreements.
        """
    
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process negotiation facilitation request."""
        try:
            parties = input_data.get("parties", [])
            dispute_summary = input_data.get("dispute_summary", "")
            desired_outcomes = input_data.get("desired_outcomes", {})
            
            # Analyze negotiation positions
            position_analysis = self._analyze_positions(parties, desired_outcomes)
            
            # Generate settlement proposals
            settlement_options = self._generate_settlement_options(
                dispute_summary, desired_outcomes
            )
            
            # Add to conversation history
            self.add_to_history("user", dispute_summary, {
                "parties": parties,
                "outcomes": desired_outcomes
            })
            
            response = {
                "agent": self.name,
                "position_analysis": position_analysis,
                "settlement_options": settlement_options,
                "negotiation_strategy": "Recommended approach for productive negotiations",
                "next_steps": "Suggested actions for moving forward",
                "timestamp": self.created_at.isoformat()
            }
            
            self.add_to_history("assistant", str(response))
            
            return response
            
        except Exception as e:
            logger.error(f"Error in negotiation processing: {str(e)}")
            return {
                "error": "Failed to process negotiation request",
                "details": str(e)
            }
    
    def _analyze_positions(self, parties: List[str], outcomes: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze negotiation positions of all parties."""
        return {
            "party_interests": "Analysis of underlying interests",
            "common_ground": "Areas of potential agreement",
            "conflict_points": "Key areas of disagreement",
            "leverage_analysis": "Assessment of each party's negotiation power"
        }
    
    def _generate_settlement_options(self, dispute: str, outcomes: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate potential settlement options."""
        return [
            {
                "option": "Monetary Settlement",
                "description": "Financial compensation approach",
                "pros": ["Clear resolution", "Quick implementation"],
                "cons": ["May not address underlying issues"]
            },
            {
                "option": "Performance-Based Settlement",
                "description": "Specific performance requirements",
                "pros": ["Addresses root cause", "Maintains relationships"],
                "cons": ["Requires ongoing monitoring"]
            }
        ]