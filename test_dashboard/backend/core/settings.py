"""
Dashboard Settings Management
============================

Manages persistent settings for the test dashboard including multi-instance configuration.
Settings are stored in a JSON file and can be updated via API or UI.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class MultiInstanceSettings(BaseModel):
    """Multi-instance ML server settings"""
    enabled: bool = Field(default=True, description="Enable multi-instance mode by default")
    default_instances: int = Field(default=4, ge=1, le=8, description="Default number of instances to launch")
    auto_start: bool = Field(default=True, description="Automatically start instances on dashboard launch")
    max_workers_per_job: int = Field(default=8, ge=1, le=8, description="Default max workers for new jobs - increased to maximize instance usage")


class DashboardSettings(BaseModel):
    """Main dashboard settings"""
    multi_instance: MultiInstanceSettings = Field(default_factory=MultiInstanceSettings)
    ml_server_port: int = Field(default=6001, description="Base ML server port (single-instance mode)")
    ml_server_digit: int = Field(default=1, description="ML server digit for single-instance mode")
    enable_enhanced_logging: bool = Field(default=True, description="Enable ML server enhanced logging")
    auto_discover_tests: bool = Field(default=True, description="Auto-discover tests on startup")


class SettingsManager:
    """Manages persistent settings with file-based storage"""
    
    def __init__(self, settings_file: str = None):
        if settings_file is None:
            # Use backend directory for settings file
            import os
            backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            settings_file = os.path.join(backend_dir, "dashboard_settings.json")
        self.settings_file = Path(settings_file)
        self.settings: DashboardSettings = self.load()
    
    def load(self) -> DashboardSettings:
        """Load settings from file or create defaults"""
        if self.settings_file.exists():
            try:
                with open(self.settings_file, 'r') as f:
                    data = json.load(f)
                    return DashboardSettings(**data)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")
                return DashboardSettings()
        else:
            # Create default settings
            settings = DashboardSettings()
            self.save(settings)
            return settings
    
    def save(self, settings: Optional[DashboardSettings] = None) -> None:
        """Save settings to file"""
        if settings:
            self.settings = settings
        
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings.dict(), f, indent=2)
            logger.info(f"Settings saved to {self.settings_file}")
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")
    
    def update(self, updates: Dict[str, Any]) -> DashboardSettings:
        """Update settings with partial data"""
        try:
            # Deep update the settings
            current_data = self.settings.dict()
            
            # Handle nested updates
            for key, value in updates.items():
                if key == "multi_instance" and isinstance(value, dict):
                    current_data["multi_instance"].update(value)
                else:
                    current_data[key] = value
            
            self.settings = DashboardSettings(**current_data)
            self.save()
            return self.settings
        except Exception as e:
            logger.error(f"Failed to update settings: {e}")
            raise
    
    def get(self) -> DashboardSettings:
        """Get current settings"""
        return self.settings
    
    def reset(self) -> DashboardSettings:
        """Reset to default settings"""
        self.settings = DashboardSettings()
        self.save()
        return self.settings


# Global settings manager instance
settings_manager = SettingsManager()


# Convenience functions for backward compatibility
def get_settings() -> DashboardSettings:
    """Get current dashboard settings"""
    return settings_manager.get()


def update_settings(updates: Dict[str, Any]) -> DashboardSettings:
    """Update dashboard settings"""
    return settings_manager.update(updates)


def get_multi_instance_config() -> MultiInstanceSettings:
    """Get multi-instance configuration"""
    return settings_manager.get().multi_instance