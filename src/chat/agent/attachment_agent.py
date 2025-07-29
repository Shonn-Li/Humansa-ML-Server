"""
Attachment Agent - Processes file attachments

This agent handles various file attachments (PDFs, images, text files, etc.)
and extracts their content to provide context for the response.
"""

from typing import Dict, Any
import logging

from .base import BaseAgent
from ..attachment.file_attachment_manager import FileAttachmentManager

logger = logging.getLogger(__name__)


class AttachmentAgent(BaseAgent):
    """Agent for processing file attachments"""
    
    def __init__(self, file_attachment_manager: FileAttachmentManager):
        super().__init__()
        self.file_attachment_manager = file_attachment_manager
    
    async def run(self, request: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Process attachments and extract context"""
        
        attachments = request.get("attachments", [])
        if not attachments:
            return {
                "status": "success", 
                "context": "", 
                "sources": [],
                "metadata": {"attachment_count": 0, "file_types": []}
            }
        
        router_result = context.get("router_agent", {})
        condensed_query = router_result.get("condensed_query", router_result.get("original_query", ""))
        
        # Process attachments
        user_id = request.get("user_id", 0)
        attachment_result = await self.file_attachment_manager.process_attachments(
            attachments, condensed_query, user_id
        )
        
        # Convert AttachmentContext to string for context
        attachment_context = self.file_attachment_manager.chunks_to_context_text(
            attachment_result.chunks,
            attachment_result.image_chunks
        ) if attachment_result else ""
        
        # Build sources for file attachments
        sources = []
        file_types = set()
        
        logger.info(f"Processing {len(attachments)} attachments for sources")
        for i, attachment in enumerate(attachments):
            try:
                logger.info(f"Attachment {i}: type={type(attachment)}, value={attachment}")
                
                # Handle both string URLs and dictionary format
                if isinstance(attachment, str):
                    # Legacy format: just URL string
                    attachment_url = attachment
                    filename = attachment_url.split('/')[-1].split('?')[0]
                    file_extension = filename.split('.')[-1].lower() if '.' in filename else 'unknown'
                elif isinstance(attachment, dict):
                    # New format: dictionary with type, url, filename
                    attachment_url = attachment.get('url', '')
                    filename = attachment.get('filename', '')
                    # Extract extension from filename or use type
                    if '.' in filename:
                        file_extension = filename.split('.')[-1].lower()
                    else:
                        # Try to extract from MIME type
                        mime_type = attachment.get('type', '')
                        if '/' in mime_type:
                            file_extension = mime_type.split('/')[-1].split('.')[-1]
                        else:
                            file_extension = 'unknown'
                else:
                    logger.error(f"Unexpected attachment type: {type(attachment)}")
                    continue
                
                file_types.add(file_extension)
                
                source = {
                    "file_id": f"file_{i}",
                    "filename": filename,
                    "url": attachment_url,
                    "type": "file_attachment",
                    "file_type": file_extension,
                    "title": f"Attachment: {filename}",
                    "content": f"Content from {filename}"  # Preview
                }
                sources.append(source)
                
            except Exception as e:
                logger.error(f"Error processing attachment {i}: {e}")
                logger.error(f"Attachment data: {attachment}")
                continue
        
        return {
            "status": "success",
            "context": attachment_context,
            "sources": sources,
            "metadata": {
                "attachment_count": len(attachments),
                "context_length": len(attachment_context),
                "file_types": list(file_types),
                "chunk_count": len(attachment_result.chunks) if attachment_result else 0,
                "image_chunk_count": len(attachment_result.image_chunks) if attachment_result else 0
            }
        }