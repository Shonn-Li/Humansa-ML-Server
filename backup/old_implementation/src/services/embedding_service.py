import logging
from typing import List, Tuple
from src.utility.postgres import get_db_connection, get_notes_for_rag, get_notes_without_embeddings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for managing embedding operations"""

    def get_user_notes(self, user_id: int) -> List[int]:
        """Get all note IDs for a user"""
        return get_notes_for_rag(user_id, folder_ids=None, note_ids=None)

    def get_all_notes(self) -> List[int]:
        """Get all note IDs in the system"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM note_v1 
                    WHERE completed = true 
                    AND "ownerId" IS NOT NULL
                    ORDER BY id
                """)
                return [row[0] for row in cursor.fetchall()]

    def get_notes_needing_embeddings(self, note_ids: List[int]) -> List[int]:
        """Get notes that don't have embeddings yet"""
        return get_notes_without_embeddings(note_ids)

    def get_all_conversations(self) -> List[int]:
        """Get all conversation IDs in the system"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM conversation_v1 
                    ORDER BY id
                """)
                return [row[0] for row in cursor.fetchall()]

    def get_user_conversations(self, user_id: int) -> List[int]:
        """Get all conversation IDs for a user"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM conversation_v1 
                    WHERE "userId" = %s
                    ORDER BY id
                """, (user_id,))
                return [row[0] for row in cursor.fetchall()]

    def get_conversations_needing_embeddings(self, conversation_ids: List[int]) -> List[int]:
        """Get conversations that don't have embeddings yet"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT DISTINCT c.id
                    FROM conversation_v1 c
                    WHERE c.id = ANY(%s)
                    AND NOT EXISTS (
                        SELECT 1 FROM embedding_v1 e 
                        WHERE e.type_id = c.id AND e.type = 'conversation'
                    )
                    ORDER BY c.id
                """, (conversation_ids,))
                return [row[0] for row in cursor.fetchall()]

    def delete_all_embeddings(self) -> None:
        """Delete all existing embeddings (for re-embedding)"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM embedding_v1")
                conn.commit()
                logger.info("Deleted all existing embeddings")

    def delete_conversation_embeddings(self) -> None:
        """Delete only conversation embeddings"""
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM embedding_v1 WHERE type = 'conversation'")
                conn.commit()
                logger.info("Deleted all conversation embeddings")

    def validate_embed_request(self, data: dict, require_confirm: bool = False) -> Tuple[bool, str]:
        """Validate embedding request data"""
        if require_confirm:
            confirm = data.get("confirm_embed_all", False) or data.get(
                "confirm_re_embed_all", False)
            if not confirm:
                return False, "This operation requires confirmation. Set 'confirm_embed_all' or 'confirm_re_embed_all': true"

        user_id = data.get("user_id")
        if "user" in data and not user_id:
            return False, "user_id is required"

        return True, ""


# Global embedding service instance
embedding_service = EmbeddingService()
