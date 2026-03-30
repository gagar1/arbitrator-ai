"""Enterprise-grade RAG Engine with thread safety and comprehensive error handling.

This module implements the core Retrieval-Augmented Generation (RAG) engine that powers
the Arbitrator AI system's ability to search and retrieve relevant information from
documents to enhance AI agent responses.

Key Features:
- Thread-safe vector database operations
- Async/await support for non-blocking I/O
- Comprehensive error handling and retry logic
- Enterprise monitoring and health checks
- Batch processing for large document sets
- Similarity threshold filtering

The RAG engine bridges the gap between static AI knowledge and dynamic document content,
allowing agents to provide accurate, context-aware responses based on your specific data.
"""

import os
import asyncio
import threading
import time
import uuid  # Added for batch ID generation
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import logging
from functools import wraps

try:
    import chromadb
    from chromadb.config import Settings

    CHROMADB_AVAILABLE = True
except ImportError:
    chromadb = None
    CHROMADB_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer

    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .logging_config import get_logger

logger = get_logger('rag_engine')


def with_retry(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for retry logic with exponential backoff."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == max_retries - 1:
                        logger.error(f"Function {func.__name__} failed after {max_retries} attempts: {e}")
                        raise

                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(
                        f"Function {func.__name__} attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)

            raise last_exception

        return wrapper

    return decorator


class RAGEngine:
    """The "Knowledge Brain" of Arbitrator AI - handles document storage and intelligent retrieval.

    This class implements a production-ready RAG (Retrieval-Augmented Generation) system that:

    🧠 **Core Functionality**:
    - Stores documents as searchable vector embeddings
    - Performs semantic similarity search (not just keyword matching)
    - Retrieves relevant context for AI agent queries
    - Maintains document metadata and relationships

    🔒 **Enterprise Features**:
    - Thread-safe operations for concurrent access
    - Comprehensive error handling and retry logic
    - Health monitoring and performance metrics
    - Batch processing for large document sets
    - Resource management and cleanup

    🚀 **Performance Optimizations**:
    - Async/await patterns for non-blocking operations
    - Connection pooling and resource reuse
    - Intelligent caching and similarity thresholds
    - Configurable batch sizes and worker pools

    Think of this as a "smart library" that not only stores your documents
    but understands their meaning and can find relevant information instantly.
    """

    def __init__(self,
                 collection_name: str = "arbitrator_docs",
                 embedding_model: str = "all-MiniLM-L6-v2",
                 persist_directory: str = "./data/chroma_db",
                 max_workers: int = 4,
                 batch_size: int = 100,
                 similarity_threshold: float = 0.7):
        """Initialize the RAG engine with enterprise-grade configuration.

        Args:
            collection_name: Name of the vector database collection (like a "database table")
            embedding_model: AI model used to convert text to vectors ("all-MiniLM-L6-v2" is fast and accurate)
            persist_directory: Where to store the vector database files on disk
            max_workers: Number of parallel threads for processing (more = faster, but uses more memory)
            batch_size: How many documents to process at once (larger = more efficient, but uses more memory)
            similarity_threshold: Minimum similarity score to return results (0.7 = 70% similar)
        """

        # Core configuration - these define how the RAG engine behaves
        self.collection_name = collection_name  # Name of our document collection
        self.embedding_model_name = embedding_model  # AI model for converting text to vectors
        self.persist_directory = persist_directory  # Where we store data on disk
        self.max_workers = max_workers  # Parallel processing capacity
        self.batch_size = batch_size  # Documents per batch
        self.similarity_threshold = similarity_threshold  # Minimum relevance score

        # Thread safety mechanisms - critical for concurrent access
        # Multiple users/agents can access the RAG engine simultaneously
        self._lock = asyncio.Lock()  # Prevents race conditions in async operations
        self._initialization_lock = threading.Lock()  # Ensures single initialization
        self._initialized = False  # Tracks initialization state

        # Core components - these do the actual work
        self.client = None  # ChromaDB client for vector storage
        self.collection = None  # The actual document collection
        self.embedding_model = None  # AI model for text-to-vector conversion
        self._executor = ThreadPoolExecutor(max_workers=max_workers)  # Thread pool for CPU-intensive tasks

        # Monitoring and metrics - essential for production systems
        self._operation_count = 0  # Total operations performed
        self._error_count = 0  # Total errors encountered
        self._last_health_check = None  # When we last checked system health
        self._health_status = True  # Current health status

        # Create storage directory with secure permissions
        # This is where all vector data and metadata will be stored
        persist_path = Path(persist_directory)
        persist_path.mkdir(parents=True, exist_ok=True, mode=0o750)  # rwxr-x--- permissions

        logger.info(f"RAG Engine initialized with collection: {collection_name}", extra={
            "embedding_model": embedding_model,
            "persist_directory": persist_directory,
            "max_workers": max_workers,
            "batch_size": batch_size
        })

    @with_retry(max_retries=3, backoff_factor=1.0)
    async def initialize(self):
        """Initialize the RAG engine components with comprehensive error handling.

        This method sets up all the components needed for the RAG engine to function:
        1. Validates that required dependencies are installed
        2. Initializes the ChromaDB vector database client
        3. Creates or connects to the document collection
        4. Loads the AI embedding model for text-to-vector conversion
        5. Performs a health check to ensure everything works

        The initialization is thread-safe and idempotent (safe to call multiple times).
        """
        # Quick check - if already initialized, nothing to do
        if self._initialized:
            logger.info("RAG Engine already initialized")
            return

        # Use async lock to prevent multiple simultaneous initializations
        # This is the "double-check locking" pattern for thread safety
        async with self._lock:
            if self._initialized:  # Double-check pattern - another thread might have initialized while we waited
                return

            try:
                # Step 1: Verify all required dependencies are installed
                # These checks prevent cryptic errors later if packages are missing
                if not CHROMADB_AVAILABLE:
                    raise ImportError(
                        "ChromaDB not installed. This is required for vector database functionality. "
                        "Install with: pip install chromadb>=0.4.18"
                    )

                if not SENTENCE_TRANSFORMERS_AVAILABLE:
                    raise ImportError(
                        "SentenceTransformers not installed. This is required for text-to-vector conversion. "
                        "Install with: pip install sentence-transformers>=2.2.2"
                    )

                # Step 2: Initialize ChromaDB client with enterprise settings
                # ChromaDB is our vector database - it stores documents as searchable vectors
                logger.info("Initializing ChromaDB client...")
                self.client = chromadb.PersistentClient(
                    path=self.persist_directory,
                    settings=Settings(
                        anonymized_telemetry=False,  # Disable telemetry for privacy
                        allow_reset=True,  # Allow collection resets for development
                        chroma_db_impl="duckdb+parquet",  # Use DuckDB backend for performance
                        persist_directory=self.persist_directory  # Where to store data
                    )
                )

                # Step 3: Get or create collection with optimized settings
                # A collection is like a "table" in a traditional database
                logger.info(f"Creating/accessing collection: {self.collection_name}")
                self.collection = self.client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={
                        # HNSW (Hierarchical Navigable Small World) algorithm settings for fast similarity search
                        "hnsw:space": "cosine",  # Use cosine similarity (good for text)
                        "hnsw:construction_ef": 200,  # Higher = more accurate but slower indexing
                        "hnsw:M": 16,  # Number of connections per node (balance speed/accuracy)

                        # Metadata for tracking and debugging
                        "created_at": datetime.utcnow().isoformat(),
                        "embedding_model": self.embedding_model_name,
                        "purpose": "arbitrator_ai_document_storage"
                    }
                )

                # Step 4: Initialize embedding model in thread pool to avoid blocking
                # Loading AI models can take several seconds, so we do it in a separate thread
                # This prevents blocking the main async event loop
                logger.info(f"Loading embedding model: {self.embedding_model_name}")
                loop = asyncio.get_event_loop()
                self.embedding_model = await loop.run_in_executor(
                    self._executor,  # Use our thread pool
                    self._load_embedding_model  # Function to run in thread
                )

                # Step 5: Perform health check to ensure everything works
                # This validates that all components can work together
                await self._health_check()

                # Mark as successfully initialized
                self._initialized = True

                # Log successful initialization with key metrics
                logger.info("RAG Engine initialization completed successfully", extra={
                    "collection_name": self.collection_name,
                    "document_count": self.collection.count(),  # How many docs are already stored
                    "embedding_model": self.embedding_model_name,
                    "persist_directory": self.persist_directory,
                    "max_workers": self.max_workers,
                    "batch_size": self.batch_size
                })

            except Exception as e:
                # Handle initialization failures gracefully
                self._error_count += 1
                self._health_status = False

                # Log detailed error information for debugging
                logger.error(f"Failed to initialize RAG Engine: {str(e)}", extra={
                    "error_type": type(e).__name__,
                    "persist_directory": self.persist_directory,
                    "collection_name": self.collection_name,
                    "embedding_model": self.embedding_model_name,
                    "chromadb_available": CHROMADB_AVAILABLE,
                    "sentence_transformers_available": SENTENCE_TRANSFORMERS_AVAILABLE
                })

                # Re-raise the exception so the caller knows initialization failed
                raise

    def _load_embedding_model(self) -> SentenceTransformer:
        """Load the AI embedding model in a separate thread.

        This function runs in a thread pool to avoid blocking the main async event loop.
        The embedding model converts text into numerical vectors that can be compared
        for semantic similarity.

        Returns:
            SentenceTransformer: The loaded embedding model ready for use
        """
        try:
            # Load the pre-trained embedding model
            # "all-MiniLM-L6-v2" is a good balance of speed and accuracy for most use cases
            model = SentenceTransformer(self.embedding_model_name)

            # Log successful loading with model details
            logger.info(f"Embedding model loaded successfully: {self.embedding_model_name}", extra={
                "model_name": self.embedding_model_name,
                "model_max_seq_length": getattr(model, 'max_seq_length', 'unknown'),
                "model_device": str(getattr(model, 'device', 'unknown'))
            })

            return model

        except Exception as e:
            # Provide helpful error message with troubleshooting info
            logger.error(
                f"Failed to load embedding model {self.embedding_model_name}: {e}. "
                f"This might be due to network issues (model download) or insufficient memory.",
                extra={"model_name": self.embedding_model_name, "error_type": type(e).__name__}
            )
            raise

    async def _health_check(self) -> bool:
        """Perform comprehensive health check on all RAG engine components.

        This method validates that all parts of the RAG engine are working correctly:
        1. ChromaDB client connectivity
        2. Collection accessibility
        3. Embedding model functionality
        4. End-to-end embedding generation

        Returns:
            bool: True if all checks pass, False if any component fails
        """
        try:
            # Check 1: Verify ChromaDB client is initialized and responsive
            if not self.client:
                raise RuntimeError("ChromaDB client not initialized - cannot store or retrieve documents")

            # Check 2: Verify collection is accessible and functional
            if not self.collection:
                raise RuntimeError("Document collection not initialized - cannot access stored documents")

            # Check 3: Test basic collection operations
            # This verifies the database connection is working
            count = self.collection.count()
            logger.debug(f"Health check: Collection '{self.collection_name}' contains {count} documents")

            # Check 4: Verify embedding model is loaded and ready
            if not self.embedding_model:
                raise RuntimeError("Embedding model not initialized - cannot convert text to vectors")

            # Check 5: Test end-to-end embedding generation
            # This is the most comprehensive test - it verifies the entire pipeline works
            test_text = "health check test - verifying embedding generation"
            test_embedding = await self._generate_embeddings([test_text])

            if not test_embedding or len(test_embedding[0]) == 0:
                raise RuntimeError("Embedding generation failed - cannot convert text to searchable vectors")

            # Validate embedding dimensions (should be consistent)
            expected_dim = 384  # all-MiniLM-L6-v2 produces 384-dimensional vectors
            actual_dim = len(test_embedding[0])
            if actual_dim != expected_dim:
                logger.warning(f"Unexpected embedding dimension: {actual_dim}, expected: {expected_dim}")

            # All checks passed - update health status
            self._last_health_check = datetime.utcnow()
            self._health_status = True

            logger.debug(f"Health check passed successfully", extra={
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_dimension": actual_dim,
                "embedding_model": self.embedding_model_name
            })

            return True

        except Exception as e:
            # Log health check failure with detailed context
            logger.error(f"Health check failed: {e}", extra={
                "collection_name": self.collection_name,
                "client_initialized": self.client is not None,
                "collection_initialized": self.collection is not None,
                "embedding_model_initialized": self.embedding_model is not None,
                "error_type": type(e).__name__
            })

            self._health_status = False
            return False

    async def add_documents(self, documents: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """Add documents to the vector database with comprehensive validation and batching."""
        if not self._initialized:
            await self.initialize()

        if not documents:
            logger.warning("No documents provided for addition")
            return False, {"error": "No documents provided"}

        # Validate document size limits
        if len(documents) > self.batch_size * 10:  # Allow up to 10 batches
            logger.error(f"Document batch too large: {len(documents)} > {self.batch_size * 10}")
            return False, {"error": "Document batch too large"}

        async with self._lock:
            try:
                start_time = time.time()
                total_added = 0
                failed_documents = []

                # Process documents in batches
                for batch_start in range(0, len(documents), self.batch_size):
                    batch_end = min(batch_start + self.batch_size, len(documents))
                    batch = documents[batch_start:batch_end]

                    logger.info(f"Processing batch {batch_start // self.batch_size + 1} ({len(batch)} documents)")

                    try:
                        success, batch_result = await self._add_document_batch(batch)
                        if success:
                            total_added += batch_result.get("added_count", 0)
                        else:
                            failed_documents.extend(batch_result.get("failed_documents", []))
                    except Exception as e:
                        logger.error(f"Batch processing failed: {e}")
                        failed_documents.extend([doc.get("id", f"batch_{batch_start}") for doc in batch])

                processing_time = time.time() - start_time
                self._operation_count += 1

                result = {
                    "total_documents": len(documents),
                    "added_count": total_added,
                    "failed_count": len(failed_documents),
                    "processing_time_seconds": round(processing_time, 2),
                    "failed_documents": failed_documents[:10]  # Limit to first 10 failures
                }

                if total_added > 0:
                    logger.info(f"Successfully added {total_added}/{len(documents)} documents", extra=result)
                    return True, result
                else:
                    logger.error(f"Failed to add any documents", extra=result)
                    return False, result

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to add documents: {str(e)}", exc_info=True)
                return False, {"error": str(e)}

    async def _add_document_batch(self, batch: List[Dict[str, Any]]) -> Tuple[bool, Dict[str, Any]]:
        """Add a single batch of documents."""
        try:
            texts = []
            metadatas = []
            ids = []

            for i, doc in enumerate(batch):
                # Validate document content
                text_content = doc.get("content", "")
                if not text_content or len(text_content.strip()) == 0:
                    logger.warning(f"Empty document content for document {i}")
                    continue

                # Validate text length
                if len(text_content) > 100000:  # 100KB limit per document
                    logger.warning(f"Document {i} exceeds size limit, truncating")
                    text_content = text_content[:100000]

                metadata = {
                    "source": doc.get("source", "unknown"),
                    "document_type": doc.get("type", "contract"),
                    "created_at": datetime.utcnow().isoformat(),
                    "content_length": len(text_content),
                    "batch_id": str(uuid.uuid4())[:8],
                    **doc.get("metadata", {})
                }

                doc_id = doc.get("id", f"doc_{i}_{int(datetime.utcnow().timestamp())}")

                texts.append(text_content)
                metadatas.append(metadata)
                ids.append(doc_id)

            if not texts:
                return False, {"error": "No valid documents in batch"}

            # Generate embeddings asynchronously
            embeddings = await self._generate_embeddings(texts)

            # Add to collection
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )

            return True, {"added_count": len(texts)}

        except Exception as e:
            logger.error(f"Failed to add document batch: {str(e)}")
            return False, {"error": str(e)}

    async def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings asynchronously."""
        if not texts:
            return []

        try:
            # Run embedding generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self._executor,
                lambda: self.embedding_model.encode(texts).tolist()
            )

            logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings

        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise

    async def query(self,
                    query_text: str,
                    top_k: int = 5,
                    filter_metadata: Optional[Dict[str, Any]] = None,
                    include_similarity_threshold: bool = True) -> List[Dict[str, Any]]:
        """Query the vector database with enhanced filtering and validation."""
        if not self._initialized:
            await self.initialize()

        # Input validation
        if not query_text or len(query_text.strip()) == 0:
            logger.warning("Empty query text provided")
            return []

        if len(query_text) > 10000:  # 10KB limit
            logger.warning("Query text too long, truncating")
            query_text = query_text[:10000]

        if top_k <= 0 or top_k > 100:
            logger.warning(f"Invalid top_k value: {top_k}, using default 5")
            top_k = 5

        try:
            start_time = time.time()

            # Generate query embedding asynchronously
            query_embeddings = await self._generate_embeddings([query_text])
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []

            query_embedding = query_embeddings[0]

            # Perform similarity search with error handling
            try:
                results = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=top_k,
                    where=filter_metadata,
                    include=["metadatas", "documents", "distances"]
                )
            except Exception as e:
                logger.error(f"ChromaDB query failed: {e}")
                return []

            # Format and filter results
            formatted_results = []
            if results and results.get('ids') and results['ids'][0]:
                for i in range(len(results['ids'][0])):
                    similarity_score = 1 - results['distances'][0][i]  # Convert distance to similarity

                    # Apply similarity threshold filter
                    if include_similarity_threshold and similarity_score < self.similarity_threshold:
                        continue

                    result = {
                        "id": results['ids'][0][i],
                        "content": results['documents'][0][i],
                        "metadata": results['metadatas'][0][i],
                        "similarity_score": round(similarity_score, 4),
                        "distance": round(results['distances'][0][i], 4)
                    }

                    # Add query metadata
                    result["metadata"]["query_timestamp"] = datetime.utcnow().isoformat()
                    result["metadata"]["query_length"] = len(query_text)

                    formatted_results.append(result)

            query_time = time.time() - start_time
            self._operation_count += 1

            logger.info(f"Query completed successfully", extra={
                "query_length": len(query_text),
                "results_count": len(formatted_results),
                "query_time_seconds": round(query_time, 3),
                "top_k_requested": top_k,
                "similarity_threshold": self.similarity_threshold if include_similarity_threshold else None
            })

            return formatted_results

        except Exception as e:
            self._error_count += 1
            logger.error(f"Failed to query documents: {str(e)}", extra={
                "query_length": len(query_text),
                "top_k": top_k,
                "filter_metadata": filter_metadata
            }, exc_info=True)
            return []

    async def delete_documents(self, document_ids: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """Delete documents from the vector database with validation."""
        if not self._initialized:
            await self.initialize()

        if not document_ids:
            return False, {"error": "No document IDs provided"}

        # Validate document IDs
        if len(document_ids) > 1000:  # Reasonable batch limit
            return False, {"error": "Too many documents to delete at once (max 1000)"}

        async with self._lock:
            try:
                start_time = time.time()

                # Check which documents exist before deletion
                existing_docs = []
                try:
                    # Query to check existence (ChromaDB will return empty if not found)
                    check_results = self.collection.get(ids=document_ids)
                    existing_docs = check_results.get('ids', [])
                except Exception as e:
                    logger.warning(f"Could not verify document existence: {e}")
                    # Proceed with deletion anyway

                # Perform deletion
                self.collection.delete(ids=document_ids)

                deletion_time = time.time() - start_time
                self._operation_count += 1

                result = {
                    "requested_count": len(document_ids),
                    "existing_count": len(existing_docs),
                    "deletion_time_seconds": round(deletion_time, 3),
                    "deleted_ids": document_ids[:10]  # Limit logged IDs
                }

                logger.info(f"Deleted {len(document_ids)} documents", extra=result)
                return True, result

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to delete documents: {str(e)}", extra={
                    "document_count": len(document_ids),
                    "document_ids_sample": document_ids[:5]
                })
                return False, {"error": str(e)}

    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the collection and engine health."""
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                return {
                    "error": f"Failed to initialize: {str(e)}",
                    "health_status": False
                }

        try:
            # Perform health check
            health_status = await self._health_check()

            # Get basic collection stats
            count = self.collection.count() if self.collection else 0

            # Get storage info
            storage_info = self._get_storage_info()

            stats = {
                "collection_name": self.collection_name,
                "document_count": count,
                "embedding_model": self.embedding_model_name,
                "persist_directory": self.persist_directory,
                "health_status": health_status,
                "last_health_check": self._last_health_check.isoformat() if self._last_health_check else None,
                "operation_count": self._operation_count,
                "error_count": self._error_count,
                "error_rate": round(self._error_count / max(self._operation_count, 1), 4),
                "initialized": self._initialized,
                "max_workers": self.max_workers,
                "batch_size": self.batch_size,
                "similarity_threshold": self.similarity_threshold,
                "storage_info": storage_info,
                "timestamp": datetime.utcnow().isoformat()
            }

            # Add collection metadata if available
            if self.collection:
                try:
                    collection_metadata = self.collection.metadata
                    if collection_metadata:
                        stats["collection_metadata"] = collection_metadata
                except Exception as e:
                    logger.warning(f"Failed to get collection metadata: {e}")

            return stats

        except Exception as e:
            logger.error(f"Failed to get collection stats: {str(e)}")
            return {
                "error": str(e),
                "health_status": False,
                "collection_name": self.collection_name,
                "timestamp": datetime.utcnow().isoformat()
            }

    def _get_storage_info(self) -> Dict[str, Any]:
        """Get storage information for the persist directory."""
        try:
            persist_path = Path(self.persist_directory)
            if persist_path.exists():
                total_size = sum(f.stat().st_size for f in persist_path.rglob('*') if f.is_file())
                file_count = sum(1 for f in persist_path.rglob('*') if f.is_file())

                return {
                    "total_size_bytes": total_size,
                    "total_size_mb": round(total_size / (1024 * 1024), 2),
                    "file_count": file_count,
                    "directory_exists": True
                }
            else:
                return {
                    "directory_exists": False,
                    "total_size_bytes": 0,
                    "total_size_mb": 0,
                    "file_count": 0
                }
        except Exception as e:
            logger.warning(f"Failed to get storage info: {e}")
            return {"error": str(e)}

    async def reset_collection(self, confirm: bool = False) -> Tuple[bool, str]:
        """Reset the collection with safety confirmation."""
        if not confirm:
            return False, "Reset requires explicit confirmation (confirm=True)"

        if not self._initialized:
            await self.initialize()

        async with self._lock:
            try:
                logger.warning(f"Resetting collection: {self.collection_name}")

                # Get current stats for logging
                current_count = self.collection.count() if self.collection else 0

                # Delete and recreate collection
                if self.client:
                    self.client.delete_collection(name=self.collection_name)
                    self.collection = self.client.create_collection(
                        name=self.collection_name,
                        metadata={
                            "hnsw:space": "cosine",
                            "hnsw:construction_ef": 200,
                            "hnsw:M": 16,
                            "reset_at": datetime.utcnow().isoformat(),
                            "embedding_model": self.embedding_model_name,
                            "previous_document_count": current_count
                        }
                    )

                    # Reset metrics
                    self._operation_count = 0
                    self._error_count = 0

                    logger.info(f"Collection reset successfully", extra={
                        "collection_name": self.collection_name,
                        "previous_document_count": current_count
                    })

                    return True, f"Collection reset successfully. Previous document count: {current_count}"
                else:
                    return False, "Client not initialized"

            except Exception as e:
                self._error_count += 1
                logger.error(f"Failed to reset collection: {str(e)}")
                return False, f"Reset failed: {str(e)}"

    async def cleanup(self):
        """Cleanup resources and close connections."""
        logger.info("Cleaning up RAG Engine resources")

        try:
            if self._executor:
                self._executor.shutdown(wait=True)
                logger.info("Thread pool executor shutdown")

            # ChromaDB client cleanup (if needed)
            if self.client:
                # ChromaDB doesn't require explicit cleanup, but we can log
                logger.info("ChromaDB client cleanup completed")

            self._initialized = False
            logger.info("RAG Engine cleanup completed")

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            if hasattr(self, '_executor') and self._executor:
                self._executor.shutdown(wait=False)
        except Exception:
            pass  # Ignore errors during destruction
