"""
Document Converter Endpoint for YouWoAI ML Server

This module provides endpoints for converting documents between different formats,
with a focus on converting various document types to PDF for better text extraction
and consistent storage format.

Endpoints:
- POST /v1/document-converter - Convert documents between formats
- POST /v1/document-to-pdf - Specialized endpoint for PDF conversion
"""

import logging
import time
import tempfile
import os
import base64
from pathlib import Path
from typing import Optional, Dict, Any
import requests

# Quart imports for async endpoints
from quart import Blueprint, request, jsonify, send_file, Response
from quart_cors import cors

# Import document converter
from chat.utils.document_converter import convert_document_to_pdf

logger = logging.getLogger(__name__)

# Create blueprint
document_converter_bp = Blueprint('document_converter', __name__)
document_converter_bp = cors(document_converter_bp, allow_origin="*")


@document_converter_bp.route('/v1/document-to-pdf', methods=['POST'])
async def convert_to_pdf():
    """
    Convert a document to PDF format
    
    This endpoint accepts either:
    1. A file URL (for files stored remotely)
    2. Base64 encoded file content with filename
    
    Request body:
    {
        "url": "https://example.com/document.docx",  // For URL-based conversion
        "filename": "document.docx",
        "type": "url"  // or "base64"
        "content": "base64_encoded_content"  // For base64 uploads
    }
    
    Response:
    - Binary PDF data (application/pdf content type)
    - Or JSON error response if conversion fails
    """
    try:
        start_time = time.time()
        data = await request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        filename = data.get('filename', 'document')
        request_type = data.get('type', 'url')
        
        # Create temporary file for input
        file_extension = Path(filename).suffix.lower()
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_input:
            temp_input_path = temp_input.name
            
            if request_type == 'url':
                # Download file from URL
                url = data.get('url')
                if not url:
                    return jsonify({
                        "success": False,
                        "error": "URL is required for type 'url'"
                    }), 400
                
                logger.info(f"📄 Downloading document from URL: {url[:50]}...")
                
                # Download the file
                response = requests.get(url, timeout=60)
                response.raise_for_status()
                temp_input.write(response.content)
                
            elif request_type == 'base64':
                # Decode base64 content
                content = data.get('content')
                if not content:
                    return jsonify({
                        "success": False,
                        "error": "'content' is required for type 'base64'"
                    }), 400
                
                logger.info(f"📄 Processing base64 document: {filename}")
                
                try:
                    file_data = base64.b64decode(content)
                    temp_input.write(file_data)
                except Exception as e:
                    return jsonify({
                        "success": False,
                        "error": f"Invalid base64 content: {str(e)}"
                    }), 400
            else:
                return jsonify({
                    "success": False,
                    "error": "Invalid type. Must be 'url' or 'base64'"
                }), 400
        
        # Convert to PDF
        logger.info(f"🔄 Converting {filename} to PDF...")
        success, pdf_path = convert_document_to_pdf(temp_input_path)
        
        # Clean up input file
        try:
            os.unlink(temp_input_path)
        except:
            pass
        
        if not success or not pdf_path:
            logger.error(f"❌ Failed to convert {filename} to PDF")
            return jsonify({
                "success": False,
                "error": f"Failed to convert {file_extension} to PDF. Make sure LibreOffice is installed for best results."
            }), 500
        
        processing_time = time.time() - start_time
        logger.info(f"✅ Successfully converted {filename} to PDF in {processing_time:.2f}s")
        
        # Read the PDF file
        with open(pdf_path, 'rb') as pdf_file:
            pdf_data = pdf_file.read()
        
        # Clean up PDF file if it's a temp file
        try:
            if pdf_path != temp_input_path:
                os.unlink(pdf_path)
        except:
            pass
        
        # Return PDF as binary response
        return Response(
            pdf_data,
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{Path(filename).stem}.pdf"',
                'Content-Length': str(len(pdf_data))
            }
        )
        
    except Exception as e:
        logger.error(f"❌ Error in document-to-pdf endpoint: {e}")
        processing_time = time.time() - start_time if 'start_time' in locals() else 0
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}",
            "processing_time": round(processing_time, 2)
        }), 500


@document_converter_bp.route('/v1/document-converter', methods=['POST'])
async def convert_document():
    """
    General document converter endpoint for converting between various formats
    
    Request body:
    {
        "sourceUrl": "https://example.com/document.pdf",  // For URL source
        "sourceContent": "base64_encoded_content",  // For base64 source
        "sourceFilename": "document.pdf",  // Required for base64
        "sourceType": "url",  // or "base64"
        "targetFormat": "md",  // Target format: pdf, docx, md, html, txt
        "options": {
            "preserveFormatting": true,
            "includeImages": true,
            "pageRange": "1-5",  // Optional page range
            "quality": "high"  // draft, standard, high
        }
    }
    
    Response:
    {
        "success": true,
        "filename": "document.md",
        "content": "# Document content...",  // For text formats
        "downloadUrl": "https://...",  // For binary formats
        "metadata": {
            "pageCount": 5,
            "wordCount": 1234
        }
    }
    """
    try:
        data = await request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body is required"
            }), 400
        
        target_format = data.get('targetFormat', 'pdf').lower()
        
        # For now, only support conversion to PDF
        if target_format == 'pdf':
            # Reuse the PDF conversion logic
            return await convert_to_pdf()
        else:
            return jsonify({
                "success": False,
                "error": f"Target format '{target_format}' is not yet supported. Currently only 'pdf' is supported."
            }), 400
            
    except Exception as e:
        logger.error(f"❌ Error in document converter endpoint: {e}")
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500


@document_converter_bp.route('/v1/document-converter/status', methods=['GET'])
async def converter_status():
    """Status endpoint for document converter service"""
    try:
        from chat.utils.document_converter import (
            UNOCONV_AVAILABLE,
            DOCX2PDF_AVAILABLE,
            PYPANDOC_AVAILABLE,
            PYTHON_DOCX_AVAILABLE,
            OPENPYXL_AVAILABLE,
            REPORTLAB_AVAILABLE
        )
        
        return jsonify({
            "success": True,
            "service": "document_converter",
            "version": "1.0.0",
            "capabilities": {
                "unoconv_available": UNOCONV_AVAILABLE,
                "docx2pdf_available": DOCX2PDF_AVAILABLE,
                "pypandoc_available": PYPANDOC_AVAILABLE,
                "python_docx_available": PYTHON_DOCX_AVAILABLE,
                "openpyxl_available": OPENPYXL_AVAILABLE,
                "reportlab_available": REPORTLAB_AVAILABLE,
                "supported_conversions": {
                    "to_pdf": ["doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "md", "html"],
                    "from_pdf": []  # Future: PDF to other formats
                },
                "recommended_setup": "Install LibreOffice for best conversion quality (enables unoconv)"
            }
        })
        
    except Exception as e:
        logger.error(f"Error in converter status: {e}")
        return jsonify({
            "success": False,
            "error": f"Status check failed: {str(e)}"
        }), 500