"""
ML Server Instance Management
=============================

Manages multiple ML server instances with isolated databases for parallel test execution.
"""

import asyncio
import os
import subprocess
import time
import logging
import httpx
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None
    PSUTIL_AVAILABLE = False
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from pathlib import Path


logger = logging.getLogger(__name__)


class InstanceStatus(str, Enum):
    """ML server instance status"""
    STARTING = "starting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    STOPPED = "stopped"


class MLServerInstance(BaseModel):
    """Represents a single ML server instance with its own database"""
    digit: int = Field(ge=1, le=8)
    ml_port: int
    db_port: int
    container_name: str
    status: InstanceStatus = InstanceStatus.STOPPED
    process: Optional[Any] = Field(None, exclude=True)  # subprocess.Popen instance
    started_at: Optional[datetime] = None
    last_health_check: Optional[datetime] = None
    current_test_id: Optional[str] = None
    current_worker_id: Optional[int] = None
    memory_usage_mb: float = 0.0
    cpu_percent: float = 0.0
    total_tests_run: int = 0
    
    class Config:
        arbitrary_types_allowed = True
    
    @classmethod
    def create(cls, digit: int) -> "MLServerInstance":
        """Create a new instance configuration"""
        return cls(
            digit=digit,
            ml_port=6010 + digit,  # Use 601X range to avoid conflicts
            db_port=5060 + digit,  # Use 506X range to avoid conflicts
            container_name=f"humansa_test_db_{digit}"
        )
    
    async def start(self) -> bool:
        """Start the ML server instance"""
        try:
            self.status = InstanceStatus.STARTING
            logger.info(f"🚀 Starting ML server instance {self.digit} on port {self.ml_port}")
            
            # Check if port is available (important for port 6002 conflict)
            if not self._is_port_available(self.ml_port):
                logger.error(f"❌ Port {self.ml_port} is already in use (instance {self.digit})")
                self.status = InstanceStatus.ERROR
                return False
                
            # Check if database is ready
            if not await self._check_database():
                logger.error(f"❌ Database not ready for instance {self.digit}")
                self.status = InstanceStatus.ERROR
                return False
            
            # Prepare environment variables - copy current environment and override specific values
            env = os.environ.copy()
            
            # Override with instance-specific settings
            env.update({
                "DIGIT": str(self.digit),
                "ML_SERVER_PORT": str(self.ml_port),
                "DB_HOST": "127.0.0.1",  # Use IPv4 explicitly to avoid IPv6 issues
                "DB_PORT": str(self.db_port),
                "DB_NAME": "youwoai",
                "DB_USER": "youwo",
                "DB_PASSWORD": "youwo123",
                "HUMANSA_ENHANCED_LOGGING": "true",
                "INSTANCE_ID": str(self.digit),
                "PYTHONPATH": str(Path(__file__).parent.parent.parent.parent)
            })
            
            # Start ML server process using virtual environment
            # Define repo root - go up to the main repository root
            repo_root = Path(__file__).parent.parent.parent.parent
            
            # Use the simple start script
            script_path = Path(__file__).parent.parent / "start_ml_instance_simple.sh"
            cmd = [
                "bash", str(script_path),
                str(self.ml_port), str(self.digit)
            ]
            
            # Create log file for this instance
            log_file = f"/tmp/ml_server_instance_{self.digit}.log"
            with open(log_file, 'w') as log:
                self.process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    cwd=str(repo_root)
                )
            
            # Wait for server to be ready
            if await self._wait_for_ready():
                self.status = InstanceStatus.READY
                self.started_at = datetime.now()
                logger.info(f"✅ ML server instance {self.digit} is ready on port {self.ml_port}")
                return True
            else:
                logger.error(f"❌ ML server instance {self.digit} failed to start")
                await self.stop()
                return False
                
        except Exception as e:
            logger.error(f"❌ Error starting instance {self.digit}: {e}")
            self.status = InstanceStatus.ERROR
            return False
    
    async def stop(self) -> None:
        """Stop the ML server instance"""
        if self.process and self.process.poll() is None:
            logger.info(f"🛑 Stopping ML server instance {self.digit}")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        
        self.status = InstanceStatus.STOPPED
        self.current_test_id = None
        self.current_worker_id = None
    
    async def health_check(self) -> bool:
        """Check if the instance is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"http://localhost:{self.ml_port}/health")
                if resp.status_code == 200:
                    self.last_health_check = datetime.now()
                    
                    # Update resource usage if process exists
                    if self.process and PSUTIL_AVAILABLE:
                        try:
                            proc = psutil.Process(self.process.pid)
                            self.memory_usage_mb = proc.memory_info().rss / 1024 / 1024
                            self.cpu_percent = proc.cpu_percent(interval=0.1)
                        except:
                            pass
                    
                    return True
        except:
            pass
        return False
    
    async def _check_database(self, max_tries: int = 10) -> bool:
        """Check if the database is ready"""
        import asyncpg
        
        for attempt in range(max_tries):
            try:
                conn = await asyncpg.connect(
                    host="127.0.0.1",  # Use IPv4 explicitly
                    port=self.db_port,
                    user="youwo",
                    password="youwo123",
                    database="youwoai"
                )
                await conn.fetchval("SELECT 1")
                await conn.close()
                return True
            except Exception as e:
                if attempt < max_tries - 1:
                    await asyncio.sleep(2)
                else:
                    logger.error(f"Database check failed for instance {self.digit}: {e}")
        return False
    
    async def _wait_for_ready(self, timeout: int = 60) -> bool:
        """Wait for ML server to be ready"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if await self.health_check():
                return True
            await asyncio.sleep(2)
        
        return False
    
    def _is_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return True
            except OSError:
                return False
    
    def is_available(self) -> bool:
        """Check if instance is available for new tests"""
        return (
            self.status == InstanceStatus.READY and
            self.current_test_id is None
        )
    
    def allocate(self, test_id: str, worker_id: int) -> None:
        """Allocate instance to a test"""
        self.current_test_id = test_id
        self.current_worker_id = worker_id
        self.status = InstanceStatus.BUSY
    
    def release(self) -> None:
        """Release instance after test completion"""
        self.current_test_id = None
        self.current_worker_id = None
        self.status = InstanceStatus.READY
        self.total_tests_run += 1


class InstancePool:
    """Manages a pool of ML server instances"""
    
    def __init__(self, max_instances: int = 4):
        self.max_instances = min(max_instances, 8)  # Hard limit of 8
        self.instances: Dict[int, MLServerInstance] = {}
        self._lock = asyncio.Lock()
        self._last_allocated_digit = 0  # For round-robin allocation
    
    async def initialize(self, num_instances: int = None) -> None:
        """Initialize the instance pool"""
        if num_instances:
            self.max_instances = min(num_instances, 8)
        
        logger.info(f"🏊 Initializing instance pool with {self.max_instances} instances")
        
        # Clear existing instances first
        if self.instances:
            logger.info("Clearing existing instance pool...")
            await self.shutdown()
            self.instances.clear()
        
        # Start instances in parallel
        tasks = []
        digits_to_use = list(range(1, self.max_instances + 1))
        
        for digit in digits_to_use:
            instance = MLServerInstance.create(digit)
            self.instances[digit] = instance
            tasks.append(instance.start())
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log results
        success_count = sum(1 for r in results if r is True)
        logger.info(f"✅ Started {success_count}/{self.max_instances} instances successfully")
    
    async def get_available_instance(self) -> Optional[MLServerInstance]:
        """Get an available instance from the pool using round-robin"""
        async with self._lock:
            # Get sorted digits for consistent ordering
            sorted_digits = sorted(self.instances.keys())
            if not sorted_digits:
                return None
            
            # Start from the digit after the last allocated one
            start_idx = 0
            for i, digit in enumerate(sorted_digits):
                if digit > self._last_allocated_digit:
                    start_idx = i
                    break
            
            # Try instances in round-robin order
            for i in range(len(sorted_digits)):
                idx = (start_idx + i) % len(sorted_digits)
                digit = sorted_digits[idx]
                instance = self.instances[digit]
                
                if instance.is_available():
                    self._last_allocated_digit = digit
                    return instance
            
            return None
    
    async def allocate_instance(self, test_id: str, worker_id: int) -> Optional[MLServerInstance]:
        """Allocate an instance for a test"""
        instance = await self.get_available_instance()
        if instance:
            instance.allocate(test_id, worker_id)
            logger.info(f"🎯 Allocated instance {instance.digit} (port {instance.ml_port}) to test {test_id} (worker {worker_id}) - Round-robin distribution")
        else:
            logger.warning(f"⚠️ No available instance for test {test_id} (worker {worker_id})")
        return instance
    
    async def release_instance(self, digit: int) -> None:
        """Release an instance back to the pool"""
        async with self._lock:
            if digit in self.instances:
                self.instances[digit].release()
                logger.info(f"🔄 Released instance {digit} back to pool")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get pool status"""
        total_instances = len(self.instances)
        available = sum(1 for i in self.instances.values() if i.is_available())
        busy = sum(1 for i in self.instances.values() if i.status == InstanceStatus.BUSY)
        error = sum(1 for i in self.instances.values() if i.status == InstanceStatus.ERROR)
        
        return {
            "total_instances": total_instances,
            "available": available,
            "busy": busy,
            "error": error,
            "instances": [
                {
                    "digit": i.digit,
                    "ml_port": i.ml_port,
                    "db_port": i.db_port,
                    "status": i.status,
                    "current_test": i.current_test_id,
                    "memory_mb": round(i.memory_usage_mb, 1),
                    "cpu_percent": round(i.cpu_percent, 1),
                    "total_tests": i.total_tests_run
                }
                for i in self.instances.values()
            ]
        }
    
    async def health_check_all(self) -> None:
        """Health check all instances"""
        tasks = [instance.health_check() for instance in self.instances.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def shutdown(self) -> None:
        """Shutdown all instances"""
        logger.info("🛑 Shutting down instance pool")
        tasks = [instance.stop() for instance in self.instances.values()]
        await asyncio.gather(*tasks, return_exceptions=True)


# Global instance pool
instance_pool = InstancePool()


# API Router
router = APIRouter()


@router.post("/initialize")
async def initialize_pool(num_instances: int = 4):
    """Initialize the instance pool"""
    try:
        await instance_pool.initialize(num_instances)
        status = await instance_pool.get_status()
        return {"message": "Instance pool initialized", "status": status}
    except Exception as e:
        logger.error(f"Failed to initialize pool: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_instances():
    """Sync instance pool with already running ML servers"""
    try:
        # Initialize pool if empty
        if not instance_pool.instances:
            instance_pool.instances = {
                i: MLServerInstance.create(i) 
                for i in range(1, 5)  # Default to 4 instances
            }
        
        # Check each instance's health and update status
        for instance in instance_pool.instances.values():
            # Check if ML server is responsive
            if await instance.health_check():
                instance.status = InstanceStatus.READY
                logger.info(f"✅ Instance {instance.digit} is already running on port {instance.ml_port}")
            else:
                instance.status = InstanceStatus.STOPPED
                logger.info(f"❌ Instance {instance.digit} is not running on port {instance.ml_port}")
        
        status = await instance_pool.get_status()
        return {"message": "Instance pool synced", "status": status}
    except Exception as e:
        logger.error(f"Failed to sync instances: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_pool_status():
    """Get instance pool status"""
    return await instance_pool.get_status()


@router.post("/allocate")
async def allocate_instance(test_id: str, worker_id: int):
    """Allocate an instance for a test"""
    instance = await instance_pool.allocate_instance(test_id, worker_id)
    if instance:
        return {
            "allocated": True,
            "instance_digit": instance.digit,
            "ml_port": instance.ml_port,
            "db_port": instance.db_port
        }
    else:
        return {"allocated": False, "message": "No available instances"}


@router.post("/release/{digit}")
async def release_instance(digit: int):
    """Release an instance back to the pool"""
    await instance_pool.release_instance(digit)
    return {"message": f"Instance {digit} released"}


@router.post("/health-check")
async def health_check_instances():
    """Health check all instances"""
    await instance_pool.health_check_all()
    status = await instance_pool.get_status()
    return {"message": "Health check completed", "status": status}


@router.post("/shutdown")
async def shutdown_pool():
    """Shutdown all instances"""
    await instance_pool.shutdown()
    return {"message": "Instance pool shutdown complete"}