"""
Settings API Endpoints
======================

API endpoints for managing dashboard settings including multi-instance configuration.
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from test_dashboard.backend.core.settings import (
    settings_manager,
    DashboardSettings,
    MultiInstanceSettings
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=DashboardSettings)
async def get_settings():
    """Get current dashboard settings"""
    return settings_manager.get()


@router.put("/", response_model=DashboardSettings)
async def update_settings(updates: Dict[str, Any]):
    """Update dashboard settings"""
    try:
        updated = settings_manager.update(updates)
        return updated
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reset", response_model=DashboardSettings)
async def reset_settings():
    """Reset settings to defaults"""
    return settings_manager.reset()


@router.get("/multi-instance", response_model=MultiInstanceSettings)
async def get_multi_instance_settings():
    """Get multi-instance specific settings"""
    return settings_manager.get().multi_instance


@router.put("/multi-instance", response_model=MultiInstanceSettings)
async def update_multi_instance_settings(settings: MultiInstanceSettings):
    """Update multi-instance settings"""
    try:
        updates = {"multi_instance": settings.dict()}
        updated = settings_manager.update(updates)
        return updated.multi_instance
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/multi-instance/apply")
async def apply_multi_instance_settings():
    """Apply multi-instance settings (start/stop instances based on configuration)"""
    # Import instance_pool locally to avoid circular imports
    from test_dashboard.backend.api.instances import instance_pool
    
    settings = settings_manager.get().multi_instance
    
    try:
        current_status = await instance_pool.get_status()
        current_count = current_status["total_instances"]
        desired_count = settings.default_instances
        
        result = {
            "current_instances": current_count,
            "desired_instances": desired_count,
            "actions": []
        }
        
        if desired_count > current_count:
            # Need to add more instances
            logger.info(f"Adding {desired_count - current_count} instances")
            await instance_pool.initialize(desired_count)
            result["actions"].append(f"Started {desired_count - current_count} new instances")
        
        elif desired_count < current_count:
            # Need to remove instances
            logger.info(f"Reducing instances from {current_count} to {desired_count}")
            # Stop excess instances
            for digit in range(desired_count + 1, current_count + 1):
                if digit in instance_pool.instances:
                    await instance_pool.instances[digit].stop()
                    del instance_pool.instances[digit]
            result["actions"].append(f"Stopped {current_count - desired_count} instances")
        
        else:
            result["actions"].append("No changes needed")
        
        # Update status
        result["final_status"] = await instance_pool.get_status()
        return result
        
    except Exception as e:
        logger.error(f"Failed to apply multi-instance settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/launch-config")
async def get_launch_configuration():
    """Get the configuration that should be used for launching services"""
    settings = settings_manager.get()
    
    return {
        "multi_instance": {
            "enabled": settings.multi_instance.enabled,
            "instances": settings.multi_instance.default_instances,
            "auto_start": settings.multi_instance.auto_start
        },
        "ml_server": {
            "port": settings.ml_server_port,
            "digit": settings.ml_server_digit,
            "enhanced_logging": settings.enable_enhanced_logging
        },
        "dashboard": {
            "auto_discover_tests": settings.auto_discover_tests
        }
    }