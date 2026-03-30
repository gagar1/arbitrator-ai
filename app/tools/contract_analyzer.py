"""Contract analysis tool for extracting key terms and conditions."""

from typing import Dict, Any, List, Optional
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ContractAnalyzer:
    """Tool for analyzing contract documents and extracting key information."""
    
    def __init__(self):
        self.key_terms = [
            "payment terms", "delivery date", "termination clause",
            "liability", "force majeure", "governing law",
            "dispute resolution", "confidentiality", "intellectual property",
            "warranties", "indemnification", "amendment"
        ]
        
        self.risk_indicators = [
            "unlimited liability", "no warranty", "as-is condition",
            "immediate termination", "sole discretion", "without notice",
            "liquidated damages", "penalty", "forfeiture"
        ]
    
    async def analyze_terms(self, contract_id: str, dispute_context: str = "") -> Dict[str, Any]:
        """Analyze contract terms and identify relevant clauses."""
        try:
            # In a real implementation, this would load the actual contract
            # For now, we'll return a structured analysis template
            
            analysis = {
                "contract_id": contract_id,
                "analysis_date": datetime.utcnow().isoformat(),
                "key_terms_found": self._extract_key_terms(dispute_context),
                "risk_assessment": self._assess_risks(dispute_context),
                "relevant_clauses": self._identify_relevant_clauses(dispute_context),
                "recommendations": self._generate_recommendations(dispute_context),
                "compliance_status": "pending_review"
            }
            
            logger.info(f"Completed contract analysis for {contract_id}")
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing contract {contract_id}: {str(e)}")
            return {
                "error": "Contract analysis failed",
                "contract_id": contract_id,
                "details": str(e)
            }
    
    def _extract_key_terms(self, text: str) -> List[Dict[str, Any]]:
        """Extract key contractual terms from text."""
        found_terms = []
        
        for term in self.key_terms:
            # Simple pattern matching - in production, use more sophisticated NLP
            pattern = rf"\b{re.escape(term)}\b"
            matches = re.finditer(pattern, text, re.IGNORECASE)
            
            for match in matches:
                found_terms.append({
                    "term": term,
                    "position": match.start(),
                    "context": text[max(0, match.start()-50):match.end()+50],
                    "confidence": 0.8  # Placeholder confidence score
                })
        
        return found_terms
    
    def _assess_risks(self, text: str) -> Dict[str, Any]:
        """Assess potential risks in the contract."""
        risks_found = []
        
        for risk in self.risk_indicators:
            if risk.lower() in text.lower():
                risks_found.append({
                    "risk_type": risk,
                    "severity": "high" if risk in ["unlimited liability", "no warranty"] else "medium",
                    "description": f"Contract contains {risk} clause"
                })
        
        return {
            "total_risks": len(risks_found),
            "high_risk_count": len([r for r in risks_found if r["severity"] == "high"]),
            "risks_identified": risks_found,
            "overall_risk_level": "high" if any(r["severity"] == "high" for r in risks_found) else "medium"
        }
    
    def _identify_relevant_clauses(self, dispute_context: str) -> List[Dict[str, Any]]:
        """Identify clauses relevant to the dispute context."""
        # This would use more sophisticated matching in production
        relevant_clauses = [
            {
                "clause_number": "5.2",
                "clause_title": "Payment Terms",
                "relevance_score": 0.9,
                "content": "Payment shall be made within 30 days of invoice date...",
                "why_relevant": "Dispute involves payment timing"
            },
            {
                "clause_number": "12.1",
                "clause_title": "Dispute Resolution",
                "relevance_score": 0.95,
                "content": "Any disputes shall be resolved through binding arbitration...",
                "why_relevant": "Defines the dispute resolution process"
            }
        ]
        
        return relevant_clauses
    
    def _generate_recommendations(self, dispute_context: str) -> List[Dict[str, Any]]:
        """Generate recommendations based on contract analysis."""
        recommendations = [
            {
                "type": "legal_strategy",
                "priority": "high",
                "recommendation": "Focus on payment terms clause interpretation",
                "rationale": "Contract language supports client position on payment timing"
            },
            {
                "type": "risk_mitigation",
                "priority": "medium",
                "recommendation": "Consider alternative dispute resolution",
                "rationale": "Contract mandates arbitration before litigation"
            },
            {
                "type": "documentation",
                "priority": "high",
                "recommendation": "Gather all payment-related correspondence",
                "rationale": "Evidence needed to support contract interpretation"
            }
        ]
        
        return recommendations
    
    async def compare_contracts(self, contract_ids: List[str]) -> Dict[str, Any]:
        """Compare multiple contracts and identify differences."""
        try:
            comparison = {
                "contracts_compared": contract_ids,
                "comparison_date": datetime.utcnow().isoformat(),
                "key_differences": [],
                "common_terms": [],
                "risk_variations": [],
                "recommendations": []
            }
            
            # Placeholder comparison logic
            comparison["key_differences"] = [
                {
                    "aspect": "Payment Terms",
                    "contract_1": "30 days",
                    "contract_2": "45 days",
                    "impact": "Different payment schedules may affect dispute resolution"
                }
            ]
            
            return comparison
            
        except Exception as e:
            logger.error(f"Error comparing contracts: {str(e)}")
            return {"error": "Contract comparison failed", "details": str(e)}
    
    async def extract_obligations(self, contract_text: str) -> Dict[str, Any]:
        """Extract party obligations from contract text."""
        try:
            obligations = {
                "party_a_obligations": [],
                "party_b_obligations": [],
                "mutual_obligations": [],
                "conditional_obligations": []
            }
            
            # Simple obligation extraction patterns
            obligation_patterns = [
                r"shall\s+([^.]+)",
                r"must\s+([^.]+)",
                r"agrees\s+to\s+([^.]+)",
                r"responsible\s+for\s+([^.]+)"
            ]
            
            for pattern in obligation_patterns:
                matches = re.finditer(pattern, contract_text, re.IGNORECASE)
                for match in matches:
                    obligation_text = match.group(1).strip()
                    obligations["mutual_obligations"].append({
                        "text": obligation_text,
                        "type": "general",
                        "enforceability": "binding"
                    })
            
            return obligations
            
        except Exception as e:
            logger.error(f"Error extracting obligations: {str(e)}")
            return {"error": "Obligation extraction failed", "details": str(e)}