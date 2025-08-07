"""
Configuration settings for Test Management Dashboard
"""

import os
from typing import Optional

# Try to import pydantic_settings
try:
    from pydantic_settings import BaseSettings
    PYDANTIC_AVAILABLE = True
except ImportError:
    # Fallback to regular class if pydantic_settings not available
    PYDANTIC_AVAILABLE = False
    class BaseSettings:
        def __init__(self, **kwargs):
            # Set defaults for all the fields we need
            defaults = {
                'PORT': 6002,
                'DEBUG': True,
                'DB_HOST': 'localhost',
                'DB_PORT': 5432,
                'DB_USER': 'postgres',
                'DB_PASSWORD': '12931',
                'DB_NAME': 'test1',
                'ML_SERVER_PORT': None,
                'ML_SERVER_DIGIT': None,
                'MAX_PARALLEL_WORKERS': 8,
                'DEFAULT_TEST_TIMEOUT': 30,
                'LOG_BUFFER_SIZE': 1000,
                'TEST_DEFINITIONS_PATH': 'test_definitions',
                'TEST_RESULTS_PATH': 'test_results',
                'LOG_PATH': 'test_logs',
                'WS_HEARTBEAT_INTERVAL': 30,
                'WS_MESSAGE_QUEUE_SIZE': 100
            }
            
            # Set defaults first
            for key, value in defaults.items():
                setattr(self, key, value)
            
            # Override with any provided kwargs (ignoring extras)
            for key, value in kwargs.items():
                if hasattr(self, key):
                    setattr(self, key, value)
        
        class Config:
            env_file = ".env"
            case_sensitive = True
            extra = "ignore"


class Settings(BaseSettings):
    """Application settings"""
    
    # Server settings
    PORT: int = 6002
    DEBUG: bool = True
    
    # Database settings (inherit from ML server)
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: int = int(os.getenv("DB_PORT", "5432"))
    DB_USER: str = os.getenv("DB_USER", "postgres")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "12931")
    DB_NAME: str = os.getenv("DB_NAME", "test1")  # Will be updated based on ML_DIGIT
    
    # ML Server detection
    ML_SERVER_PORT: Optional[int] = None
    ML_SERVER_DIGIT: Optional[int] = None
    
    # Test execution settings
    MAX_PARALLEL_WORKERS: int = 8
    DEFAULT_TEST_TIMEOUT: int = 30
    LOG_BUFFER_SIZE: int = 1000
    
    # File paths
    TEST_DEFINITIONS_PATH: str = "test_definitions"
    TEST_RESULTS_PATH: str = "test_results"
    LOG_PATH: str = "test_logs"
    
    # WebSocket settings
    WS_HEARTBEAT_INTERVAL: int = 30
    WS_MESSAGE_QUEUE_SIZE: int = 100
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables that aren't defined as fields
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._detect_ml_server()
    
    def _detect_ml_server(self):
        """Detect running ML server port and calculate digit"""
        # First try to get digit directly from environment
        ml_digit = os.getenv("ML_DIGIT")
        if ml_digit:
            self.ML_SERVER_DIGIT = int(ml_digit)
            self.ML_SERVER_PORT = 6000 + self.ML_SERVER_DIGIT
            self.DB_NAME = f"test{self.ML_SERVER_DIGIT}"
            return
            
        # Try to detect from ML_SERVER_PORT environment
        ml_port = os.getenv("ML_SERVER_PORT")
        if ml_port:
            self.ML_SERVER_PORT = int(ml_port)
            self.ML_SERVER_DIGIT = self.ML_SERVER_PORT - 6000
            self.DB_NAME = f"test{self.ML_SERVER_DIGIT}"
            return
        
        # Try to detect from running processes
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                cmdline = proc.info.get('cmdline', [])
                if cmdline and 'src.main' in ' '.join(cmdline):
                    for i, arg in enumerate(cmdline):
                        if arg == '--port' and i + 1 < len(cmdline):
                            port = int(cmdline[i + 1])
                            if 6000 <= port < 6100:
                                self.ML_SERVER_PORT = port
                                self.ML_SERVER_DIGIT = port - 6000
                                self.DB_NAME = f"test{self.ML_SERVER_DIGIT}"
                                return
        except:
            pass
        
        # Default values if nothing found
        self.ML_SERVER_DIGIT = 1
        self.ML_SERVER_PORT = 6001
        self.DB_NAME = "test1"
    
    @property
    def database_url(self) -> str:
        """Get PostgreSQL connection URL"""
        try:
            return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        except Exception as e:
            # Return a default URL if there are issues with the configuration
            return "postgresql+asyncpg://postgres:password@localhost:5432/test_dashboard"
    
    @property
    def ml_server_url(self) -> str:
        """Get ML server URL"""
        port = self.ML_SERVER_PORT or 6001
        return f"http://localhost:{port}"


# Create settings instance
settings = Settings()