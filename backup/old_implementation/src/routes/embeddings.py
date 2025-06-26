import asyncio
import logging
from quart import Blueprint, jsonify, request
from src.services.job_service import job_service
from src.services.embedding_service import embedding_service
from src.models.response import JobResponse

logger = logging.getLogger(__name__)
embeddings_bp = Blueprint('embeddings', __name__)


@embeddings_bp.route("/admin/embed-user-notes", methods=["POST"])
async def embed_user_notes():
    """Create embeddings for all notes and conversations of a user"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Get user notes
        note_ids = embedding_service.get_user_notes(user_id)
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(
            note_ids) if note_ids else []

        # Get user conversations
        conversation_ids = embedding_service.get_user_conversations(user_id)
        conversations_without_embeddings = embedding_service.get_conversations_needing_embeddings(
            conversation_ids) if conversation_ids else []

        if not notes_without_embeddings and not conversations_without_embeddings:
            return jsonify({
                "message": f"All {len(note_ids)} notes and {len(conversation_ids)} conversations for user {user_id} already have embeddings",
                "embedded_notes": 0,
                "embedded_conversations": 0
            })

        # Create background job
        job_id = job_service.create_job(
            "embed_user_notes_conversations", user_id)

        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="embed_user_notes_conversations",
            note_ids=notes_without_embeddings,
            conversation_ids=conversations_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message=f"Embedding job started for user {user_id} (notes + conversations)",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings) +
            len(conversations_without_embeddings),
            user_id=user_id
        )

        return jsonify({
            **response.to_dict(),
            "notes_to_embed": len(notes_without_embeddings),
            "conversations_to_embed": len(conversations_without_embeddings),
            "total_user_notes": len(note_ids),
            "total_user_conversations": len(conversation_ids)
        })

    except Exception as e:
        logger.error(f"Error in embed_user_notes: {e}")
        return jsonify({"error": f"Failed to start embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/embed-all-notes", methods=["POST"])
async def embed_all_notes():
    """Create embeddings for all notes and conversations in the system"""
    try:
        data = await request.get_json()

        # Validate request
        is_valid, error_msg = embedding_service.validate_embed_request(
            data, require_confirm=True)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Get all notes
        all_notes = embedding_service.get_all_notes()
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(
            all_notes) if all_notes else []

        # Get all conversations
        all_conversations = embedding_service.get_all_conversations()
        conversations_without_embeddings = embedding_service.get_conversations_needing_embeddings(
            all_conversations) if all_conversations else []

        if not notes_without_embeddings and not conversations_without_embeddings:
            return jsonify({
                "message": f"All {len(all_notes)} notes and {len(all_conversations)} conversations already have embeddings",
                "embedded_notes": 0,
                "embedded_conversations": 0
            })

        # Create background job
        job_id = job_service.create_job("embed_all_notes_conversations")

        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="embed_all_notes_conversations",
            note_ids=notes_without_embeddings,
            conversation_ids=conversations_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message="System-wide embedding job started (notes + conversations)",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings) +
            len(conversations_without_embeddings)
        )

        return jsonify({
            **response.to_dict(),
            "notes_to_embed": len(notes_without_embeddings),
            "conversations_to_embed": len(conversations_without_embeddings),
            "total_notes": len(all_notes),
            "total_conversations": len(all_conversations)
        })

    except Exception as e:
        logger.error(f"Error in embed_all_notes: {e}")
        return jsonify({"error": f"Failed to start embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/re-embed-all-notes", methods=["POST"])
async def re_embed_all_notes():
    """Re-embed all notes and conversations with new optimized settings"""
    try:
        data = await request.get_json()

        # Validate request
        is_valid, error_msg = embedding_service.validate_embed_request(
            data, require_confirm=True)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Get all notes and conversations
        all_notes = embedding_service.get_all_notes()
        all_conversations = embedding_service.get_all_conversations()

        if not all_notes and not all_conversations:
            return jsonify({
                "message": "No notes or conversations found in the system",
                "re_embedded_notes": 0,
                "re_embedded_conversations": 0
            })

        # Delete existing embeddings
        embedding_service.delete_all_embeddings()

        # Create background job
        job_id = job_service.create_job("re_embed_all_notes_conversations")

        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="re_embed_all_notes_conversations",
            note_ids=all_notes,
            conversation_ids=all_conversations,
            batch_size=5
        ))

        response = JobResponse(
            job_id=job_id,
            message="Re-embedding job started in background (notes + conversations)",
            status_url=f"/jobs/{job_id}",
            total_items=len(all_notes) + len(all_conversations)
        )

        return jsonify({
            **response.to_dict(),
            "notes_to_re_embed": len(all_notes),
            "conversations_to_re_embed": len(all_conversations),
            "optimization_applied": {
                "chunk_size": 1024,
                "chunk_overlap": 100,
                "separate_ai_user_content": True,
                "source_tagging": True,
                "conversation_pairing": True
            }
        })

    except Exception as e:
        logger.error(f"Error in re_embed_all_notes: {e}")
        return jsonify({"error": f"Failed to start re-embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/resume-embeddings", methods=["POST"])
async def resume_embeddings():
    """Resume embedding creation for notes and conversations that don't have embeddings yet"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")  # Optional: limit to specific user

        # Get notes and conversations (filtered by user if specified)
        if user_id:
            all_notes = embedding_service.get_user_notes(user_id)
            all_conversations = embedding_service.get_user_conversations(
                user_id)
        else:
            all_notes = embedding_service.get_all_notes()
            all_conversations = embedding_service.get_all_conversations()

        # Check which need embeddings
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(
            all_notes) if all_notes else []
        conversations_without_embeddings = embedding_service.get_conversations_needing_embeddings(
            all_conversations) if all_conversations else []

        if not notes_without_embeddings and not conversations_without_embeddings:
            return jsonify({
                "message": "All notes and conversations already have embeddings",
                "total_notes": len(all_notes),
                "total_conversations": len(all_conversations),
                "embedded_notes": 0,
                "embedded_conversations": 0
            })

        # Create background job
        job_id = job_service.create_job("resume_embeddings", user_id)

        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="resume_embeddings",
            note_ids=notes_without_embeddings,
            conversation_ids=conversations_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message="Resume embedding job started (notes + conversations)",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings) +
            len(conversations_without_embeddings),
            user_id=user_id
        )

        return jsonify({
            **response.to_dict(),
            "notes_to_embed": len(notes_without_embeddings),
            "conversations_to_embed": len(conversations_without_embeddings),
            "total_notes": len(all_notes),
            "total_conversations": len(all_conversations)
        })

    except Exception as e:
        logger.error(f"Error in resume_embeddings: {e}")
        return jsonify({"error": f"Failed to start resume embedding job: {str(e)}"}), 500
