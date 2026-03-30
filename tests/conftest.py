"""Pytest configuration and fixtures."""

import pytest
import asyncio
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock

from app.core.rag_engine import RAGEngine
from app.core.document_processor import DocumentProcessor
from app.core.config import Config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_contract_text():
    """Sample contract text for testing."""
    return """
    CONTRACT AGREEMENT
    
    This agreement is entered into between Party A and Party B.
    
    PAYMENT TERMS:
    Payment shall be made within 30 days of invoice receipt.
    Late payments will incur a penalty of 2% per month.
    
    DELIVERY TERMS:
    Goods shall be delivered within 14 business days of order confirmation.
    Delivery delays due to force majeure events are excused.
    
    LIABILITY:
    Liability is limited to the contract value.
    Neither party shall be liable for consequential damages.
    
    DISPUTE RESOLUTION:
    Any disputes shall be resolved through binding arbitration.
    The arbitration shall be conducted under the rules of the American Arbitration Association.
    
    TERMINATION:
    Either party may terminate this agreement with 30 days written notice.
    
    GOVERNING LAW:
    This agreement shall be governed by the laws of the State of New York.
    """


@pytest.fixture
def sample_documents():
    """Sample documents for RAG testing."""
    return [
        {
            "id": "contract_001",
            "content": "Payment terms require settlement within 30 days. Late fees apply after grace period.",
            "source": "contract_001.pdf",
            "type": "contract",
            "metadata": {
                "document_type": "contract",
                "parties": ["Company A", "Company B"],
                "date_created": "2024-01-15"
            }
        },
        {
            "id": "legal_case_001",
            "content": "In Smith v. Jones, the court held that material breach occurs when performance deviates substantially from contract terms.",
            "source": "case_law_001.pdf",
            "type": "legal_case",
            "metadata": {
                "document_type": "legal_case",
                "jurisdiction": "US",
                "court": "Supreme Court",
                "year": "2023"
            }
        },
        {
            "id": "regulation_001",
            "content": "Commercial contracts must include clear dispute resolution mechanisms as per Section 15.3 of the Commercial Code.",
            "source": "commercial_code.pdf",
            "type": "regulation",
            "metadata": {
                "document_type": "regulation",
                "jurisdiction": "Federal",
                "section": "15.3"
            }
        }
    ]


@pytest.fixture
def mock_rag_engine():
    """Mock RAG engine for testing."""
    mock_engine = Mock(spec=RAGEngine)
    mock_engine.initialize = AsyncMock()
    mock_engine.add_documents = AsyncMock(return_value=True)
    mock_engine.query = AsyncMock(return_value=[
        {
            "id": "test_doc_1",
            "content": "Test document content",
            "metadata": {"source": "test.pdf"},
            "similarity_score": 0.9
        }
    ])
    mock_engine.delete_documents = AsyncMock(return_value=True)
    mock_engine.get_collection_stats = AsyncMock(return_value={
        "collection_name": "test_collection",
        "document_count": 10,
        "embedding_model": "test_model"
    })
    mock_engine.reset_collection = AsyncMock(return_value=True)
    return mock_engine


@pytest.fixture
def mock_document_processor():
    """Mock document processor for testing."""
    mock_processor = Mock(spec=DocumentProcessor)
    mock_processor.supported_formats = ['.pdf', '.txt', '.json', '.docx', '.md']
    mock_processor.process_file = AsyncMock(return_value=[
        {
            "id": "test_chunk_1",
            "content": "Test document chunk content",
            "source": "test.pdf",
            "type": "contract",
            "metadata": {
                "file_name": "test.pdf",
                "chunk_index": 0,
                "total_chunks": 1
            }
        }
    ])
    mock_processor.process_directory = AsyncMock(return_value=[
        {
            "id": "dir_doc_1",
            "content": "Directory document content",
            "source": "dir/test.pdf",
            "type": "contract",
            "metadata": {"file_name": "test.pdf"}
        }
    ])
    return mock_processor


@pytest.fixture
def test_config(temp_directory):
    """Test configuration with temporary directories."""
    config = Config()
    config.data_dir = temp_directory / "data"
    config.contracts_dir = config.data_dir / "contracts"
    config.legal_docs_dir = config.data_dir / "legal_docs"
    config.temp_dir = config.data_dir / "temp"
    
    # Create directories
    for directory in [config.data_dir, config.contracts_dir, config.legal_docs_dir, config.temp_dir]:
        directory.mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def sample_weather_data():
    """Sample weather data for testing."""
    return {
        "location": "New York",
        "temperature": 15.5,
        "humidity": 65,
        "wind_speed": 8.2,
        "weather_main": "Rain",
        "weather_description": "light rain",
        "visibility": 8.5
    }


@pytest.fixture
def sample_tracking_data():
    """Sample shipping tracking data for testing."""
    return {
        "tracking_number": "123456789012",
        "carrier": "fedex",
        "status": "delivered",
        "delivery_date": "2024-01-20T14:30:00Z",
        "estimated_delivery": "2024-01-20T12:00:00Z",
        "tracking_events": [
            {
                "date": "2024-01-18T09:00:00Z",
                "status": "picked_up",
                "location": "Origin facility"
            },
            {
                "date": "2024-01-19T15:30:00Z",
                "status": "in_transit",
                "location": "Sorting facility"
            },
            {
                "date": "2024-01-20T14:30:00Z",
                "status": "delivered",
                "location": "Destination address"
            }
        ]
    }


@pytest.fixture
def api_test_headers():
    """Headers for API testing."""
    return {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }


# Pytest configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "api: mark test as API test"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        
        # Add api marker to API tests
        if "test_api" in item.nodeid:
            item.add_marker(pytest.mark.api)
        
        # Add slow marker to tests that might be slow
        if any(keyword in item.nodeid.lower() for keyword in ["comprehensive", "full", "large"]):
            item.add_marker(pytest.mark.slow)