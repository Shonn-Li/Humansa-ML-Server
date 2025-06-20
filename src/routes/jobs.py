from quart import Blueprint, jsonify
from src.services.job_service import job_service

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route("/jobs/<job_id>", methods=["GET"])
async def get_job_status(job_id: str):
    """Get the status of a background job"""
    job = job_service.get_job(job_id)
    
    if not job:
        return jsonify({"error": "Job not found"}), 404
    
    return jsonify(job.to_dict())


@jobs_bp.route("/jobs", methods=["GET"])
async def list_jobs():
    """List all background jobs (for debugging)"""
    jobs = job_service.list_jobs()
    return jsonify({
        "jobs": [job.to_dict() for job in jobs],
        "total": len(jobs)
    })
