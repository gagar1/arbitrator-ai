# Arbitrator AI

> Multi-agent system for commercial dispute resolution with RAG capabilities

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](#testing)

Arbitrator AI is an intelligent dispute resolution system that combines multiple AI agents, document analysis, and external data integration to provide comprehensive arbitration, legal research, and negotiation support for commercial disputes.

## 🚀 Features

- **Multi-Agent Architecture**: Specialized AI agents for arbitration, legal research, and negotiation
- **RAG-Powered Analysis**: Semantic search and retrieval from contract documents and legal precedents
- **Contract Intelligence**: Automated contract analysis, risk assessment, and obligation extraction
- **External Data Integration**: Weather data for shipping disputes, logistics tracking, and delivery verification
- **Comprehensive API**: RESTful endpoints for all system functionality
- **Document Processing**: Support for PDF, DOCX, TXT, JSON, and Markdown files
- **Real-time Analysis**: Fast processing with async architecture

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Architecture](#-architecture)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

## 🚀 Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/arbitrator-ai.git
   cd arbitrator-ai
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Start the server**
   ```bash
   python -m app.api.main
   ```

5. **Access the API documentation**
   - Open http://localhost:8000/docs for interactive API docs
   - Or visit http://localhost:8000/redoc for alternative documentation

## 📦 Installation

### Prerequisites

- Python 3.9 or higher
- pip package manager
- At least 4GB RAM (for embedding models)
- 2GB free disk space (for vector database)

### Standard Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install additional AI model packages (optional)
pip install anthropic openai google-generativeai
```

### Docker Installation

```bash
# Build the container
docker build -t arbitrator-ai .

# Run with environment file
docker run -p 8000:8000 --env-file .env arbitrator-ai
```

### Development Installation

```bash
# Install with development dependencies
pip install -r requirements.txt
pip install -e .

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# AI Model API Keys
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key
GEMINI_API_KEY=your_gemini_key

# External API Keys
WEATHER_API_KEY=your_openweathermap_key

# Server Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_KEY=your_api_key_for_authentication

# RAG Configuration
RAG_COLLECTION_NAME=arbitrator_docs
RAG_EMBEDDING_MODEL=all-MiniLM-L6-v2
RAG_CHUNK_SIZE=1000
```

### Model Configuration

The system supports multiple AI providers:

- **Anthropic Claude**: Best for arbitration and legal reasoning
- **OpenAI GPT**: Excellent for research and analysis
- **Google Gemini**: Good for negotiation and creative solutions

## 📖 Usage

### Basic Workflow

1. **Upload Documents**
   ```python
   import requests
   
   # Upload a contract
   with open("contract.pdf", "rb") as f:
       response = requests.post(
           "http://localhost:8000/documents/upload",
           files={"file": f},
           data={"document_type": "contract"}
       )
   ```

2. **Process Dispute**
   ```python
   # Submit arbitration request
   response = requests.post(
       "http://localhost:8000/agents/arbitrator/process",
       json={
           "dispute_details": "Payment delay dispute",
           "contract_id": "contract_123",
           "parties": ["Company A", "Company B"]
       }
   )
   
   result = response.json()
   print(result["response"]["recommendation"])
   ```

3. **Search Documents**
   ```python
   # Find relevant contract clauses
   response = requests.post(
       "http://localhost:8000/documents/search",
       json={
           "query": "payment terms and penalties",
           "top_k": 5
       }
   )
   ```

### Advanced Features

#### Comprehensive Analysis

```python
# Multi-modal dispute analysis
response = requests.post(
    "http://localhost:8000/analysis/comprehensive",
    json={
        "dispute_id": "DISP-2024-001",
        "contract_id": "contract_123",
        "tracking_numbers": ["1Z999AA1234567890"],
        "incident_location": "New York",
        "incident_date": "2024-01-15T00:00:00Z",
        "analysis_scope": ["contract", "shipping", "weather"]
    }
)
```

#### Legal Research

```python
# Research legal precedents
response = requests.post(
    "http://localhost:8000/agents/legal_research/process",
    json={
        "query": "force majeure weather delays shipping",
        "jurisdiction": "US",
        "case_type": "commercial"
    }
)
```

## 📚 API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health/` | GET | System health check |
| `/agents/` | GET | List available agents |
| `/documents/upload` | POST | Upload and process documents |
| `/documents/search` | POST | Semantic document search |
| `/analysis/contract` | POST | Contract analysis |
| `/analysis/comprehensive` | POST | Multi-modal analysis |

### Agent Endpoints

- **Arbitrator Agent**: `/agents/arbitrator/process`
  - Processes dispute details and contract information
  - Returns arbitration recommendations and legal reasoning

- **Legal Research Agent**: `/agents/legal_research/process`
  - Searches legal precedents and case law
  - Provides jurisdiction-specific analysis

- **Negotiation Agent**: `/agents/negotiation/process`
  - Facilitates settlement discussions
  - Generates win-win solution proposals

### Analysis Tools

- **Contract Analyzer**: Extract terms, assess risks, identify obligations
- **Weather API**: Historical weather data for shipping disputes
- **Shipping Tracker**: Delivery verification and performance analysis

For complete API documentation, visit `/docs` when the server is running.

## 🏗️ Architecture

### System Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   AI Agents     │    │   External      │
│   REST API      │◄──►│   - Arbitrator  │◄──►│   APIs          │
│                 │    │   - Legal       │    │   - Weather     │
│                 │    │   - Negotiation │    │   - Shipping    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Document      │    │   RAG Engine    │
│   Processor     │◄──►│   - ChromaDB    │
│   - PDF/DOCX    │    │   - Embeddings  │
│   - Text/JSON   │    │   - Search      │
└─────────────────┘    └─────────────────┘
```

### Key Components

1. **Multi-Agent System**: Specialized AI agents for different aspects of dispute resolution
2. **RAG Engine**: Vector database with semantic search capabilities
3. **Document Processor**: Handles multiple file formats and chunking strategies
4. **External Integrations**: Weather data, shipping tracking, and other APIs
5. **FastAPI Backend**: RESTful API with automatic documentation

### Data Flow

1. Documents are uploaded and processed into chunks
2. Chunks are embedded and stored in vector database
3. User queries trigger semantic search for relevant context
4. AI agents process queries with retrieved context
5. External APIs provide additional data when needed
6. Results are returned with reasoning and recommendations

## 🧪 Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app

# Run specific test categories
pytest -m "not slow"  # Skip slow tests
pytest tests/test_agents.py  # Test specific module
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **API Tests**: FastAPI endpoint testing
- **Performance Tests**: Load and stress testing

### Test Data

The test suite includes:
- Sample contracts and legal documents
- Mock API responses for external services
- Comprehensive fixtures for different scenarios

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run the test suite
5. Submit a pull request

### Code Standards

- Follow PEP 8 style guidelines
- Use type hints for all functions
- Write comprehensive docstrings
- Maintain test coverage above 90%
- Use async/await for I/O operations

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the `/docs` endpoint when running the server
- **Issues**: Report bugs and feature requests on GitHub
- **Discussions**: Join our community discussions
- **Email**: Contact us at support@arbitrator-ai.com

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vector database powered by [ChromaDB](https://www.trychroma.com/)
- Embeddings by [Sentence Transformers](https://www.sbert.net/)
- AI models from Anthropic, OpenAI, and Google

---

**Arbitrator AI** - Intelligent dispute resolution for the modern world.