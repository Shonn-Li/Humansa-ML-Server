"""
Admin Embedding Endpoint - Provides admin endpoints for bulk embedding operations.

This replaces the old re-embedding endpoint with a clean, modular approach
that only embeds missing items (no re-embedding needed).
"""

import logging
import asyncio
from quart import Blueprint, jsonify, request
from .embedding_manager import embedding_manager

logger = logging.getLogger(__name__)
admin_embedding_bp = Blueprint('admin_embedding', __name__)


@admin_embedding_bp.route("/admin/embed-missing-notes", methods=["POST"])
async def embed_missing_notes():
    """
    Embed all notes that don't have embeddings yet.
    """
    try:
        data = await request.get_json() or {}
        user_id = data.get("user_id")  # Optional: limit to specific user
        confirm = data.get("confirm_embed_all", False)

        # Require confirmation for system-wide embedding
        if not user_id and not confirm:
            return jsonify({
                "error": "System-wide embedding requires confirmation. Set 'confirm_embed_all': true"
            }), 400

        # Start embedding process
        if user_id:
            result = await embedding_manager.embed_all_missing_notes(user_id)
            scope = f"user {user_id}"
        else:
            result = await embedding_manager.embed_all_missing_notes()
            scope = "system-wide"

        return jsonify({
            **result,
            "scope": scope,
            "message": f"Embedding completed for {scope}: {result['message']}"
        })

    except Exception as e:
        logger.error(f"Error in embed_missing_notes: {e}")
        return jsonify({"error": f"Failed to embed missing notes: {str(e)}"}), 500


@admin_embedding_bp.route("/admin/embed-missing-conversations", methods=["POST"])
async def embed_missing_conversations():
    """
    Embed all conversations that don't have embeddings yet.
    """
    try:
        data = await request.get_json() or {}
        user_id = data.get("user_id")  # Optional: limit to specific user
        confirm = data.get("confirm_embed_all", False)

        # Require confirmation for system-wide embedding
        if not user_id and not confirm:
            return jsonify({
                "error": "System-wide embedding requires confirmation. Set 'confirm_embed_all': true"
            }), 400

        # Start embedding process
        if user_id:
            result = await embedding_manager.embed_all_missing_conversations(user_id)
            scope = f"user {user_id}"
        else:
            result = await embedding_manager.embed_all_missing_conversations()
            scope = "system-wide"

        return jsonify({
            **result,
            "scope": scope,
            "message": f"Conversation embedding completed for {scope}: {result['message']}"
        })

    except Exception as e:
        logger.error(f"Error in embed_missing_conversations: {e}")
        return jsonify({"error": f"Failed to embed missing conversations: {str(e)}"}), 500


@admin_embedding_bp.route("/admin/embed-all-missing", methods=["POST"])
async def embed_all_missing():
    """
    Embed all missing notes AND conversations in one operation.
    This is the main admin endpoint to ensure all content has embeddings.
    """
    try:
        data = await request.get_json() or {}
        user_id = data.get("user_id")  # Optional: limit to specific user
        confirm = data.get("confirm_embed_all", False)

        # Require confirmation for system-wide embedding
        if not user_id and not confirm:
            return jsonify({
                "error": "System-wide embedding requires confirmation. Set 'confirm_embed_all': true"
            }), 400

        # Start both embedding processes
        logger.info(
            f"Starting combined embedding for {'user ' + str(user_id) if user_id else 'system-wide'}")

        # Run both in parallel
        notes_task = embedding_manager.embed_all_missing_notes(user_id)
        conversations_task = embedding_manager.embed_all_missing_conversations(
            user_id)

        notes_result, conversations_result = await asyncio.gather(
            notes_task, conversations_task, return_exceptions=True
        )

        # Handle any exceptions
        if isinstance(notes_result, Exception):
            logger.error(f"Notes embedding failed: {notes_result}")
            notes_result = {"status": "error", "message": str(
                notes_result), "embedded_count": 0}

        if isinstance(conversations_result, Exception):
            logger.error(
                f"Conversations embedding failed: {conversations_result}")
            conversations_result = {"status": "error", "message": str(
                conversations_result), "embedded_count": 0}

        # Combine results
        total_embedded = notes_result.get(
            "embedded_count", 0) + conversations_result.get("embedded_count", 0)
        total_items = notes_result.get(
            "total_notes", 0) + conversations_result.get("total_conversations", 0)

        scope = f"user {user_id}" if user_id else "system-wide"

        return jsonify({
            "status": "success",
            "scope": scope,
            "total_embedded": total_embedded,
            "total_items": total_items,
            "notes": {
                "embedded_count": notes_result.get("embedded_count", 0),
                "total_notes": notes_result.get("total_notes", 0),
                "failed_notes": notes_result.get("failed_notes", []),
                "status": notes_result.get("status", "unknown")
            },
            "conversations": {
                "embedded_count": conversations_result.get("embedded_count", 0),
                "total_conversations": conversations_result.get("total_conversations", 0),
                "failed_conversations": conversations_result.get("failed_conversations", []),
                "status": conversations_result.get("status", "unknown")
            },
            "message": f"Combined embedding completed for {scope}: {total_embedded} items embedded"
        })

    except Exception as e:
        logger.error(f"Error in embed_all_missing: {e}")
        return jsonify({"error": f"Failed to embed all missing items: {str(e)}"}), 500


@admin_embedding_bp.route("/admin/embedding-status", methods=["GET"])
async def embedding_status():
    """Get status of embedding coverage in the system"""
    try:
        user_id = request.args.get("user_id", type=int)

        if user_id:
            # Get user-specific status
            from src.chat.embedding.note_embedder import NoteEmbedder
            from src.chat.embedding.conversation_embedder import ConversationEmbedder

            note_embedder = NoteEmbedder()
            conversation_embedder = ConversationEmbedder()

            # Get user notes and conversations
            user_notes = await note_embedder.get_user_notes(user_id)
            user_conversations = await conversation_embedder.get_user_conversations(user_id)

            # Check missing embeddings
            notes_missing = await note_embedder.get_notes_without_embeddings(user_notes)
            conversations_missing = await conversation_embedder.get_conversations_without_embeddings(user_conversations)

            return jsonify({
                "user_id": user_id,
                "notes": {
                    "total": len(user_notes),
                    "with_embeddings": len(user_notes) - len(notes_missing),
                    "missing_embeddings": len(notes_missing),
                    "coverage_percent": round((len(user_notes) - len(notes_missing)) / len(user_notes) * 100, 2) if user_notes else 100
                },
                "conversations": {
                    "total": len(user_conversations),
                    "with_embeddings": len(user_conversations) - len(conversations_missing),
                    "missing_embeddings": len(conversations_missing),
                    "coverage_percent": round((len(user_conversations) - len(conversations_missing)) / len(user_conversations) * 100, 2) if user_conversations else 100
                },
                "active_embedding_tasks": embedding_manager.get_active_embedding_tasks()
            })
        else:
            # Get system-wide status
            from src.chat.embedding.note_embedder import NoteEmbedder
            from src.chat.embedding.conversation_embedder import ConversationEmbedder

            note_embedder = NoteEmbedder()
            conversation_embedder = ConversationEmbedder()

            # Get all notes and conversations
            all_notes = await note_embedder.get_all_notes()
            all_conversations = await conversation_embedder.get_all_conversations()

            # Check missing embeddings
            notes_missing = await note_embedder.get_notes_without_embeddings(all_notes)
            conversations_missing = await conversation_embedder.get_conversations_without_embeddings(all_conversations)

            return jsonify({
                "system_wide": True,
                "notes": {
                    "total": len(all_notes),
                    "with_embeddings": len(all_notes) - len(notes_missing),
                    "missing_embeddings": len(notes_missing),
                    "coverage_percent": round((len(all_notes) - len(notes_missing)) / len(all_notes) * 100, 2) if all_notes else 100
                },
                "conversations": {
                    "total": len(all_conversations),
                    "with_embeddings": len(all_conversations) - len(conversations_missing),
                    "missing_embeddings": len(conversations_missing),
                    "coverage_percent": round((len(all_conversations) - len(conversations_missing)) / len(all_conversations) * 100, 2) if all_conversations else 100
                },
                "active_embedding_tasks": embedding_manager.get_active_embedding_tasks()
            })

    except Exception as e:
        logger.error(f"Error in embedding_status: {e}")
        return jsonify({"error": f"Failed to get embedding status: {str(e)}"}), 500


@admin_embedding_bp.route("/admin/stop-embeddings", methods=["POST"])
async def stop_embeddings():
    """Stop all currently running embedding tasks"""
    try:
        active_tasks = embedding_manager.get_active_embedding_tasks()

        if not active_tasks:
            return jsonify({
                "message": "No active embedding tasks to stop",
                "stopped_tasks": []
            })

        # Cancel all embedding tasks
        for task_key, task in embedding_manager._embedding_tasks.items():
            if not task.done():
                task.cancel()

        # Clear all tasks
        embedding_manager._embedding_tasks.clear()

        return jsonify({
            "message": f"Stopped {len(active_tasks)} embedding tasks",
            "stopped_tasks": active_tasks
        })

    except Exception as e:
        logger.error(f"Error stopping embeddings: {e}")
        return jsonify({"error": f"Failed to stop embeddings: {str(e)}"}), 500
