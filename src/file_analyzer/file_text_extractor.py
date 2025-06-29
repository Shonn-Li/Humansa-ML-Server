"""
File Text Extractor for YouWoAI ML Server

This module provides text extraction capabilities for various file types
including PDF, PPTX (PowerPoint), images, and other document formats.
"""

import os
import logging
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)

# Import LlamaIndex file readers
try:
    from llama_index.readers.file import PDFReader
    LLAMAINDEX_PDF_READER_AVAILABLE = True
except ImportError:
    LLAMAINDEX_PDF_READER_AVAILABLE = False
    logger.warning("LlamaIndex PDFReader not available")

# Import PyPDF2 fallback
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    logger.warning("PyPDF2 not available")

# Import python-pptx for PowerPoint processing
try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    PPTX_AVAILABLE = False
    logger.warning("python-pptx not available - PPTX processing disabled")

# Import PIL for basic image processing
try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - image processing disabled")

# Import Azure Inference for image text extraction
try:
    from llama_index.llms.azure_inference import AzureAICompletionsModel
    from llama_index.core.base.llms.types import ChatMessage, ImageBlock, TextBlock
    AZURE_INFERENCE_AVAILABLE = True
except ImportError:
    AZURE_INFERENCE_AVAILABLE = False
    logger.warning("Azure Inference not available - image text extraction disabled")


class FileTextExtractor:
    """Extract text from various file types"""
    
    def __init__(self):
        """Initialize the file text extractor"""
        self.supported_types = self._get_supported_types()
        logger.info(f"FileTextExtractor initialized with support for: {', '.join(self.supported_types)}")
    
    def _get_supported_types(self) -> list:
        """Get list of supported file types based on available libraries"""
        types = []
        
        if LLAMAINDEX_PDF_READER_AVAILABLE or PYPDF2_AVAILABLE:
            types.append('pdf')
        
        if PPTX_AVAILABLE:
            types.append('pptx')
        
        if AZURE_INFERENCE_AVAILABLE and PIL_AVAILABLE:
            types.extend(['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'])
        
        return types
    
    def extract_text_from_file(self, file_path: str, file_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract text from a file
        
        Args:
            file_path: Path to the file (local path or URL)
            file_type: Optional file type hint (pdf, pptx, jpg, etc.)
            
        Returns:
            Dict containing:
            - success: bool
            - text: str (extracted text)
            - file_type: str (detected file type)
            - error: str (if extraction failed)
            - metadata: dict (additional info)
        """
        try:
            # Download file if it's a URL
            if file_path.startswith(('http://', 'https://')):
                file_path = self._download_file(file_path)
                if not file_path:
                    return {
                        'success': False,
                        'error': 'Failed to download file',
                        'text': '',
                        'file_type': file_type or 'unknown'
                    }
            
            # Detect file type if not provided
            if not file_type:
                file_type = self._detect_file_type(file_path)
            
            # Extract text based on file type
            if file_type == 'pdf':
                return self._extract_pdf_text(file_path)
            elif file_type == 'pptx':
                return self._extract_pptx_text(file_path)
            elif file_type in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
                return self._extract_image_text(file_path)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported file type: {file_type}',
                    'text': '',
                    'file_type': file_type,
                    'supported_types': self.supported_types
                }
                
        except Exception as e:
            logger.error(f"Error extracting text from file {file_path}: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'file_type': file_type or 'unknown'
            }
    
    def _download_file(self, url: str) -> Optional[str]:
        """Download file from URL to temporary location"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Error downloading file from {url}: {e}")
            return None
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from file extension"""
        path = Path(file_path)
        extension = path.suffix.lower().lstrip('.')
        
        # Map common extensions
        type_mapping = {
            'pdf': 'pdf',
            'ppt': 'pptx',
            'pptx': 'pptx',
            'jpg': 'jpg',
            'jpeg': 'jpeg',
            'png': 'png',
            'gif': 'gif',
            'bmp': 'bmp',
            'webp': 'webp'
        }
        
        return type_mapping.get(extension, 'unknown')
    
    def _extract_pdf_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PDF file"""
        # Try LlamaIndex PDFReader first
        if LLAMAINDEX_PDF_READER_AVAILABLE:
            try:
                logger.info(f"Using LlamaIndex PDFReader for: {file_path}")
                pdf_reader = PDFReader()
                documents = pdf_reader.load_data(file=Path(file_path))
                
                text = "\n\n".join([doc.text for doc in documents])
                logger.info(f"✅ LlamaIndex PDF extraction successful: {len(text)} chars")
                
                return {
                    'success': True,
                    'text': text.strip(),
                    'file_type': 'pdf',
                    'metadata': {
                        'extractor': 'llamaindex_pdf_reader',
                        'page_count': len(documents)
                    }
                }
                
            except Exception as e:
                logger.error(f"❌ LlamaIndex PDFReader failed: {e}")
                logger.info("🔄 Falling back to PyPDF2...")
        
        # Fallback to PyPDF2
        if PYPDF2_AVAILABLE:
            try:
                logger.info(f"Using PyPDF2 fallback for: {file_path}")
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    text = ""
                    for page in pdf_reader.pages:
                        text += page.extract_text() + "\n"
                    
                    logger.info(f"✅ PyPDF2 extraction successful: {len(text)} chars")
                    
                    return {
                        'success': True,
                        'text': text.strip(),
                        'file_type': 'pdf',
                        'metadata': {
                            'extractor': 'pypdf2',
                            'page_count': len(pdf_reader.pages)
                        }
                    }
                    
            except Exception as e:
                logger.error(f"❌ PyPDF2 extraction failed: {e}")
        
        return {
            'success': False,
            'error': 'No PDF processing libraries available',
            'text': '',
            'file_type': 'pdf'
        }
    
    def _extract_pptx_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from PowerPoint PPTX file"""
        if not PPTX_AVAILABLE:
            return {
                'success': False,
                'error': 'python-pptx library not available',
                'text': '',
                'file_type': 'pptx'
            }
        
        try:
            logger.info(f"Extracting text from PPTX: {file_path}")
            presentation = Presentation(file_path)
            
            extracted_text = []
            slide_count = 0
            
            for slide in presentation.slides:
                slide_count += 1
                slide_text = []
                
                # Extract text from all shapes in the slide
                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text:
                        slide_text.append(shape.text.strip())
                
                if slide_text:
                    extracted_text.append(f"--- Slide {slide_count} ---\n" + "\n".join(slide_text))
            
            full_text = "\n\n".join(extracted_text)
            logger.info(f"✅ PPTX extraction successful: {len(full_text)} chars from {slide_count} slides")
            
            return {
                'success': True,
                'text': full_text,
                'file_type': 'pptx',
                'metadata': {
                    'extractor': 'python_pptx',
                    'slide_count': slide_count
                }
            }
            
        except Exception as e:
            logger.error(f"❌ PPTX extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'file_type': 'pptx'
            }
    
    def _extract_image_text(self, file_path: str) -> Dict[str, Any]:
        """Extract text from image using Azure GPT-4o mini"""
        if not (AZURE_INFERENCE_AVAILABLE and PIL_AVAILABLE):
            return {
                'success': False,
                'error': 'Azure Inference or PIL not available for image processing',
                'text': '',
                'file_type': 'image'
            }
        
        try:
            logger.info(f"Extracting text from image: {file_path}")
            
            # Verify image can be opened
            with Image.open(file_path) as img:
                img.verify()
            
            # Initialize Azure GPT-4o mini model
            azure_model = AzureAICompletionsModel(
                model="gpt-4o-mini",
                azure_ai_token=os.getenv("AZURE_AI_TOKEN"),
                azure_ai_endpoint=os.getenv("AZURE_AI_ENDPOINT")
            )
            
            # Create chat message with image
            with open(file_path, "rb") as image_file:
                image_data = image_file.read()
            
            message = ChatMessage(
                role="user",
                content=[
                    TextBlock(text="Please extract all text content from this image. If there's no text, respond with 'No text found in image'."),
                    ImageBlock(image=image_data)
                ]
            )
            
            # Get response from Azure model
            response = azure_model.chat([message])
            extracted_text = response.message.content.strip()
            
            logger.info(f"✅ Image text extraction successful: {len(extracted_text)} chars")
            
            return {
                'success': True,
                'text': extracted_text,
                'file_type': 'image',
                'metadata': {
                    'extractor': 'azure_gpt4o_mini'
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Image text extraction failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'text': '',
                'file_type': 'image'
            }
