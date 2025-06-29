"""
Conversation Database Operations

This module handles database operations for conversations, including:
- Fetching conversations without titles
- Updating conversation titles
- Retrieving conversation details
"""

import logging
from typing import List, Dict, Any, Optional
from chat.postgres.db_manager import PostgresManager

logger = logging.getLogger(__name__)


class ConversationDBOperations:
    """Handle conversation-related database operations"""

    def __init__(self):
        self.db_manager = PostgresManager()

    async def get_conversations_without_titles(self, max_conversations: int = 1000) -> List[Dict[str, Any]]:
        """
        Get conversations that don't have titles from the database

        Args:
            max_conversations: Maximum number of conversations to retrieve

        Returns:
            List of conversation dictionaries with id, messages, user_id, etc.
        """
        try:
            query = """
            SELECT 
                c.id,
                c."ownerId" as user_id,
                c.messages,
                c."createDate",
                c."updateDate",
                c.type as conversation_scope,
                c."typeId" as type_id
            FROM "conversation_v1" c
            WHERE 
                -- No title or empty title
                (c.title IS NULL OR LENGTH(TRIM(c.title)) = 0)
                
                -- Not deleted
                AND c."deletedAt" IS NULL
                
                -- Recent conversations (last 90 days) - focus on recent ones first
                AND c."createDate" >= NOW() - INTERVAL '90 days'
                
            ORDER BY c."createDate" DESC
            LIMIT %s
            """

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (max_conversations,))
                    rows = cursor.fetchall()

                    conversations = []
                    for row in rows:
                        # Convert the row to a dictionary and process messages
                        conv_dict = {
                            'id': row[0],
                            'user_id': row[1],
                            'messages': row[2] or [],
                            'createDate': row[3],
                            'updateDate': row[4],
                            'conversation_scope': row[5],
                            'type_id': row[6]
                        }

                        # Parse messages if they exist
                        messages = conv_dict.get('messages', [])
                        if isinstance(messages, str):
                            import json
                            try:
                                messages = json.loads(messages)
                            except json.JSONDecodeError:
                                messages = []

                        conv_dict['messages'] = messages or []
                        conversations.append(conv_dict)

                    logger.info(
                        f"📊 Found {len(conversations)} conversations without titles")
                    return conversations

        except Exception as e:
            logger.error(f"❌ Failed to get conversations without titles: {e}")
            raise

    async def update_conversation_title(self, conversation_id: int, title: str) -> bool:
        """
        Update the title of a conversation

        Args:
            conversation_id: ID of the conversation to update
            title: New title for the conversation

        Returns:
            True if successful, False otherwise
        """
        try:
            query = """
            UPDATE "conversation_v1" 
            SET 
                title = %s,
                "updateDate" = NOW()
            WHERE 
                id = %s 
                AND "deletedAt" IS NULL
            """

            with self.db_manager.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, (title, conversation_id))
                    rows_affected = cursor.rowcount
                    conn.commit()

                    # Check if any row was updated
                    if rows_affected > 0:
                        logger.info(
                            f"✅ Updated conversation {conversation_id} title: '{title}'")
                        return True
                    else:
                        logger.warning(
                            f"⚠️ No conversation found with ID {conversation_id} to update")
                        return False

        except Exception as e:
            logger.error(
                f"❌ Failed to update conversation {conversation_id} title: {e}")
            raise

    async def get_conversation_by_id(self, conversation_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by its ID

        Args:
            conversation_id: ID of the conversation

        Returns:
            Conversation dictionary or None if not found
        """
        try:
            query = """
            SELECT 
                c.id,
                c."ownerId" as user_id,
                c.title,
                c.messages,
                c."createDate",
                c."updateDate",
                c.type as conversation_scope,
                c."typeId" as type_id
            FROM "conversation_v1" c
            WHERE 
                c.id = $1
                AND c."deletedAt" IS NULL
            """

            async with self.db_manager.get_connection() as conn:
                row = await conn.fetchrow(query, conversation_id)

                if row:
                    conv_dict = dict(row)

                    # Parse messages if they exist
                    messages = conv_dict.get('messages', [])
                    if isinstance(messages, str):
                        import json
                        try:
                            messages = json.loads(messages)
                        except json.JSONDecodeError:
                            messages = []

                    conv_dict['messages'] = messages or []
                    return conv_dict
                else:
                    return None

        except Exception as e:
            logger.error(
                f"❌ Failed to get conversation {conversation_id}: {e}")
            raise

    async def conversation_exists(self, conversation_id: int) -> bool:
        """
        Check if a conversation exists

        Args:
            conversation_id: ID of the conversation to check

        Returns:
            True if conversation exists, False otherwise
        """
        try:
            query = """
            SELECT 1 FROM "conversation_v1" 
            WHERE id = $1 AND "deletedAt" IS NULL
            """

            async with self.db_manager.get_connection() as conn:
                result = await conn.fetchval(query, conversation_id)
                return result is not None

        except Exception as e:
            logger.error(
                f"❌ Failed to check if conversation {conversation_id} exists: {e}")
            return False


# Global instance for easy importing
conversation_db_operations = ConversationDBOperations()

# Functions for backward compatibility


async def get_conversations_without_titles(max_conversations: int = 1000) -> List[Dict[str, Any]]:
    """Get conversations without titles - backward compatibility function"""
    # Since PostgresManager is synchronous, we need to run it synchronously
    # but wrap it for async compatibility
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If we're in an async context, run in thread pool
        return await loop.run_in_executor(None, _get_conversations_without_titles_sync, max_conversations)
    else:
        return _get_conversations_without_titles_sync(max_conversations)


async def update_conversation_title(conversation_id: int, title: str) -> bool:
    """Update conversation title - backward compatibility function"""
    # Since PostgresManager is synchronous, we need to run it synchronously
    # but wrap it for async compatibility
    import asyncio
    loop = asyncio.get_event_loop()
    if loop.is_running():
        # If we're in an async context, run in thread pool
        return await loop.run_in_executor(None, _update_conversation_title_sync, conversation_id, title)
    else:
        return _update_conversation_title_sync(conversation_id, title)


def _get_conversations_without_titles_sync(max_conversations: int) -> List[Dict[str, Any]]:
    """Synchronous version of get conversations without titles"""
    try:
        query = """
        SELECT 
            c.id,
            c."ownerId" as user_id,
            c.messages,
            c."createDate",
            c."updateDate",
            c.type as conversation_scope,
            c."typeId" as type_id
        FROM "conversation_v1" c
        WHERE 
            -- No title or empty title
            (c.title IS NULL OR LENGTH(TRIM(c.title)) = 0)
            
            -- Not deleted
            AND c."deletedAt" IS NULL
            
            -- Recent conversations (last 90 days) - focus on recent ones first
            AND c."createDate" >= NOW() - INTERVAL '90 days'
            
        ORDER BY c."createDate" DESC
        LIMIT %s
        """

        with conversation_db_operations.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (max_conversations,))
                rows = cursor.fetchall()

                conversations = []
                for row in rows:
                    # Convert the row to a dictionary and process messages
                    conv_dict = {
                        'id': row[0],
                        'user_id': row[1],
                        'messages': row[2] or [],
                        'createDate': row[3],
                        'updateDate': row[4],
                        'conversation_scope': row[5],
                        'type_id': row[6]
                    }

                    # Parse messages if they exist
                    messages = conv_dict.get('messages', [])
                    if isinstance(messages, str):
                        import json
                        try:
                            messages = json.loads(messages)
                        except json.JSONDecodeError:
                            messages = []

                    conv_dict['messages'] = messages or []
                    conversations.append(conv_dict)

                logger.info(
                    f"📊 Found {len(conversations)} conversations without titles")
                return conversations

    except Exception as e:
        logger.error(f"❌ Failed to get conversations without titles: {e}")
        raise


def _update_conversation_title_sync(conversation_id: int, title: str) -> bool:
    """Synchronous version of update conversation title"""
    try:
        query = """
        UPDATE "conversation_v1" 
        SET 
            title = %s,
            "updateDate" = NOW()
        WHERE 
            id = %s 
            AND "deletedAt" IS NULL
        """

        with conversation_db_operations.db_manager.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (title, conversation_id))
                rows_affected = cursor.rowcount
                conn.commit()

                # Check if any row was updated
                if rows_affected > 0:
                    logger.info(
                        f"✅ Updated conversation {conversation_id} title: '{title}'")
                    return True
                else:
                    logger.warning(
                        f"⚠️ No conversation found with ID {conversation_id} to update")
                    return False

    except Exception as e:
        logger.error(
            f"❌ Failed to update conversation {conversation_id} title: {e}")
        raise
