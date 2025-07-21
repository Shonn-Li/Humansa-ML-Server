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
            return {"status": "success", "context": "", "metadata": {"attachment_count": 0}}
        
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
        
        return {
            "status": "success",
            "context": attachment_context,
            "metadata": {
                "attachment_count": len(attachments),
                "context_length": len(attachment_context)
            }
        }