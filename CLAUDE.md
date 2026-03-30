# Arbitrator AI - Project Memory for Claude

## Project Overview

Arbitrator AI is a multi-agent system designed for commercial dispute resolution with RAG (Retrieval-Augmented Generation) capabilities. The system combines AI agents, external API integrations, and a comprehensive document processing pipeline to provide intelligent arbitration, legal research, and negotiation support.

## Architecture

### Core Components

1. **Multi-Agent System** (`/app/agents/`)
   - `ArbitratorAgent`: Main dispute resolution agent
   - `LegalResearchAgent`: Legal precedent and case law research
   - `NegotiationAgent`: Settlement facilitation and negotiation support
   - `BaseAgent`: Abstract base class for all agents

2. **RAG Engine** (`/app/core/`)
   - Vector database integration (ChromaDB)
   - Semantic search capabilities
   - Document embedding and retrieval
   - Collection management

3. **External Tools** (`/app/tools/`)
   - `ContractAnalyzer`: Contract term extraction and risk assessment
   - `WeatherAPI`: Weather data for shipping disputes
   - `ShippingTracker`: Logistics and delivery verification

4. **FastAPI Backend** (`/app/api/`)
   - RESTful API endpoints
   - Agent orchestration
   - Document management
   - Analysis services

### Key Features

- **Intelligent Document Processing**: Supports PDF, DOCX, TXT, JSON, and Markdown files
- **Semantic Search**: Vector-based document retrieval for context-aware responses
- **Multi-Modal Analysis**: Contract, weather, and shipping data integration
- **Comprehensive Testing**: Unit tests, integration tests, and API tests
- **Scalable Architecture**: Modular design with dependency injection

## File Structure

```
/arbitrator-ai/
├── app/
│   ├── agents/          # AI agent implementations
│   │   ├── base_agent.py
│   │   ├── arbitrator_agent.py
│   │   ├── legal_research_agent.py
│   │   └── negotiation_agent.py
│   ├── tools/           # External API integrations
│   │   ├── contract_analyzer.py
│   │   ├── weather_api.py
│   │   └── shipping_tracker.py
│   ├── core/            # RAG Engine and core functionality
│   │   ├── rag_engine.py
│   │   ├── document_processor.py
│   │   └── config.py
│   └── api/             # FastAPI endpoints
│       ├── main.py
│       └── routes/
│           ├── agents.py
│           ├── documents.py
│           ├── analysis.py
│           └── health.py
├── data/                # Document storage
│   ├── contracts/       # Contract documents
│   ├── legal_docs/      # Legal precedents and regulations
│   └── chroma_db/       # Vector database storage
├── tests/               # Comprehensive test suite
│   ├── test_agents.py
│   ├── test_tools.py
│   ├── test_api.py
│   └── conftest.py
├── .env                 # Environment configuration
└── CLAUDE.md           # This file
```

## Configuration

### Environment Variables

The system uses environment variables for configuration:

- **AI Model APIs**: Anthropic, OpenAI, Gemini API keys
- **RAG Configuration**: Embedding models, chunk sizes, collection settings
- **External APIs**: Weather API, shipping carrier APIs
- **Server Settings**: Host, port, CORS, authentication

### Model Configuration

Supports multiple AI providers:
- **Anthropic Claude**: Primary arbitration agent
- **OpenAI GPT**: Legal research and analysis
- **Google Gemini**: Negotiation and settlement

## API Endpoints

### Agent Endpoints (`/agents/`)
- `GET /agents/` - List available agents
- `POST /agents/arbitrator/process` - Process arbitration requests
- `POST /agents/legal_research/process` - Conduct legal research
- `POST /agents/negotiation/process` - Facilitate negotiations

### Document Management (`/documents/`)
- `GET /documents/` - List documents and collection stats
- `POST /documents/upload` - Upload and process documents
- `POST /documents/search` - Semantic document search
- `POST /documents/process_directory` - Batch process documents

### Analysis Services (`/analysis/`)
- `POST /analysis/contract` - Contract analysis and risk assessment
- `POST /analysis/weather` - Weather impact analysis
- `POST /analysis/shipping` - Shipping performance analysis
- `POST /analysis/comprehensive` - Multi-modal dispute analysis

### Health Monitoring (`/health/`)
- `GET /health/` - Basic health check
- `GET /health/detailed` - Comprehensive system status
- `GET /health/rag` - RAG engine status

## Development Guidelines

### Code Organization

1. **Agents**: Inherit from `BaseAgent`, implement `process()` and `get_system_prompt()`
2. **Tools**: Standalone classes with async methods for external API integration
3. **API Routes**: Use Pydantic models for request/response validation
4. **Configuration**: Centralized in `config.py` with environment variable support

### Testing Strategy

- **Unit Tests**: Individual component testing with mocks
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: FastAPI endpoint testing with TestClient
- **Fixtures**: Comprehensive test data and mock objects

### Dependencies

Key Python packages:
- `fastapi`: Web framework
- `chromadb`: Vector database
- `sentence-transformers`: Text embeddings
- `aiohttp`: Async HTTP client
- `pytest`: Testing framework
- `pydantic`: Data validation

## Usage Examples

### Starting the Server

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ANTHROPIC_API_KEY="your_key_here"
export OPENAI_API_KEY="your_key_here"

# Start the server
python -m app.api.main
```

### Processing a Dispute

```python
import requests

# Upload contract document
with open("contract.pdf", "rb") as f:
    response = requests.post(
        "http://localhost:8000/documents/upload",
        files={"file": f},
        data={"document_type": "contract"}
    )

# Process arbitration request
response = requests.post(
    "http://localhost:8000/agents/arbitrator/process",
    json={
        "dispute_details": "Payment delay dispute between Company A and Company B",
        "contract_id": "contract_123",
        "parties": ["Company A", "Company B"]
    }
)

print(response.json())
```

### Document Search

```python
# Search for relevant contract clauses
response = requests.post(
    "http://localhost:8000/documents/search",
    json={
        "query": "payment terms and late fees",
        "top_k": 5,
        "document_type": "contract"
    }
)

for doc in response.json()["documents"]:
    print(f"Score: {doc['similarity_score']:.2f}")
    print(f"Content: {doc['content'][:200]}...")
```

## Deployment Considerations

### Production Setup

1. **Environment Configuration**:
   - Set production API keys
   - Configure secure database connections
   - Enable authentication and rate limiting

2. **Scaling**:
   - Use container orchestration (Docker/Kubernetes)
   - Implement load balancing for API endpoints
   - Scale vector database for large document collections

3. **Monitoring**:
   - Health check endpoints for system monitoring
   - Logging configuration for debugging
   - Performance metrics collection

### Security

- API key authentication
- Input validation and sanitization
- Secure file upload handling
- Environment variable protection

## Future Enhancements

1. **Advanced Analytics**: Machine learning models for dispute outcome prediction
2. **Real-time Collaboration**: WebSocket support for multi-party negotiations
3. **Document Versioning**: Track contract amendments and changes
4. **Integration Expansion**: Additional shipping carriers, legal databases
5. **UI Dashboard**: Web interface for dispute management

## Troubleshooting

### Common Issues

1. **RAG Engine Initialization**: Check ChromaDB installation and permissions
2. **API Key Errors**: Verify environment variables are set correctly
3. **Document Processing**: Ensure supported file formats and sizes
4. **Performance**: Monitor embedding model performance and vector database size

### Debug Mode

Enable debug logging:
```bash
export LOG_LEVEL=DEBUG
export DEBUG_RAG_QUERIES=true
```

## Contributing

1. Follow the established code structure and patterns
2. Add comprehensive tests for new features
3. Update this documentation for significant changes
4. Use type hints and docstrings for all functions
5. Follow async/await patterns for I/O operations

---

*Last Updated: March 29, 2026*
*Version: 0.1.0*