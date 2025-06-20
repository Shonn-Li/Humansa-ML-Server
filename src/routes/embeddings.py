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
    """Create embeddings for all notes of a user"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Get user notes
        note_ids = embedding_service.get_user_notes(user_id)
        if not note_ids:
            return jsonify({
                "message": f"No notes found for user {user_id}",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(note_ids)
        if not notes_without_embeddings:
            return jsonify({
                "message": f"All {len(note_ids)} notes for user {user_id} already have embeddings",
                "embedded_notes": 0
            })

        # Create background job
        job_id = job_service.create_job("embed_user_notes", user_id)
        
        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="embed_user_notes",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message=f"Embedding job started for user {user_id}",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings),
            user_id=user_id
        )

        return jsonify(response.to_dict())

    except Exception as e:
        logger.error(f"Error in embed_user_notes: {e}")
        return jsonify({"error": f"Failed to start embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/embed-all-notes", methods=["POST"])
async def embed_all_notes():
    """Create embeddings for all notes in the system"""
    try:
        data = await request.get_json()
        
        # Validate request
        is_valid, error_msg = embedding_service.validate_embed_request(data, require_confirm=True)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Get all notes
        all_notes = embedding_service.get_all_notes()
        if not all_notes:
            return jsonify({
                "message": "No notes found in the system",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(all_notes)
        if not notes_without_embeddings:
            return jsonify({
                "message": f"All {len(all_notes)} notes in the system already have embeddings",
                "embedded_notes": 0
            })

        # Create background job
        job_id = job_service.create_job("embed_all_notes")
        
        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="embed_all_notes",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message="System-wide embedding job started",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings)
        )

        return jsonify(response.to_dict())

    except Exception as e:
        logger.error(f"Error in embed_all_notes: {e}")
        return jsonify({"error": f"Failed to start embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/re-embed-all-notes", methods=["POST"])
async def re_embed_all_notes():
    """Re-embed all notes with new optimized settings"""
    try:
        data = await request.get_json()
        
        # Validate request
        is_valid, error_msg = embedding_service.validate_embed_request(data, require_confirm=True)
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Get all notes
        all_notes = embedding_service.get_all_notes()
        if not all_notes:
            return jsonify({
                "message": "No notes found in the system",
                "re_embedded_notes": 0
            })

        # Delete existing embeddings
        embedding_service.delete_all_embeddings()

        # Create background job
        job_id = job_service.create_job("re_embed_all_notes")
        
        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="re_embed_all_notes", 
            note_ids=all_notes,
            batch_size=5
        ))

        response = JobResponse(
            job_id=job_id,
            message="Re-embedding job started in background",
            status_url=f"/jobs/{job_id}",
            total_items=len(all_notes)
        )

        return jsonify({
            **response.to_dict(),
            "optimization_applied": {
                "chunk_size": 1024,
                "chunk_overlap": 100,
                "separate_ai_user_content": True,
                "source_tagging": True
            }
        })

    except Exception as e:
        logger.error(f"Error in re_embed_all_notes: {e}")
        return jsonify({"error": f"Failed to start re-embedding job: {str(e)}"}), 500


@embeddings_bp.route("/admin/resume-embeddings", methods=["POST"])
async def resume_embeddings():
    """Resume embedding creation for notes that don't have embeddings yet"""
    try:
        data = await request.get_json()
        user_id = data.get("user_id")  # Optional: limit to specific user
        
        # Get notes (filtered by user if specified)
        if user_id:
            all_notes = embedding_service.get_user_notes(user_id)
        else:
            all_notes = embedding_service.get_all_notes()

        if not all_notes:
            return jsonify({
                "message": "No notes found",
                "embedded_notes": 0
            })

        # Check which notes need embeddings
        notes_without_embeddings = embedding_service.get_notes_needing_embeddings(all_notes)
        if not notes_without_embeddings:
            return jsonify({
                "message": "All notes already have embeddings",
                "total_notes": len(all_notes),
                "embedded_notes": 0
            })

        # Create background job
        job_id = job_service.create_job("resume_embeddings", user_id)
        
        # Start background task
        asyncio.create_task(job_service.run_embedding_job(
            job_id=job_id,
            job_type="resume_embeddings",
            note_ids=notes_without_embeddings,
            batch_size=10
        ))

        response = JobResponse(
            job_id=job_id,
            message="Resume embedding job started",
            status_url=f"/jobs/{job_id}",
            total_items=len(notes_without_embeddings),
            user_id=user_id
        )

        return jsonify(response.to_dict())

    except Exception as e:
        logger.error(f"Error in resume_embeddings: {e}")
        return jsonify({"error": f"Failed to start resume embedding job: {str(e)}"}), 500
