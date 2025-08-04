"""
Environment Management API
=========================

Handles ML server environment detection, management, and health monitoring.
"""

import os
import asyncio
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
from typing import List, Optional, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel


# Pydantic models
class Environment(BaseModel):
    """ML Server environment representation"""
    id: int
    name: str
    port: int
    status: str
    url: str
    health_status: Optional[str] = None
    last_check: Optional[datetime] = None
    version: Optional[str] = None
    test_count: Optional[int] = None


class EnvironmentHealth(BaseModel):
    """Environment health check response"""
    environment_id: int
    status: str
    response_time: Optional[float] = None
    error_message: Optional[str] = None
    services: Optional[Dict[str, str]] = None
    timestamp: datetime


class EnvironmentCreate(BaseModel):
    """Environment creation request"""
    name: Optional[str] = None
    port: Optional[int] = None
    auto_start: bool = False


class EnvironmentUpdate(BaseModel):
    """Environment update request"""
    name: Optional[str] = None
    status: Optional[str] = None


# Create router
router = APIRouter()

# In-memory storage (in production, use database)
environments_cache = {}
last_scan_time = None


async def detect_running_ml_servers() -> List[Environment]:
    """Detect running ML servers on the system"""
    environments = []
    
    # Check standard ports (6001-6010)
    for i in range(1, 11):
        port = 6000 + i
        env = Environment(
            id=i,
            name=f"ML Server {i}",
            port=port,
            url=f"http://localhost:{port}",
            status="unknown"
        )
        
        # Check if port is open
        try:
            # Quick port check
            proc = await asyncio.create_subprocess_exec(
                "lsof", "-i", f":{port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode == 0 and stdout:
                env.status = "running"
                
                # Try to get health info
                if HTTPX_AVAILABLE:
                    try:
                        async with httpx.AsyncClient(timeout=2.0) as client:
                            response = await client.get(f"{env.url}/health")
                            if response.status_code == 200:
                                env.health_status = "healthy"
                                env.last_check = datetime.now()
                            else:
                                env.health_status = "unhealthy"
                    except:
                        env.health_status = "unreachable"
                else:
                    env.health_status = "unknown"
            else:
                env.status = "stopped"
                
        except Exception:
            env.status = "unknown"
            
        environments.append(env)
    
    return environments


@router.get("/", response_model=List[Environment])
@router.get("", response_model=List[Environment])
async def list_environments():
    """List all ML server environments"""
    global environments_cache, last_scan_time
    
    # Refresh cache every 30 seconds
    now = datetime.now()
    if not last_scan_time or (now - last_scan_time).seconds > 30:
        environments = await detect_running_ml_servers()
        environments_cache = {env.id: env for env in environments}
        last_scan_time = now
    
    return list(environments_cache.values())


@router.get("/current")
async def get_current_environment():
    """Get the currently active ML server environment"""
    # Try to detect from environment variables
    ml_digit = os.getenv("ML_DIGIT")
    ml_port = os.getenv("ML_SERVER_PORT")
    
    if ml_digit:
        env_id = int(ml_digit)
    elif ml_port:
        env_id = int(ml_port) - 6000
    else:
        # Default to environment 1
        env_id = 1
    
    # Get environment info
    environments = await list_environments()
    current_env = next((env for env in environments if env.id == env_id), None)
    
    if not current_env:
        # Create default environment if not found
        current_env = Environment(
            id=env_id,
            name=f"ML Server {env_id}",
            port=6000 + env_id,
            url=f"http://localhost:{6000 + env_id}",
            status="unknown"
        )
    
    return {
        "current": current_env,
        "detected_from": "ML_DIGIT" if ml_digit else "ML_SERVER_PORT" if ml_port else "default"
    }


@router.get("/{environment_id}", response_model=Environment)
async def get_environment(environment_id: int):
    """Get specific environment details"""
    if environment_id < 1 or environment_id > 10:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    environments = await list_environments()
    env = next((e for e in environments if e.id == environment_id), None)
    
    if not env:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    return env


@router.get("/{environment_id}/health", response_model=EnvironmentHealth)
async def check_environment_health(environment_id: int):
    """Check health of specific environment"""
    if environment_id < 1 or environment_id > 10:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    port = 6000 + environment_id
    url = f"http://localhost:{port}"
    
    health = EnvironmentHealth(
        environment_id=environment_id,
        status="unknown",
        timestamp=datetime.now()
    )
    
    if not HTTPX_AVAILABLE:
        health.status = "unavailable"
        health.error_message = "httpx not available"
        return health
    
    try:
        start_time = datetime.now()
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/health")
            response_time = (datetime.now() - start_time).total_seconds()
            
            health.response_time = response_time
            
            if response.status_code == 200:
                health.status = "healthy"
                try:
                    data = response.json()
                    health.services = data.get("services", {})
                except:
                    pass
            else:
                health.status = "unhealthy"
                health.error_message = f"HTTP {response.status_code}"
                
    except Exception as e:
        if "ConnectError" in str(type(e)):
            health.status = "offline"
            health.error_message = "Connection refused"
        elif "TimeoutException" in str(type(e)):
            health.status = "timeout"
            health.error_message = "Request timeout"
        else:
            health.status = "error"
            health.error_message = str(e)
    
    return health


@router.post("/{environment_id}/start")
async def start_environment(environment_id: int, background_tasks: BackgroundTasks):
    """Start ML server environment"""
    if environment_id < 1 or environment_id > 10:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    port = 6000 + environment_id
    
    # Check if already running
    if HTTPX_AVAILABLE:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                response = await client.get(f"http://localhost:{port}/health")
                if response.status_code == 200:
                    return {
                        "message": f"Environment {environment_id} is already running",
                        "port": port,
                        "status": "already_running"
                    }
        except:
            pass
    
    # Start the server in background
    def start_ml_server():
        """Start ML server process"""
        try:
            import subprocess
            env = os.environ.copy()
            env["ML_DIGIT"] = str(environment_id)
            env["ENVIRONMENT"] = "test"
            
            # Launch the ML server
            process = subprocess.Popen([
                "./run_HUMANSA_test_environment_v2_enhanced.sh"
            ], env=env, cwd="/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1")
            
            return process.pid
        except Exception as e:
            print(f"Failed to start ML server {environment_id}: {e}")
            return None
    
    background_tasks.add_task(start_ml_server)
    
    return {
        "message": f"Starting ML server environment {environment_id}",
        "port": port,
        "status": "starting",
        "estimated_startup_time": "30-60 seconds"
    }


@router.post("/{environment_id}/stop")
async def stop_environment(environment_id: int):
    """Stop ML server environment"""
    if environment_id < 1 or environment_id > 10:
        raise HTTPException(status_code=404, detail="Environment not found")
    
    port = 6000 + environment_id
    
    try:
        # Find and kill processes on this port
        proc = await asyncio.create_subprocess_exec(
            "lsof", "-ti", f":{port}",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await proc.communicate()
        
        if proc.returncode == 0 and stdout:
            pids = stdout.decode().strip().split('\n')
            for pid in pids:
                if pid:
                    try:
                        os.kill(int(pid), 15)  # SIGTERM
                    except ProcessLookupError:
                        pass
                        
            return {
                "message": f"Stopped environment {environment_id}",
                "port": port,
                "status": "stopped",
                "processes_killed": len(pids)
            }
        else:
            return {
                "message": f"Environment {environment_id} was not running",
                "port": port,
                "status": "already_stopped"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop environment: {str(e)}")


@router.post("/{environment_id}/restart")
async def restart_environment(environment_id: int, background_tasks: BackgroundTasks):
    """Restart ML server environment"""
    # Stop first
    await stop_environment(environment_id)
    
    # Wait a moment
    await asyncio.sleep(2)
    
    # Start again
    result = await start_environment(environment_id, background_tasks)
    result["status"] = "restarting"
    result["message"] = f"Restarting ML server environment {environment_id}"
    
    return result


@router.get("/scan/processes")
async def scan_ml_processes():
    """Scan system for running ML server processes"""
    processes = []
    
    if not PSUTIL_AVAILABLE:
        return {
            "error": "psutil not available - cannot scan processes",
            "processes": [],
            "ml_servers": [],
            "scan_time": datetime.now().isoformat()
        }
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'create_time']):
            try:
                cmdline = proc.info.get('cmdline', [])
                if cmdline and any('src.main' in arg or 'main.py' in arg for arg in cmdline):
                    # Look for port in cmdline
                    port = None
                    for i, arg in enumerate(cmdline):
                        if arg in ['--port', '-p'] and i + 1 < len(cmdline):
                            try:
                                port = int(cmdline[i + 1])
                                break
                            except ValueError:
                                pass
                    
                    processes.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "port": port,
                        "cmdline": ' '.join(cmdline),
                        "started": datetime.fromtimestamp(proc.info['create_time']).isoformat(),
                        "is_ml_server": port and 6000 <= port <= 6010
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
    except Exception as e:
        return {"error": str(e), "processes": []}
    
    return {
        "processes": processes,
        "ml_servers": [p for p in processes if p.get("is_ml_server")],
        "scan_time": datetime.now().isoformat()
    }


@router.get("/stats/overview")
async def get_environments_overview():
    """Get overview statistics for all environments"""
    environments = await list_environments()
    
    stats = {
        "total_environments": len(environments),
        "running": len([e for e in environments if e.status == "running"]),
        "stopped": len([e for e in environments if e.status == "stopped"]),
        "unknown": len([e for e in environments if e.status == "unknown"]),
        "healthy": len([e for e in environments if e.health_status == "healthy"]),
        "unhealthy": len([e for e in environments if e.health_status == "unhealthy"]),
        "unreachable": len([e for e in environments if e.health_status == "unreachable"]),
        "last_scan": last_scan_time.isoformat() if last_scan_time else None
    }
    
    return {
        "statistics": stats,
        "environments": environments
    }