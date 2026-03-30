"""Document processing utilities for RAG engine."""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import asyncio
from datetime import datetime
import json

try:
    import PyPDF2
except ImportError:
    PyPDF2 = None

try:
    from docx import Document
except ImportError:
    Document = None

logger = logging.getLogger(__name__)


class DocumentProcessor:
    """Process various document formats for RAG indexing."""
    
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.supported_formats = ['.pdf', '.txt', '.json', '.docx', '.md']
    
    async def process_directory(self, directory_path: str) -> List[Dict[str, Any]]:
        """Process all supported documents in a directory."""
        documents = []
        directory = Path(directory_path)
        
        if not directory.exists():
            logger.error(f"Directory does not exist: {directory_path}")
            return documents
        
        for file_path in directory.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in self.supported_formats:
                try:
                    doc_data = await self.process_file(str(file_path))
                    if doc_data:
                        documents.extend(doc_data)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {str(e)}")
        
        logger.info(f"Processed {len(documents)} document chunks from {directory_path}")
        return documents
    
    async def process_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Process a single file and return document chunks."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.error(f"File does not exist: {file_path}")
            return []
        
        file_extension = file_path.suffix.lower()
        
        try:
            if file_extension == '.pdf':
                content = await self._extract_pdf_content(file_path)
            elif file_extension == '.txt':
                content = await self._extract_text_content(file_path)
            elif file_extension == '.json':
                content = await self._extract_json_content(file_path)
            elif file_extension == '.docx':
                content = await self._extract_docx_content(file_path)
            elif file_extension == '.md':
                content = await self._extract_text_content(file_path)
            else:
                logger.warning(f"Unsupported file format: {file_extension}")
                return []
            
            if not content:
                logger.warning(f"No content extracted from {file_path}")
                return []
            
            # Split content into chunks
            chunks = self._split_text_into_chunks(content)
            
            # Create document objects
            documents = []
            for i, chunk in enumerate(chunks):
                doc = {
                    "id": f"{file_path.stem}_chunk_{i}",
                    "content": chunk,
                    "source": str(file_path),
                    "type": self._determine_document_type(file_path),
                    "metadata": {
                        "file_name": file_path.name,
                        "file_size": file_path.stat().st_size,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                        "processed_at": datetime.utcnow().isoformat()
                    }
                }
                documents.append(doc)
            
            return documents
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return []
    
    async def _extract_pdf_content(self, file_path: Path) -> str:
        """Extract text content from PDF file."""
        if PyPDF2 is None:
            raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")
        
        content = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                content += page.extract_text() + "\n"
        
        return content.strip()
    
    async def _extract_text_content(self, file_path: Path) -> str:
        """Extract content from text-based files."""
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    
    async def _extract_json_content(self, file_path: Path) -> str:
        """Extract content from JSON files."""
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
            # Convert JSON to readable text format
            return json.dumps(data, indent=2)
    
    async def _extract_docx_content(self, file_path: Path) -> str:
        """Extract content from DOCX files."""
        if Document is None:
            raise ImportError("python-docx not installed. Run: pip install python-docx")
        
        doc = Document(file_path)
        content = ""
        for paragraph in doc.paragraphs:
            content += paragraph.text + "\n"
        
        return content.strip()
    
    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            
            # Try to break at sentence boundaries
            if end < len(text):
                # Look for sentence endings near the chunk boundary
                for i in range(end, max(start + self.chunk_size // 2, end - 100), -1):
                    if text[i] in '.!?\n':
                        end = i + 1
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start >= len(text):
                break
        
        return chunks
    
    def _determine_document_type(self, file_path: Path) -> str:
        """Determine document type based on file name and content."""
        file_name_lower = file_path.name.lower()
        
        if any(keyword in file_name_lower for keyword in ['contract', 'agreement', 'terms']):
            return 'contract'
        elif any(keyword in file_name_lower for keyword in ['policy', 'procedure', 'guideline']):
            return 'policy'
        elif any(keyword in file_name_lower for keyword in ['case', 'precedent', 'ruling']):
            return 'legal_case'
        elif any(keyword in file_name_lower for keyword in ['regulation', 'statute', 'law']):
            return 'regulation'
        else:
            return 'document'