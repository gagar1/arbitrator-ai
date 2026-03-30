"""Analysis and reporting endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timedelta

from ...tools.contract_analyzer import ContractAnalyzer
from ...tools.weather_api import WeatherAPI
from ...tools.shipping_tracker import ShippingTracker
from ...core.rag_engine import RAGEngine

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic models
class ContractAnalysisRequest(BaseModel):
    contract_id: str
    dispute_context: Optional[str] = ""
    analysis_type: str = "full"  # full, terms, risks, obligations


class WeatherAnalysisRequest(BaseModel):
    location: str
    incident_date: str  # ISO format
    duration_days: int = 7
    analysis_type: str = "dispute"  # dispute, current, historical


class ShippingAnalysisRequest(BaseModel):
    tracking_numbers: List[str]
    contract_terms: Dict[str, Any] = {}
    expected_delivery_date: Optional[str] = None


class ComprehensiveAnalysisRequest(BaseModel):
    dispute_id: str
    contract_id: Optional[str] = None
    tracking_numbers: List[str] = []
    incident_location: Optional[str] = None
    incident_date: Optional[str] = None
    analysis_scope: List[str] = ["contract", "shipping", "weather"]


# Tool instances
contract_analyzer = ContractAnalyzer()
weather_api = WeatherAPI()
shipping_tracker = ShippingTracker()


@router.get("/")
async def list_analysis_tools() -> Dict[str, Any]:
    """List available analysis tools and their capabilities."""
    return {
        "tools": [
            {
                "name": "contract_analyzer",
                "description": "Analyze contract terms and identify risks",
                "capabilities": [
                    "Key terms extraction",
                    "Risk assessment",
                    "Obligation identification",
                    "Contract comparison"
                ],
                "endpoint": "/analysis/contract"
            },
            {
                "name": "weather_api",
                "description": "Weather data for shipping disputes",
                "capabilities": [
                    "Historical weather data",
                    "Severe weather detection",
                    "Impact assessment",
                    "Force majeure analysis"
                ],
                "endpoint": "/analysis/weather"
            },
            {
                "name": "shipping_tracker",
                "description": "Shipping and logistics analysis",
                "capabilities": [
                    "Delivery verification",
                    "Performance analysis",
                    "SLA compliance",
                    "Delay analysis"
                ],
                "endpoint": "/analysis/shipping"
            }
        ],
        "comprehensive_analysis": "/analysis/comprehensive"
    }


@router.post("/contract")
async def analyze_contract(
    request: ContractAnalysisRequest
) -> Dict[str, Any]:
    """Analyze contract for dispute resolution."""
    try:
        start_time = datetime.utcnow()
        
        if request.analysis_type == "full":
            analysis = await contract_analyzer.analyze_terms(
                request.contract_id, 
                request.dispute_context
            )
        elif request.analysis_type == "obligations":
            # For this demo, we'll simulate contract text
            contract_text = f"Contract {request.contract_id} with dispute context: {request.dispute_context}"
            analysis = await contract_analyzer.extract_obligations(contract_text)
        else:
            analysis = await contract_analyzer.analyze_terms(
                request.contract_id, 
                request.dispute_context
            )
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "analysis": analysis,
            "request": request.dict(),
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing contract: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Contract analysis failed: {str(e)}")


@router.post("/weather")
async def analyze_weather(
    request: WeatherAnalysisRequest
) -> Dict[str, Any]:
    """Analyze weather conditions for shipping disputes."""
    try:
        start_time = datetime.utcnow()
        
        incident_date = datetime.fromisoformat(request.incident_date.replace('Z', '+00:00'))
        
        if request.analysis_type == "dispute":
            analysis = await weather_api.get_weather_for_dispute(
                request.location,
                incident_date,
                request.duration_days
            )
        elif request.analysis_type == "current":
            analysis = await weather_api.get_current_weather(request.location)
        else:
            # Historical analysis - would need coordinates
            analysis = {
                "message": "Historical weather analysis requires coordinates",
                "location": request.location,
                "date": request.incident_date
            }
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "analysis": analysis,
            "request": request.dict(),
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing weather: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Weather analysis failed: {str(e)}")


@router.post("/shipping")
async def analyze_shipping(
    request: ShippingAnalysisRequest
) -> Dict[str, Any]:
    """Analyze shipping performance and compliance."""
    try:
        start_time = datetime.utcnow()
        
        if len(request.tracking_numbers) == 1 and request.expected_delivery_date:
            # Single shipment verification
            expected_date = datetime.fromisoformat(request.expected_delivery_date.replace('Z', '+00:00'))
            analysis = await shipping_tracker.verify_delivery(
                request.tracking_numbers[0],
                expected_date
            )
        else:
            # Multiple shipments analysis
            analysis = await shipping_tracker.analyze_shipping_disputes(
                request.tracking_numbers,
                request.contract_terms
            )
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        return {
            "analysis": analysis,
            "request": request.dict(),
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error analyzing shipping: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Shipping analysis failed: {str(e)}")


@router.post("/comprehensive")
async def comprehensive_analysis(
    request: ComprehensiveAnalysisRequest,
    rag_engine: RAGEngine = Depends()
) -> Dict[str, Any]:
    """Perform comprehensive analysis combining multiple tools."""
    try:
        start_time = datetime.utcnow()
        
        analysis_results = {
            "dispute_id": request.dispute_id,
            "analysis_scope": request.analysis_scope,
            "results": {},
            "summary": {},
            "recommendations": []
        }
        
        # Contract analysis
        if "contract" in request.analysis_scope and request.contract_id:
            try:
                contract_analysis = await contract_analyzer.analyze_terms(
                    request.contract_id,
                    f"Comprehensive dispute analysis for {request.dispute_id}"
                )
                analysis_results["results"]["contract"] = contract_analysis
            except Exception as e:
                analysis_results["results"]["contract"] = {"error": str(e)}
        
        # Shipping analysis
        if "shipping" in request.analysis_scope and request.tracking_numbers:
            try:
                shipping_analysis = await shipping_tracker.analyze_shipping_disputes(
                    request.tracking_numbers,
                    {"delivery_deadline": request.incident_date} if request.incident_date else {}
                )
                analysis_results["results"]["shipping"] = shipping_analysis
            except Exception as e:
                analysis_results["results"]["shipping"] = {"error": str(e)}
        
        # Weather analysis
        if "weather" in request.analysis_scope and request.incident_location and request.incident_date:
            try:
                incident_date = datetime.fromisoformat(request.incident_date.replace('Z', '+00:00'))
                weather_analysis = await weather_api.get_weather_for_dispute(
                    request.incident_location,
                    incident_date,
                    7
                )
                analysis_results["results"]["weather"] = weather_analysis
            except Exception as e:
                analysis_results["results"]["weather"] = {"error": str(e)}
        
        # Generate comprehensive summary
        analysis_results["summary"] = await _generate_comprehensive_summary(
            analysis_results["results"]
        )
        
        # Generate recommendations
        analysis_results["recommendations"] = await _generate_comprehensive_recommendations(
            analysis_results["results"],
            rag_engine
        )
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        analysis_results.update({
            "processing_time_ms": processing_time,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return analysis_results
        
    except Exception as e:
        logger.error(f"Error in comprehensive analysis: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Comprehensive analysis failed: {str(e)}")


async def _generate_comprehensive_summary(results: Dict[str, Any]) -> Dict[str, Any]:
    """Generate summary from comprehensive analysis results."""
    summary = {
        "total_analyses": len(results),
        "successful_analyses": len([r for r in results.values() if "error" not in r]),
        "key_findings": [],
        "risk_level": "low"
    }
    
    # Analyze contract results
    if "contract" in results and "error" not in results["contract"]:
        contract_data = results["contract"]
        if contract_data.get("risk_assessment", {}).get("overall_risk_level") == "high":
            summary["risk_level"] = "high"
            summary["key_findings"].append("High-risk contract terms identified")
    
    # Analyze shipping results
    if "shipping" in results and "error" not in results["shipping"]:
        shipping_data = results["shipping"]
        if shipping_data.get("overall_performance", {}).get("performance_rating") == "poor":
            summary["risk_level"] = "high" if summary["risk_level"] != "high" else "high"
            summary["key_findings"].append("Poor shipping performance detected")
    
    # Analyze weather results
    if "weather" in results and "error" not in results["weather"]:
        weather_data = results["weather"]
        if weather_data.get("impact_assessment", {}).get("force_majeure_applicable"):
            summary["key_findings"].append("Weather conditions may support force majeure claim")
    
    return summary


async def _generate_comprehensive_recommendations(
    results: Dict[str, Any], 
    rag_engine: RAGEngine
) -> List[Dict[str, Any]]:
    """Generate recommendations based on comprehensive analysis."""
    recommendations = []
    
    # Contract-based recommendations
    if "contract" in results and "error" not in results["contract"]:
        contract_recs = results["contract"].get("recommendations", [])
        for rec in contract_recs:
            recommendations.append({
                "source": "contract_analysis",
                "type": rec.get("type", "general"),
                "recommendation": rec.get("recommendation", ""),
                "priority": rec.get("priority", "medium")
            })
    
    # Shipping-based recommendations
    if "shipping" in results and "error" not in results["shipping"]:
        shipping_recs = results["shipping"].get("recommendations", [])
        for rec in shipping_recs:
            recommendations.append({
                "source": "shipping_analysis",
                "type": "performance",
                "recommendation": rec,
                "priority": "high" if "penalty" in rec.lower() else "medium"
            })
    
    # Weather-based recommendations
    if "weather" in results and "error" not in results["weather"]:
        weather_recs = results["weather"].get("impact_assessment", {}).get("recommendations", [])
        for rec in weather_recs:
            recommendations.append({
                "source": "weather_analysis",
                "type": "force_majeure",
                "recommendation": rec,
                "priority": "high" if "force majeure" in rec.lower() else "medium"
            })
    
    # Add general recommendation if none found
    if not recommendations:
        recommendations.append({
            "source": "general",
            "type": "process",
            "recommendation": "Proceed with standard dispute resolution process",
            "priority": "medium"
        })
    
    return recommendations