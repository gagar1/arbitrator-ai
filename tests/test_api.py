"""Integration tests for FastAPI endpoints."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import tempfile
import json
from pathlib import Path

from app.api.main import app
from app.core.rag_engine import RAGEngine
from app.core.document_processor import DocumentProcessor


class TestHealthEndpoints:
    """Test cases for health check endpoints."""
    
    def test_basic_health_check(self):
        """Test basic health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health/")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert data["service"] == "arbitrator-ai"
    
    def test_detailed_health_check(self):
        """Test detailed health check endpoint."""
        with TestClient(app) as client:
            response = client.get("/health/detailed")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "components" in data
            assert "configuration" in data["components"]
            assert "data_directories" in data["components"]
    
    def test_rag_health_check(self):
        """Test RAG engine health check."""
        with TestClient(app) as client:
            response = client.get("/health/rag")
            
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert "rag_engine" in data


class TestAgentEndpoints:
    """Test cases for agent endpoints."""
    
    def test_list_agents(self):
        """Test listing available agents."""
        with TestClient(app) as client:
            response = client.get("/agents/")
            
            assert response.status_code == 200
            data = response.json()
            assert "agents" in data
            assert "total_agents" in data
            assert data["total_agents"] == 3
            
            agent_names = [agent["name"] for agent in data["agents"]]
            assert "arbitrator" in agent_names
            assert "legal_research" in agent_names
            assert "negotiation" in agent_names
    
    @patch('app.api.routes.agents.get_agent_instance')
    def test_process_arbitration(self, mock_get_agent):
        """Test arbitration processing endpoint."""
        # Mock agent instance
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value={
            "agent": "arbitrator",
            "analysis": {"contract_id": "test_contract"},
            "recommendation": "Test recommendation"
        })
        mock_get_agent.return_value = mock_agent
        
        with TestClient(app) as client:
            request_data = {
                "dispute_details": "Payment dispute between parties",
                "contract_id": "test_contract",
                "parties": ["Company A", "Company B"],
                "dispute_type": "commercial"
            }
            
            response = client.post("/agents/arbitrator/process", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "arbitrator"
            assert "response" in data
            assert "processing_time_ms" in data
    
    @patch('app.api.routes.agents.get_agent_instance')
    def test_process_legal_research(self, mock_get_agent):
        """Test legal research processing endpoint."""
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value={
            "agent": "legal_research",
            "precedents": [{"case": "Test v. Example", "relevance": 0.9}],
            "summary": "Test legal research summary"
        })
        mock_get_agent.return_value = mock_agent
        
        with TestClient(app) as client:
            request_data = {
                "query": "contract breach precedents",
                "jurisdiction": "US",
                "case_type": "commercial"
            }
            
            response = client.post("/agents/legal_research/process", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "legal_research"
            assert "response" in data
    
    @patch('app.api.routes.agents.get_agent_instance')
    def test_process_negotiation(self, mock_get_agent):
        """Test negotiation processing endpoint."""
        mock_agent = Mock()
        mock_agent.process = AsyncMock(return_value={
            "agent": "negotiation",
            "settlement_options": [{"option": "Monetary Settlement"}],
            "negotiation_strategy": "Collaborative approach"
        })
        mock_get_agent.return_value = mock_agent
        
        with TestClient(app) as client:
            request_data = {
                "parties": ["Company A", "Company B"],
                "dispute_summary": "Delivery delay dispute",
                "desired_outcomes": {
                    "Company A": "Compensation",
                    "Company B": "Reduced penalties"
                }
            }
            
            response = client.post("/agents/negotiation/process", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert data["agent"] == "negotiation"
            assert "response" in data


class TestDocumentEndpoints:
    """Test cases for document management endpoints."""
    
    @patch('app.api.main.get_rag_engine')
    def test_list_documents(self, mock_get_rag):
        """Test listing documents endpoint."""
        mock_rag_engine = Mock()
        mock_rag_engine.get_collection_stats = AsyncMock(return_value={
            "document_count": 10,
            "collection_name": "test_collection",
            "embedding_model": "test_model"
        })
        mock_get_rag.return_value = mock_rag_engine
        
        with TestClient(app) as client:
            response = client.get("/documents/")
            
            assert response.status_code == 200
            data = response.json()
            assert "total_documents" in data
            assert data["total_documents"] == 10
    
    @patch('app.api.main.get_rag_engine')
    @patch('app.api.main.get_document_processor')
    def test_upload_document(self, mock_get_processor, mock_get_rag):
        """Test document upload endpoint."""
        # Mock document processor
        mock_processor = Mock()
        mock_processor.supported_formats = ['.txt', '.pdf']
        mock_processor.process_file = AsyncMock(return_value=[
            {
                "id": "test_doc_1",
                "content": "Test document content",
                "source": "test.txt",
                "metadata": {}
            }
        ])
        mock_get_processor.return_value = mock_processor
        
        # Mock RAG engine
        mock_rag_engine = Mock()
        mock_rag_engine.add_documents = AsyncMock(return_value=True)
        mock_get_rag.return_value = mock_rag_engine
        
        with TestClient(app) as client:
            # Create a temporary test file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                temp_file.write("Test document content")
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, 'rb') as test_file:
                    response = client.post(
                        "/documents/upload",
                        files={"file": ("test.txt", test_file, "text/plain")},
                        data={"document_type": "contract"}
                    )
                
                assert response.status_code == 200
                data = response.json()
                assert "message" in data
                assert "chunks_created" in data
                assert data["chunks_created"] == 1
                
            finally:
                Path(temp_file_path).unlink(missing_ok=True)
    
    @patch('app.api.main.get_rag_engine')
    def test_search_documents(self, mock_get_rag):
        """Test document search endpoint."""
        mock_rag_engine = Mock()
        mock_rag_engine.query = AsyncMock(return_value=[
            {
                "id": "doc_1",
                "content": "Test document content",
                "metadata": {"source": "test.pdf"},
                "similarity_score": 0.9
            }
        ])
        mock_get_rag.return_value = mock_rag_engine
        
        with TestClient(app) as client:
            request_data = {
                "query": "payment terms",
                "top_k": 5,
                "document_type": "contract"
            }
            
            response = client.post("/documents/search", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert "total_results" in data
            assert "query" in data
            assert data["query"] == "payment terms"


class TestAnalysisEndpoints:
    """Test cases for analysis endpoints."""
    
    def test_list_analysis_tools(self):
        """Test listing analysis tools endpoint."""
        with TestClient(app) as client:
            response = client.get("/analysis/")
            
            assert response.status_code == 200
            data = response.json()
            assert "tools" in data
            assert len(data["tools"]) == 3
            
            tool_names = [tool["name"] for tool in data["tools"]]
            assert "contract_analyzer" in tool_names
            assert "weather_api" in tool_names
            assert "shipping_tracker" in tool_names
    
    @patch('app.tools.contract_analyzer.ContractAnalyzer.analyze_terms')
    def test_analyze_contract(self, mock_analyze):
        """Test contract analysis endpoint."""
        mock_analyze.return_value = {
            "contract_id": "test_contract",
            "key_terms_found": [{"term": "payment terms", "confidence": 0.9}],
            "risk_assessment": {"overall_risk_level": "medium"}
        }
        
        with TestClient(app) as client:
            request_data = {
                "contract_id": "test_contract",
                "dispute_context": "Payment timing dispute",
                "analysis_type": "full"
            }
            
            response = client.post("/analysis/contract", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert "processing_time_ms" in data
    
    @patch('app.tools.weather_api.WeatherAPI.get_weather_for_dispute')
    def test_analyze_weather(self, mock_weather):
        """Test weather analysis endpoint."""
        mock_weather.return_value = {
            "location": "New York",
            "severe_weather_events": [],
            "impact_assessment": {"impact_level": "low"}
        }
        
        with TestClient(app) as client:
            request_data = {
                "location": "New York",
                "incident_date": "2024-01-15T00:00:00Z",
                "duration_days": 7,
                "analysis_type": "dispute"
            }
            
            response = client.post("/analysis/weather", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert "processing_time_ms" in data
    
    @patch('app.tools.shipping_tracker.ShippingTracker.analyze_shipping_disputes')
    def test_analyze_shipping(self, mock_shipping):
        """Test shipping analysis endpoint."""
        mock_shipping.return_value = {
            "total_shipments": 2,
            "overall_performance": {"on_time_percentage": 85},
            "contract_compliance": {"meets_sla": True}
        }
        
        with TestClient(app) as client:
            request_data = {
                "tracking_numbers": ["123456789012", "123456789013"],
                "contract_terms": {"on_time_percentage": 90}
            }
            
            response = client.post("/analysis/shipping", json=request_data)
            
            assert response.status_code == 200
            data = response.json()
            assert "analysis" in data
            assert "processing_time_ms" in data


class TestRootEndpoint:
    """Test cases for root endpoint."""
    
    def test_root_endpoint(self):
        """Test root endpoint response."""
        with TestClient(app) as client:
            response = client.get("/")
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "Arbitrator AI" in data["message"]
            assert "version" in data
            assert "docs" in data
            assert "health" in data


if __name__ == "__main__":
    pytest.main([__file__])