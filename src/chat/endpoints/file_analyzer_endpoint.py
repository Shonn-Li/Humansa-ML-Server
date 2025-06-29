"""
File Analyzer Endpoint for YouWoAI ML Server

This module provides a simple file analyzer endpoint that extracts all text content
from uploaded files without creating embeddings. Designed to bridge between backend
server and ML server for file text extraction capabilities.

Endpoint:
- POST /v1/file-analyzer - Analyze a file and return extracted text
"""

import logging
import time
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any

# Quart imports for async endpoints
from quart import Blueprint, request, jsonify
from quart_cors import cors

# Import the URL embedding operations for file processing logic
from chat.postgres.url_embedding_operations import url_embedding_ops

logger = logging.getLogger(__name__)

# Create blueprint
file_analyzer_bp = Blueprint('file_analyzer', __name__)
file_analyzer_bp = cors(file_analyzer_bp, allow_origin="*")


@file_analyzer_bp.route('/v1/file-analyzer', methods=['POST'])
async def analyze_file():
    """
    Analyze a file and extract all text content

    This endpoint accepts either:
    1. A file URL (for files stored remotely)
    2. Base64 encoded file content with filename

    Request body (Option 1 - URL):
    {
        "url": "https://example.com/document.pdf",
        "type": "url"
    }

    Request body (Option 2 - Base64 content):
    {
        "content": "base64_encoded_file_content",
        "filename": "document.pdf",
        "type": "base64"
    }

    Response:
    {
        "success": true,
        "filename": "document.pdf",
        "file_type": "pdf",
        "text_content": "Extracted text from the file...",
        "character_count": 1234,
        "processing_time": 2.5,
        "metadata": {
            "pages": 5,  // for PDFs
            "slides": 10, // for PPTX
            "extraction_method": "python-pptx (lightweight)"
        }
    }
    """
    try:
        start_time = time.time()
        data = await request.get_json()

        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400

        request_type = data.get('type', 'url')

        if request_type == 'url':
            # Process file from URL
            url = data.get('url')
            if not url:
                return jsonify({
                    "success": False,
                    "error": "URL is required for type 'url'"
                }), 400

            logger.info(f"📄 Analyzing file from URL: {url[:50]}...")

            # Use existing URL processing logic
            text_content = await url_embedding_ops._download_and_process_url(url)
            filename = Path(url.split('?')[0]).name

        elif request_type == 'base64':
            # Process base64 encoded file content
            content = data.get('content')
            filename = data.get('filename')

            if not content or not filename:
                return jsonify({
                    "success": False,
                    "error": "Both 'content' and 'filename' are required for type 'base64'"
                }), 400

            logger.info(f"📄 Analyzing base64 file: {filename}")

            # Decode base64 content and save to temporary file
            import base64
            try:
                file_data = base64.b64decode(content)
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Invalid base64 content: {str(e)}"
                }), 400

            # Create temporary file with correct extension
            file_extension = Path(filename).suffix.lower()
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
                temp_file.write(file_data)
                temp_path = temp_file.name

            try:
                # Process the temporary file
                text_content = await _process_file_by_extension(temp_path, filename)
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_path)
                except:
                    pass

        else:
            return jsonify({
                "success": False,
                "error": "Invalid type. Must be 'url' or 'base64'"
            }), 400

        processing_time = time.time() - start_time

        if text_content is None:
            return jsonify({
                "success": False,
                "error": "Failed to extract text from file",
                "filename": filename,
                "processing_time": round(processing_time, 2)
            }), 500

        # Determine file type from filename
        file_extension = Path(filename).suffix.lower()
        file_type = _get_file_type(file_extension)

        # Create response
        response_data = {
            "success": True,
            "filename": filename,
            "file_type": file_type,
            "text_content": text_content,
            "character_count": len(text_content),
            "processing_time": round(processing_time, 2),
            "metadata": {
                "extraction_method": _get_extraction_method(file_extension)
            }
        }

        # Add file-specific metadata
        if file_type == "pdf":
            # Estimate page count (rough estimation)
            page_count = max(1, text_content.count('\n\n') // 10)
            response_data["metadata"]["estimated_pages"] = page_count
        elif file_type == "pptx":
            # Count slides based on slide markers
            slide_count = text_content.count("=== Slide")
            response_data["metadata"]["slides"] = slide_count

        logger.info(
            f"✅ File analysis complete: {filename} ({len(text_content)} chars) in {processing_time:.2f}s")

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"❌ Error in file analyzer endpoint: {e}")
        processing_time = time.time() - start_time if 'start_time' in locals() else 0
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "processing_time": round(processing_time, 2)
        }), 500


async def _process_file_by_extension(file_path: str, filename: str) -> Optional[str]:
    """Process a file based on its extension"""
    file_extension = Path(filename).suffix.lower()

    try:
        if file_extension == '.pdf':
            return url_embedding_ops._process_pdf_file(file_path)
        elif file_extension in ['.pptx', '.ppt']:
            return url_embedding_ops._process_pptx_file(file_path)
        elif file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            # For images, we could use the GPT-4o processing, but for now return basic info
            return f"[Image file: {filename}] - Image content extraction would require additional processing"
        else:
            # Try to read as text
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                return f"[Binary file: {filename}] - Content type not supported for text extraction"

    except Exception as e:
        logger.error(f"Error processing file {filename}: {e}")
        return None


def _get_file_type(file_extension: str) -> str:
    """Get file type from extension"""
    extension_map = {
        '.pdf': 'pdf',
        '.pptx': 'pptx',
        '.ppt': 'ppt',
        '.docx': 'docx',
        '.doc': 'doc',
        '.txt': 'text',
        '.md': 'markdown',
        '.jpg': 'image',
        '.jpeg': 'image',
        '.png': 'image',
        '.gif': 'image',
        '.webp': 'image'
    }
    return extension_map.get(file_extension, 'unknown')


def _get_extraction_method(file_extension: str) -> str:
    """Get extraction method for file type"""
    method_map = {
        '.pdf': 'LlamaIndex PDFReader + PyPDF2 fallback',
        '.pptx': 'python-pptx (lightweight)',
        '.ppt': 'python-pptx (lightweight)',
        '.txt': 'direct text read',
        '.md': 'direct text read',
        '.jpg': 'basic metadata (GPT-4o available)',
        '.jpeg': 'basic metadata (GPT-4o available)',
        '.png': 'basic metadata (GPT-4o available)',
        '.gif': 'basic metadata (GPT-4o available)',
        '.webp': 'basic metadata (GPT-4o available)'
    }
    return method_map.get(file_extension, 'unknown')


@file_analyzer_bp.route('/v1/file-analyzer/status', methods=['GET'])
async def file_analyzer_status():
    """Status endpoint for file analyzer service"""
    try:
        # Import the necessary components to check availability
        from chat.postgres.url_embedding_operations import (
            LLAMAINDEX_PDF_READER_AVAILABLE,
            PDF_PROCESSING_AVAILABLE,
            PPTX_PROCESSING_AVAILABLE
        )

        return jsonify({
            "success": True,
            "service": "file_analyzer",
            "version": "1.0.0",
            "capabilities": {
                "pdf_processing": PDF_PROCESSING_AVAILABLE,
                "llamaindex_pdf": LLAMAINDEX_PDF_READER_AVAILABLE,
                "pptx_processing": PPTX_PROCESSING_AVAILABLE,
                "supported_formats": [
                    "pdf", "pptx", "ppt", "txt", "md",
                    "jpg", "jpeg", "png", "gif", "webp"
                ],
                "processing_methods": {
                    "pdf": "LlamaIndex PDFReader + PyPDF2 fallback",
                    "pptx": "python-pptx library",
                    "images": "GPT-4o vision (when available)",
                    "text": "direct file read"
                }
            }
        })

    except Exception as e:
        logger.error(f"Error in file analyzer status: {e}")
        return jsonify({
            "success": False,
            "error": f"Status check failed: {str(e)}"
        }), 500
