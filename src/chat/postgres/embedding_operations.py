"""
Database Embedding Operations for YouWoAI ML Server

This module handles all database operations related to embeddings,
integrated within the postgres module for better organization.
Completely independent with no external dependencies.
"""

import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime, timedelta
import logging

from dotenv import load_dotenv
from pgvector.psycopg2 import register_vector

logger = logging.getLogger(__name__)

# Load .env variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT")),
    "user": os.getenv("DB_USERNAME"),
    "password": os.getenv("DB_PASSWORD"),
    "dbname": os.getenv("DB_ACTIVE_DATABASE"),
}


class EmbeddingDBOperations:
    """Database operations specifically for embedding functionality"""

    def __init__(self):
        self.db_config = DB_CONFIG
        logger.info("EmbeddingDBOperations initialized")

    @contextmanager
    def get_connection(self):
        """Get database connection with proper cleanup"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            register_vector(conn)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def get_missing_embedding_ids(self, type_name: str, ids: List[int]) -> List[int]:
        """Generic method to find IDs that don't have embeddings

        Args:
            type_name: Either 'note' or 'conversation'
            ids: List of IDs to check

        Returns:
            List of IDs that don't have embeddings
        """
        if type_name == 'note':
            return self.get_notes_without_embeddings(ids)
        elif type_name == 'conversation':
            return self.get_conversations_without_embeddings(ids)
        else:
            logger.error(f"Unknown type_name: {type_name}")
            return []

    def get_notes_without_embeddings(self, note_ids: List[int]) -> List[int]:
        """Find note IDs that don't have ANY embedding records (never processed)"""
        if not note_ids:
            return []

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Find notes with NO embedding records at all - these have never been processed
                format_strings = ','.join(['%s'] * len(note_ids))
                cursor.execute(f"""
                    SELECT n.id 
                    FROM note_v1 n
                    LEFT JOIN embedding_v1 e ON n.id = e.type_id AND e.type = 'note'
                    WHERE n.id IN ({format_strings})
                      AND n."deletedAt" IS NULL
                      AND e.type_id IS NULL
                    ORDER BY n.id
                """, note_ids)

                notes_without_embeddings = [row[0]
                                            for row in cursor.fetchall()]

                logger.info(
                    f"Notes without embeddings: {len(notes_without_embeddings)}/{len(note_ids)}")
                return notes_without_embeddings

    def get_conversations_without_embeddings(self, conversation_ids: List[int]) -> List[int]:
        """Find conversation IDs that don't have embeddings - matches note pattern"""
        if not conversation_ids:
            return []

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # First check if skipEmbedding column exists
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 
                        FROM information_schema.columns 
                        WHERE table_name = 'conversation_v1' 
                        AND column_name = 'skipEmbedding'
                    )
                """)
                
                column_exists = cursor.fetchone()[0]
                format_strings = ','.join(['%s'] * len(conversation_ids))
                
                if column_exists:
                    # Query with skipEmbedding column
                    cursor.execute(f"""
                        SELECT c.id 
                        FROM conversation_v1 c
                        LEFT JOIN embedding_v1 e ON c.id = e.type_id AND e.type = 'conversation'
                        WHERE c.id IN ({format_strings})
                          AND c."deletedAt" IS NULL
                          AND c."skipEmbedding" = false
                          AND e.type_id IS NULL
                        ORDER BY c.id
                    """, conversation_ids)
                else:
                    # Query without skipEmbedding column - exclude conversations with SKIP_EMBEDDING marker
                    cursor.execute(f"""
                        SELECT c.id 
                        FROM conversation_v1 c
                        LEFT JOIN embedding_v1 e ON c.id = e.type_id AND e.type = 'conversation'
                        WHERE c.id IN ({format_strings})
                          AND c."deletedAt" IS NULL
                          AND e.type_id IS NULL
                          AND NOT EXISTS (
                              SELECT 1 FROM embedding_v1 skip_marker
                              WHERE skip_marker.type_id = c.id 
                              AND skip_marker.type = 'conversation'
                              AND skip_marker.section_id = -1
                              AND skip_marker.chunk_text = 'SKIP_EMBEDDING'
                          )
                        ORDER BY c.id
                    """, conversation_ids)

                conversations_without_embeddings = [
                    row[0] for row in cursor.fetchall()]

                logger.info(
                    f"Conversations without embeddings: {len(conversations_without_embeddings)}/{len(conversation_ids)}")
                return conversations_without_embeddings

    def get_note_content(self, note_id: int) -> Optional[Dict[str, Any]]:
        """Get note content for embedding"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT id, title, content, "ownerId", "folderId", 
                           "createDate", "updateDate"
                    FROM note_v1 
                    WHERE id = %s
                """, (note_id,))

                result = cursor.fetchone()
                return dict(result) if result else None

    def get_conversation_messages(self, conversation_id: int) -> List[Tuple[int, str, str, Any]]:
        """Get conversation messages for embedding

        Returns:
            List of tuples: (msg_id, role, content, created_at)
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT c.id, c.messages, c."createDate"
                    FROM conversation_v1 c
                    WHERE c.id = %s
                """, (conversation_id,))

                result = cursor.fetchone()
                if not result:
                    return []

                messages_data = result['messages'] if result['messages'] else [
                ]
                conversation_created = result['createDate']

                # Convert JSONB messages to expected format
                message_list = []
                for idx, msg in enumerate(messages_data):
                    # Use index as msg_id since messages are stored as array
                    msg_id = idx
                    role = msg.get('role', 'user')

                    # Extract content from message content array
                    content = ""
                    if 'content' in msg and isinstance(msg['content'], list):
                        content_parts = []
                        for content_item in msg['content']:
                            if content_item.get('type') == 'text':
                                content_parts.append(
                                    content_item.get('text', ''))
                        content = ' '.join(content_parts)
                    elif 'content' in msg and isinstance(msg['content'], str):
                        content = msg['content']

                    # Use conversation creation date as message timestamp
                    created_at = conversation_created

                    message_list.append((msg_id, role, content, created_at))

                return message_list

    def get_conversation_content(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """Get conversation content for embedding"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute("""
                    SELECT c.id, c.title, c."userId", c."createDate", c."updateDate",
                           c.messages
                    FROM conversation_v1 c
                    WHERE c.id = %s
                """, (conversation_id,))

                result = cursor.fetchone()
                return dict(result) if result else None

    def save_note_embeddings(self, note_id: int, embeddings_data: List[Tuple]) -> bool:
        """Save note embeddings to database using correct schema"""
        if not embeddings_data:
            return True

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Delete existing embeddings for this note
                    cursor.execute("""
                        DELETE FROM embedding_v1 
                        WHERE type_id = %s AND type = 'note'
                    """, (note_id,))

                    # Insert new embeddings - embeddings_data is list of tuples: (embedding, chunk_text, source)
                    for idx, (embedding, chunk_text, source) in enumerate(embeddings_data):
                        cursor.execute("""
                            INSERT INTO embedding_v1 
                            (type_id, type, section_id, embedding, chunk_text, source, metadata, last_updated)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            note_id,
                            'note',
                            idx,  # Use index as section_id
                            embedding,
                            chunk_text,
                            source or 'note_content',
                            json.dumps({})  # Empty metadata for notes
                        ))

                    conn.commit()
                    logger.info(
                        f"Saved {len(embeddings_data)} embeddings for note {note_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to save note embeddings for {note_id}: {e}")
            return False

    def save_conversation_embeddings(self, conversation_id: int, embeddings_data: List[Tuple]) -> bool:
        """Save conversation embeddings to database using correct schema"""
        if not embeddings_data:
            return True

        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # Delete existing embeddings for this conversation
                    cursor.execute("""
                        DELETE FROM embedding_v1 
                        WHERE type_id = %s AND type = 'conversation'
                    """, (conversation_id,))

                    # Insert new embeddings - embeddings_data is list of tuples: (embedding, text, source, metadata)
                    for idx, (embedding, chunk_text, source, metadata) in enumerate(embeddings_data):
                        cursor.execute("""
                            INSERT INTO embedding_v1 
                            (type_id, type, section_id, embedding, chunk_text, source, metadata, last_updated)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                        """, (
                            conversation_id,
                            'conversation',
                            idx,  # Use index as section_id
                            embedding,
                            chunk_text,
                            source or 'conversation_message',
                            json.dumps(
                                metadata) if metadata else json.dumps({})
                        ))

                    conn.commit()
                    logger.info(
                        f"Saved {len(embeddings_data)} embeddings for conversation {conversation_id}")

                    # Enable embedding for this conversation since it now has embeddings
                    self.enable_conversation_embedding(conversation_id)

                    return True

        except Exception as e:
            logger.error(
                f"Failed to save conversation embeddings for {conversation_id}: {e}")
            return False

    def get_embedding_statistics(self) -> Dict[str, Any]:
        """Get embedding statistics"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Count embeddings by type using correct schema
                cursor.execute("""
                    SELECT 
                        COUNT(CASE WHEN type = 'note' THEN 1 END) as note_embeddings,
                        COUNT(CASE WHEN type = 'conversation' THEN 1 END) as conversation_embeddings,
                        COUNT(DISTINCT CASE WHEN type = 'note' THEN type_id END) as unique_notes,
                        COUNT(DISTINCT CASE WHEN type = 'conversation' THEN type_id END) as unique_conversations,
                        COUNT(*) as total_embeddings
                    FROM embedding_v1
                """)

                result = cursor.fetchone()

                return {
                    "note_embeddings": result[0] or 0,
                    "conversation_embeddings": result[1] or 0,
                    "unique_notes": result[2] or 0,
                    "unique_conversations": result[3] or 0,
                    "total_embeddings": result[4] or 0
                }

    def get_all_note_ids(self) -> List[int]:
        """Get all note IDs in the system"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM note_v1 ORDER BY id")
                return [row[0] for row in cursor.fetchall()]

    def get_all_conversation_ids(self) -> List[int]:
        """Get all conversation IDs in the system"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT id FROM conversation_v1 ORDER BY id")
                return [row[0] for row in cursor.fetchall()]

    def get_user_note_ids(self, user_id: int) -> List[int]:
        """Get all note IDs for a specific user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM note_v1 
                    WHERE "ownerId" = %s 
                    ORDER BY id
                """, (user_id,))
                return [row[0] for row in cursor.fetchall()]

    def get_user_conversation_ids(self, user_id: int) -> List[int]:
        """Get all conversation IDs for a specific user"""
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT id FROM conversation_v1 
                    WHERE "ownerId" = %s 
                    ORDER BY id
                """, (user_id,))
                return [row[0] for row in cursor.fetchall()]

    def delete_note_embeddings(self, note_id: int) -> bool:
        """Delete all embeddings for a note"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM embedding_v1 
                        WHERE type_id = %s AND type = 'note'
                    """, (note_id,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    logger.info(
                        f"Deleted {deleted_count} embeddings for note {note_id}")
                    return True

        except Exception as e:
            logger.error(
                f"Failed to delete embeddings for note {note_id}: {e}")
            return False

    def delete_conversation_embeddings(self, conversation_id: int) -> bool:
        """Delete all embeddings for a conversation"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        DELETE FROM embedding_v1 
                        WHERE type_id = %s AND type = 'conversation'
                    """, (conversation_id,))

                    deleted_count = cursor.rowcount
                    conn.commit()

                    logger.info(
                        f"Deleted {deleted_count} embeddings for conversation {conversation_id}")
                    return True

        except Exception as e:
            logger.error(
                f"Failed to delete embeddings for conversation {conversation_id}: {e}")
            return False

    def health_check(self) -> bool:
        """Check if database connection and embedding table are working"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT COUNT(*) FROM embedding_v1 LIMIT 1")
                    cursor.fetchone()
                    return True
        except Exception as e:
            logger.error(f"Embedding database health check failed: {e}")
            return False

    def get_note_content_separate(self, note_id: int) -> Tuple[str, str, str]:
        """
        Get note content separated into AI content (summary) and user content
        Returns: (ai_content, user_content, note_type)
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                # Get note basic info and check if it has a noteType field
                cursor.execute("""
                    SELECT "promptContent", 
                           CASE 
                               WHEN EXISTS(SELECT 1 FROM information_schema.columns 
                                         WHERE table_name = 'note_v1' AND column_name = 'noteType') 
                               THEN "noteType" 
                               ELSE 'text'
                           END as note_type
                    FROM note_v1 
                    WHERE id = %s
                """, (note_id,))

                result = cursor.fetchone()
                if not result:
                    return "", "", "text"

                prompt_content, note_type = result

                # Extract AI content (summary) from prompt content
                ai_content = ""
                if prompt_content and isinstance(prompt_content, dict):
                    if ("currentPromptContent" in prompt_content and
                            prompt_content["currentPromptContent"]):
                        ai_content = prompt_content["currentPromptContent"].get(
                            "content", "")

                # Get user content (parts + images)
                user_content_parts = []

                # Get prefix images (not associated with any part)
                cursor.execute("""
                    SELECT "imageURL", "imageText", latex
                    FROM image_v1
                    WHERE "noteId" = %s AND "partId" IS NULL
                    ORDER BY id
                """, (note_id,))
                prefix_images = cursor.fetchall()

                # Add prefix images
                for img_url, img_text, is_latex in prefix_images:
                    if img_text:
                        user_content_parts.append(img_text)

                # Get parts in order
                cursor.execute("""
                    SELECT id, "text"
                    FROM part_v1
                    WHERE "noteId" = %s
                    ORDER BY "order"
                """, (note_id,))
                parts = cursor.fetchall()

                # Process each part and its images
                for part_id, part_text in parts:
                    # Add part text
                    if part_text:
                        user_content_parts.append(part_text)

                    # Get images for this part
                    cursor.execute("""
                        SELECT "imageURL", "imageText", latex
                        FROM image_v1
                        WHERE "partId" = %s
                        ORDER BY id
                    """, (part_id,))
                    part_images = cursor.fetchall()

                    # Add part's images
                    for img_url, img_text, is_latex in part_images:
                        if img_text:
                            user_content_parts.append(img_text)

                user_content = "\n\n".join(user_content_parts)

                # Determine note type if not available in DB
                if not note_type or note_type == 'text':
                    # Try to infer from content or use default
                    if 'youtube' in user_content.lower() or 'video' in user_content.lower():
                        note_type = 'youtube'
                    elif any(ext in user_content.lower() for ext in ['.pdf', 'document', 'doc']):
                        note_type = 'doc'
                    else:
                        note_type = 'text'

                return ai_content.strip(), user_content.strip(), note_type

    def get_all_notes(self) -> List[int]:
        """Get all note IDs in the system - alias for get_all_note_ids"""
        return self.get_all_note_ids()
    
    def get_all_conversations(self) -> List[int]:
        """Get all conversation IDs in the system - alias for get_all_conversation_ids"""
        return self.get_all_conversation_ids()

    def get_user_notes(self, user_id: int) -> List[int]:
        """Get all note IDs for a specific user - alias for get_user_note_ids"""
        return self.get_user_note_ids(user_id)
    
    def get_user_conversations(self, user_id: int) -> List[int]:
        """Get all conversation IDs for a specific user - alias for get_user_conversation_ids"""
        return self.get_user_conversation_ids(user_id)

    def mark_note_skip_embedding(self, note_id: int) -> bool:
        """Mark note to skip embedding (for notes with no content)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First check if any embedding already exists for this note
                    cursor.execute("""
                        SELECT COUNT(*) FROM embedding_v1 
                        WHERE type_id = %s AND type = 'note'
                    """, (note_id,))

                    existing_count = cursor.fetchone()[0]

                    if existing_count == 0:
                        # Insert a special marker record to indicate this note should be skipped
                        cursor.execute("""
                            INSERT INTO embedding_v1 (type_id, type, section_id, chunk_text, embedding, last_updated)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (note_id, 'note', -1, 'SKIP_EMBEDDING', None))

                        conn.commit()
                        logger.info(f"Marked note {note_id} to skip embedding")
                    else:
                        logger.info(
                            f"Note {note_id} already has embeddings, skipping mark operation")

                    return True
        except Exception as e:
            logger.error(
                f"Failed to mark note {note_id} to skip embedding: {e}")
            return False

    def mark_conversation_skip_embedding(self, conversation_id: int) -> bool:
        """Mark conversation to skip embedding (for conversations with no messages)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First check if skipEmbedding column exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'conversation_v1' 
                            AND column_name = 'skipEmbedding'
                        )
                    """)
                    
                    column_exists = cursor.fetchone()[0]
                    
                    if column_exists:
                        # Update the conversation to set skipEmbedding = true
                        cursor.execute("""
                            UPDATE conversation_v1 
                            SET "skipEmbedding" = true
                            WHERE id = %s
                        """, (conversation_id,))
                        
                        conn.commit()
                        logger.info(
                            f"Marked conversation {conversation_id} to skip embedding")
                    else:
                        # Column doesn't exist, use embedding_v1 marker approach
                        # First check if any embedding already exists for this conversation
                        cursor.execute("""
                            SELECT COUNT(*) FROM embedding_v1 
                            WHERE type_id = %s AND type = 'conversation'
                        """, (conversation_id,))
                        
                        existing_count = cursor.fetchone()[0]
                        
                        if existing_count == 0:
                            # Insert a special marker record to indicate this conversation should be skipped
                            cursor.execute("""
                                INSERT INTO embedding_v1 (type_id, type, section_id, chunk_text, embedding, last_updated)
                                VALUES (%s, %s, %s, %s, %s, NOW())
                            """, (conversation_id, 'conversation', -1, 'SKIP_EMBEDDING', None))
                            
                            conn.commit()
                            logger.info(f"Marked conversation {conversation_id} to skip embedding (using marker)")
                        else:
                            logger.info(
                                f"Conversation {conversation_id} already has embeddings, skipping mark operation")
                    
                    return True
        except Exception as e:
            logger.error(
                f"Failed to mark conversation {conversation_id} to skip embedding: {e}")
            return False

    def enable_conversation_embedding(self, conversation_id: int) -> bool:
        """Enable embedding for conversation (when it gets messages)"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    # First check if skipEmbedding column exists
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT 1 
                            FROM information_schema.columns 
                            WHERE table_name = 'conversation_v1' 
                            AND column_name = 'skipEmbedding'
                        )
                    """)
                    
                    column_exists = cursor.fetchone()[0]
                    
                    if column_exists:
                        # Update the conversation to set skipEmbedding = false
                        cursor.execute("""
                            UPDATE conversation_v1 
                            SET "skipEmbedding" = false
                            WHERE id = %s
                        """, (conversation_id,))
                        
                        conn.commit()
                        logger.info(
                            f"Enabled embedding for conversation {conversation_id}")
                    else:
                        # Column doesn't exist, remove the SKIP_EMBEDDING marker if it exists
                        cursor.execute("""
                            DELETE FROM embedding_v1 
                            WHERE type_id = %s 
                            AND type = 'conversation'
                            AND section_id = -1
                            AND chunk_text = 'SKIP_EMBEDDING'
                        """, (conversation_id,))
                        
                        if cursor.rowcount > 0:
                            conn.commit()
                            logger.info(
                                f"Enabled embedding for conversation {conversation_id} (removed marker)")
                        else:
                            logger.info(
                                f"No skip marker found for conversation {conversation_id}")
                    
                    return True
        except Exception as e:
            logger.error(
                f"Failed to enable embedding for conversation {conversation_id}: {e}")
            return False
