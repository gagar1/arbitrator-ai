"""Shipping and logistics tracking integration."""

import aiohttp
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import re

logger = logging.getLogger(__name__)


class ShippingTracker:
    """Integration with shipping carriers for tracking and delivery verification."""
    
    def __init__(self):
        self.supported_carriers = {
            "fedex": {"pattern": r"^\d{12,14}$", "api_endpoint": "fedex_api"},
            "ups": {"pattern": r"^1Z[A-Z0-9]{16}$", "api_endpoint": "ups_api"},
            "dhl": {"pattern": r"^\d{10,11}$", "api_endpoint": "dhl_api"},
            "usps": {"pattern": r"^(94|93|92|91|90)\d{20}$", "api_endpoint": "usps_api"}
        }
    
    async def track_shipment(self, tracking_number: str, carrier: Optional[str] = None) -> Dict[str, Any]:
        """Track a shipment using tracking number."""
        try:
            # Auto-detect carrier if not provided
            if not carrier:
                carrier = self._detect_carrier(tracking_number)
            
            if not carrier:
                return {
                    "error": "Unable to detect carrier from tracking number",
                    "tracking_number": tracking_number
                }
            
            # Simulate tracking data (in production, integrate with actual APIs)
            tracking_data = await self._fetch_tracking_data(tracking_number, carrier)
            
            return {
                "tracking_number": tracking_number,
                "carrier": carrier,
                "status": tracking_data.get("status", "unknown"),
                "delivery_date": tracking_data.get("delivery_date"),
                "estimated_delivery": tracking_data.get("estimated_delivery"),
                "tracking_events": tracking_data.get("events", []),
                "delivery_address": tracking_data.get("delivery_address"),
                "signature_required": tracking_data.get("signature_required", False),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error tracking shipment {tracking_number}: {str(e)}")
            return {
                "error": "Failed to track shipment",
                "tracking_number": tracking_number,
                "details": str(e)
            }
    
    async def verify_delivery(self, tracking_number: str, expected_date: datetime) -> Dict[str, Any]:
        """Verify if delivery occurred as expected."""
        try:
            tracking_data = await self.track_shipment(tracking_number)
            
            if "error" in tracking_data:
                return tracking_data
            
            verification = {
                "tracking_number": tracking_number,
                "expected_delivery_date": expected_date.isoformat(),
                "actual_delivery_date": tracking_data.get("delivery_date"),
                "delivery_status": tracking_data.get("status"),
                "verification_result": "pending",
                "delay_analysis": {},
                "dispute_evidence": []
            }
            
            # Analyze delivery performance
            if tracking_data.get("delivery_date"):
                actual_delivery = datetime.fromisoformat(tracking_data["delivery_date"])
                delay_days = (actual_delivery - expected_date).days
                
                verification["verification_result"] = "delivered"
                verification["delay_analysis"] = {
                    "delay_days": delay_days,
                    "on_time": delay_days <= 0,
                    "delay_category": self._categorize_delay(delay_days)
                }
                
                # Generate dispute evidence if delayed
                if delay_days > 0:
                    verification["dispute_evidence"] = self._generate_delay_evidence(
                        tracking_data, delay_days
                    )
            
            return verification
            
        except Exception as e:
            logger.error(f"Error verifying delivery: {str(e)}")
            return {
                "error": "Failed to verify delivery",
                "tracking_number": tracking_number,
                "details": str(e)
            }
    
    async def analyze_shipping_disputes(self, 
                                      tracking_numbers: List[str],
                                      contract_terms: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze multiple shipments for dispute resolution."""
        try:
            analysis = {
                "total_shipments": len(tracking_numbers),
                "shipment_analysis": [],
                "overall_performance": {},
                "contract_compliance": {},
                "recommendations": []
            }
            
            on_time_count = 0
            total_delay_days = 0
            
            for tracking_number in tracking_numbers:
                shipment_data = await self.track_shipment(tracking_number)
                
                if "error" not in shipment_data:
                    shipment_analysis = {
                        "tracking_number": tracking_number,
                        "status": shipment_data.get("status"),
                        "delivery_performance": "pending"
                    }
                    
                    # Analyze against contract terms
                    if contract_terms.get("delivery_deadline"):
                        deadline = datetime.fromisoformat(contract_terms["delivery_deadline"])
                        verification = await self.verify_delivery(tracking_number, deadline)
                        
                        if verification.get("delay_analysis"):
                            delay_info = verification["delay_analysis"]
                            if delay_info["on_time"]:
                                on_time_count += 1
                            else:
                                total_delay_days += delay_info["delay_days"]
                            
                            shipment_analysis["delivery_performance"] = delay_info
                    
                    analysis["shipment_analysis"].append(shipment_analysis)
            
            # Calculate overall performance
            analysis["overall_performance"] = {
                "on_time_percentage": (on_time_count / len(tracking_numbers)) * 100,
                "average_delay_days": total_delay_days / max(1, len(tracking_numbers) - on_time_count),
                "performance_rating": self._rate_performance(on_time_count, len(tracking_numbers))
            }
            
            # Assess contract compliance
            analysis["contract_compliance"] = self._assess_contract_compliance(
                analysis["overall_performance"], contract_terms
            )
            
            # Generate recommendations
            analysis["recommendations"] = self._generate_shipping_recommendations(
                analysis["overall_performance"], analysis["contract_compliance"]
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing shipping disputes: {str(e)}")
            return {
                "error": "Failed to analyze shipping disputes",
                "details": str(e)
            }
    
    def _detect_carrier(self, tracking_number: str) -> Optional[str]:
        """Auto-detect carrier based on tracking number format."""
        for carrier, config in self.supported_carriers.items():
            if re.match(config["pattern"], tracking_number):
                return carrier
        return None
    
    async def _fetch_tracking_data(self, tracking_number: str, carrier: str) -> Dict[str, Any]:
        """Fetch tracking data from carrier API (simulated)."""
        # Simulate API response - in production, integrate with actual carrier APIs
        return {
            "status": "delivered",
            "delivery_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
            "estimated_delivery": (datetime.utcnow() - timedelta(days=3)).isoformat(),
            "events": [
                {
                    "date": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                    "status": "picked_up",
                    "location": "Origin facility"
                },
                {
                    "date": (datetime.utcnow() - timedelta(days=3)).isoformat(),
                    "status": "in_transit",
                    "location": "Sorting facility"
                },
                {
                    "date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "status": "delivered",
                    "location": "Destination address"
                }
            ],
            "delivery_address": "123 Main St, City, State 12345",
            "signature_required": True
        }
    
    def _categorize_delay(self, delay_days: int) -> str:
        """Categorize delivery delay severity."""
        if delay_days <= 0:
            return "on_time"
        elif delay_days <= 2:
            return "minor_delay"
        elif delay_days <= 7:
            return "moderate_delay"
        else:
            return "major_delay"
    
    def _generate_delay_evidence(self, tracking_data: Dict[str, Any], delay_days: int) -> List[Dict[str, Any]]:
        """Generate evidence for delivery delay disputes."""
        evidence = [
            {
                "type": "tracking_record",
                "description": f"Official tracking shows {delay_days} day delay",
                "source": tracking_data.get("carrier", "carrier"),
                "reliability": "high"
            }
        ]
        
        # Add weather-related evidence if applicable
        if delay_days > 3:
            evidence.append({
                "type": "external_factors",
                "description": "Significant delay may indicate weather or operational issues",
                "source": "analysis",
                "reliability": "medium"
            })
        
        return evidence
    
    def _rate_performance(self, on_time_count: int, total_count: int) -> str:
        """Rate overall shipping performance."""
        percentage = (on_time_count / total_count) * 100
        
        if percentage >= 95:
            return "excellent"
        elif percentage >= 85:
            return "good"
        elif percentage >= 70:
            return "fair"
        else:
            return "poor"
    
    def _assess_contract_compliance(self, 
                                  performance: Dict[str, Any], 
                                  contract_terms: Dict[str, Any]) -> Dict[str, Any]:
        """Assess compliance with contract delivery terms."""
        compliance = {
            "meets_sla": False,
            "breach_severity": "none",
            "penalty_applicable": False,
            "compliance_score": 0
        }
        
        required_percentage = contract_terms.get("on_time_percentage", 95)
        actual_percentage = performance.get("on_time_percentage", 0)
        
        compliance["meets_sla"] = actual_percentage >= required_percentage
        compliance["compliance_score"] = actual_percentage
        
        if not compliance["meets_sla"]:
            gap = required_percentage - actual_percentage
            if gap > 20:
                compliance["breach_severity"] = "major"
                compliance["penalty_applicable"] = True
            elif gap > 10:
                compliance["breach_severity"] = "moderate"
            else:
                compliance["breach_severity"] = "minor"
        
        return compliance
    
    def _generate_shipping_recommendations(self, 
                                         performance: Dict[str, Any], 
                                         compliance: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on shipping analysis."""
        recommendations = []
        
        if not compliance["meets_sla"]:
            recommendations.append("Contract SLA breach identified - consider penalty enforcement")
        
        if performance["performance_rating"] == "poor":
            recommendations.append("Consider alternative shipping provider or renegotiate terms")
        
        if compliance["penalty_applicable"]:
            recommendations.append("Significant breach warrants contract penalty application")
        
        if not recommendations:
            recommendations.append("Shipping performance meets contractual requirements")
        
        return recommendations