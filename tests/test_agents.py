"""Unit tests for agent functionality."""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from app.agents.base_agent import BaseAgent
from app.agents.arbitrator_agent import ArbitratorAgent
from app.agents.legal_research_agent import LegalResearchAgent
from app.agents.negotiation_agent import NegotiationAgent
from app.core.rag_engine import RAGEngine


class TestAgent(BaseAgent):
    """Test implementation of BaseAgent for testing."""
    
    async def process(self, input_data):
        return {"test": "response"}
    
    def get_system_prompt(self):
        return "Test system prompt"


class TestBaseAgent:
    """Test cases for BaseAgent class."""
    
    def test_agent_initialization(self):
        """Test agent initialization."""
        model_config = {"provider": "test", "model": "test-model"}
        agent = TestAgent("TestAgent", model_config)
        
        assert agent.name == "TestAgent"
        assert agent.model_config == model_config
        assert isinstance(agent.created_at, datetime)
        assert len(agent.conversation_history) == 0
    
    def test_add_to_history(self):
        """Test adding messages to conversation history."""
        agent = TestAgent("TestAgent", {})
        
        agent.add_to_history("user", "Test message", {"test": "metadata"})
        
        assert len(agent.conversation_history) == 1
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[0]["content"] == "Test message"
        assert agent.conversation_history[0]["metadata"] == {"test": "metadata"}
    
    def test_clear_history(self):
        """Test clearing conversation history."""
        agent = TestAgent("TestAgent", {})
        
        agent.add_to_history("user", "Test message")
        assert len(agent.conversation_history) == 1
        
        agent.clear_history()
        assert len(agent.conversation_history) == 0
    
    @pytest.mark.asyncio
    async def test_process_method(self):
        """Test abstract process method implementation."""
        agent = TestAgent("TestAgent", {})
        result = await agent.process({"input": "test"})
        assert result == {"test": "response"}


class TestArbitratorAgent:
    """Test cases for ArbitratorAgent class."""
    
    @pytest.fixture
    def mock_rag_engine(self):
        """Create mock RAG engine."""
        rag_engine = Mock(spec=RAGEngine)
        rag_engine.query = AsyncMock(return_value=[
            {
                "id": "test_doc_1",
                "content": "Test contract clause",
                "metadata": {"source": "test_contract.pdf"},
                "similarity_score": 0.9
            }
        ])
        return rag_engine
    
    def test_arbitrator_initialization(self, mock_rag_engine):
        """Test ArbitratorAgent initialization."""
        model_config = {"provider": "anthropic", "model": "claude-3"}
        agent = ArbitratorAgent(model_config, mock_rag_engine)
        
        assert agent.name == "ArbitratorAgent"
        assert agent.rag_engine == mock_rag_engine
        assert agent.contract_analyzer is not None
    
    def test_system_prompt(self, mock_rag_engine):
        """Test system prompt generation."""
        agent = ArbitratorAgent({}, mock_rag_engine)
        prompt = agent.get_system_prompt()
        
        assert "arbitrator" in prompt.lower()
        assert "dispute resolution" in prompt.lower()
        assert "neutral" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_process_arbitration(self, mock_rag_engine):
        """Test arbitration processing."""
        agent = ArbitratorAgent({}, mock_rag_engine)
        
        # Mock contract analyzer
        agent.contract_analyzer.analyze_terms = AsyncMock(return_value={
            "contract_id": "test_contract",
            "key_terms_found": [],
            "risk_assessment": {"overall_risk_level": "low"}
        })
        
        input_data = {
            "dispute_details": "Payment dispute between parties",
            "contract_id": "test_contract"
        }
        
        result = await agent.process(input_data)
        
        assert "agent" in result
        assert result["agent"] == "ArbitratorAgent"
        assert "analysis" in result
        assert "relevant_clauses" in result
        
        # Verify RAG engine was called
        mock_rag_engine.query.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_error_handling(self, mock_rag_engine):
        """Test error handling in arbitration processing."""
        agent = ArbitratorAgent({}, mock_rag_engine)
        
        # Make RAG engine raise an exception
        mock_rag_engine.query.side_effect = Exception("RAG engine error")
        
        input_data = {
            "dispute_details": "Test dispute",
            "contract_id": "test_contract"
        }
        
        result = await agent.process(input_data)
        
        assert "error" in result
        assert "RAG engine error" in result["details"]


class TestLegalResearchAgent:
    """Test cases for LegalResearchAgent class."""
    
    @pytest.fixture
    def mock_rag_engine(self):
        """Create mock RAG engine."""
        rag_engine = Mock(spec=RAGEngine)
        rag_engine.query = AsyncMock(return_value=[
            {
                "id": "precedent_1",
                "content": "Legal precedent case",
                "metadata": {"source": "case_law.pdf"},
                "similarity_score": 0.85
            }
        ])
        return rag_engine
    
    def test_legal_research_initialization(self, mock_rag_engine):
        """Test LegalResearchAgent initialization."""
        model_config = {"provider": "openai", "model": "gpt-4"}
        agent = LegalResearchAgent(model_config, mock_rag_engine)
        
        assert agent.name == "LegalResearchAgent"
        assert agent.rag_engine == mock_rag_engine
    
    def test_system_prompt(self, mock_rag_engine):
        """Test system prompt generation."""
        agent = LegalResearchAgent({}, mock_rag_engine)
        prompt = agent.get_system_prompt()
        
        assert "legal research" in prompt.lower()
        assert "precedent" in prompt.lower()
        assert "case law" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_process_research(self, mock_rag_engine):
        """Test legal research processing."""
        agent = LegalResearchAgent({}, mock_rag_engine)
        
        input_data = {
            "query": "contract breach precedents",
            "jurisdiction": "US",
            "case_type": "commercial"
        }
        
        result = await agent.process(input_data)
        
        assert "agent" in result
        assert result["agent"] == "LegalResearchAgent"
        assert "precedents" in result
        assert "query" in result
        assert result["jurisdiction"] == "US"
        
        # Verify RAG engine was called with correct query
        mock_rag_engine.query.assert_called_once()
        call_args = mock_rag_engine.query.call_args[0]
        assert "contract breach precedents" in call_args[0]
        assert "US" in call_args[0]
        assert "commercial" in call_args[0]


class TestNegotiationAgent:
    """Test cases for NegotiationAgent class."""
    
    def test_negotiation_initialization(self):
        """Test NegotiationAgent initialization."""
        model_config = {"provider": "gemini", "model": "gemini-pro"}
        agent = NegotiationAgent(model_config)
        
        assert agent.name == "NegotiationAgent"
        assert len(agent.negotiation_strategies) == 5
        assert "collaborative" in agent.negotiation_strategies
    
    def test_system_prompt(self):
        """Test system prompt generation."""
        agent = NegotiationAgent({})
        prompt = agent.get_system_prompt()
        
        assert "negotiation" in prompt.lower()
        assert "settlement" in prompt.lower()
        assert "win-win" in prompt.lower()
    
    @pytest.mark.asyncio
    async def test_process_negotiation(self):
        """Test negotiation processing."""
        agent = NegotiationAgent({})
        
        input_data = {
            "parties": ["Company A", "Company B"],
            "dispute_summary": "Delivery delay dispute",
            "desired_outcomes": {
                "Company A": "Compensation for delays",
                "Company B": "Reduced penalties"
            }
        }
        
        result = await agent.process(input_data)
        
        assert "agent" in result
        assert result["agent"] == "NegotiationAgent"
        assert "position_analysis" in result
        assert "settlement_options" in result
        assert "negotiation_strategy" in result
    
    def test_analyze_positions(self):
        """Test position analysis method."""
        agent = NegotiationAgent({})
        
        parties = ["Party A", "Party B"]
        outcomes = {"Party A": "Goal A", "Party B": "Goal B"}
        
        analysis = agent._analyze_positions(parties, outcomes)
        
        assert "party_interests" in analysis
        assert "common_ground" in analysis
        assert "conflict_points" in analysis
        assert "leverage_analysis" in analysis
    
    def test_generate_settlement_options(self):
        """Test settlement options generation."""
        agent = NegotiationAgent({})
        
        dispute = "Payment timing dispute"
        outcomes = {"buyer": "Extended payment terms", "seller": "Guaranteed payment"}
        
        options = agent._generate_settlement_options(dispute, outcomes)
        
        assert isinstance(options, list)
        assert len(options) >= 2
        assert all("option" in opt for opt in options)
        assert all("description" in opt for opt in options)


if __name__ == "__main__":
    pytest.main([__file__])