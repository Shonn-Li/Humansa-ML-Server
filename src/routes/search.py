import logging
from quart import Blueprint, jsonify, request
from src.services.search_service import search_service

logger = logging.getLogger(__name__)
search_bp = Blueprint('search', __name__)


@search_bp.route("/search/keyword", methods=["POST"])
async def keyword_search_endpoint():
    """Keyword search endpoint using PostgreSQL full-text search"""
    try:
        request_data = await request.get_json()
        
        if not request_data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate request
        is_valid, error_msg, params = search_service.validate_search_request(request_data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        logger.info(f"Keyword search for user {params['user_id']}: '{params['query']}' (limit: {params['limit']})")
        
        # Perform search
        results = search_service.keyword_search(
            params['query'], 
            params['user_id'], 
            params['limit']
        )
        
        return jsonify({
            "query": params['query'],
            "user_id": params['user_id'],
            "total_results": len(results),
            "results": [result.to_dict() for result in results]
        })
        
    except Exception as e:
        logger.error(f"Error in keyword search endpoint: {e}")
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@search_bp.route("/search/advanced", methods=["POST"])
async def advanced_search_endpoint():
    """Advanced keyword search endpoint with source filtering"""
    try:
        request_data = await request.get_json()
        
        if not request_data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate request
        is_valid, error_msg, params = search_service.validate_search_request(request_data)
        if not is_valid:
            return jsonify({"error": error_msg}), 400
        
        logger.info(f"Advanced search for user {params['user_id']}: '{params['query']}' (source: {params['source_filter']}, limit: {params['limit']})")
        
        # Perform advanced search
        search_results = search_service.advanced_search(
            params['query'],
            params['user_id'],
            params['source_filter'],
            params['limit']
        )
        
        return jsonify({
            "query": params['query'],
            "user_id": params['user_id'],
            "source_filter": params['source_filter'],
            **search_results
        })
        
    except Exception as e:
        logger.error(f"Error in advanced search endpoint: {e}")
        return jsonify({"error": f"Advanced search failed: {str(e)}"}), 500
