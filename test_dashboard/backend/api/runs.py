"""
Execution Management API
========================

Handles test run execution, monitoring, and real-time status updates.
A run represents a single execution instance of a job or individual test.
"""

import uuid
import asyncio
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from pydantic import BaseModel, Field
import json
import time


# Enums
class RunStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TestStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"
    TIMEOUT = "timeout"


# Pydantic models
class TestResult(BaseModel):
    """Individual test result within a run"""
    test_id: str
    test_name: str
    suite: str
    status: TestStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration: Optional[float] = None
    success: bool = False
    score: Optional[float] = None
    
    # Response data
    response_status_code: Optional[int] = None
    response_data: Optional[Dict[str, Any]] = None
    
    # Validation results
    response_validation: Optional[Dict[str, Any]] = None
    reasoning_validation: Optional[Dict[str, Any]] = None
    agent_validation: Optional[Dict[str, Any]] = None
    performance_validation: Optional[Dict[str, Any]] = None
    
    # Error information
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    
    # Logs
    logs: List[Dict[str, Any]] = []


class RunProgress(BaseModel):
    """Run execution progress"""
    total_tests: int
    completed_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    success_rate: float
    average_duration: Optional[float] = None
    estimated_completion: Optional[datetime] = None
    current_test: Optional[str] = None


class RunConfiguration(BaseModel):
    """Run execution configuration"""
    environment_id: int = 1
    max_parallel_workers: int = Field(default=8, ge=1, le=20)
    timeout_per_test: int = Field(default=30, ge=5, le=300)
    retry_failed_tests: bool = True
    max_retries: int = Field(default=2, ge=0, le=5)
    continue_on_failure: bool = True
    collect_logs: bool = True
    capture_response_data: bool = True


class RunCreate(BaseModel):
    """Run creation request"""
    name: Optional[str] = None
    job_id: Optional[str] = None
    test_ids: List[str] = []
    config: RunConfiguration = RunConfiguration()
    tags: List[str] = []


class TestRun(BaseModel):
    """Test run model"""
    id: str
    name: str
    job_id: Optional[str] = None
    status: RunStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: str = "dashboard_user"
    
    # Configuration
    config: RunConfiguration
    test_ids: List[str]
    tags: List[str] = []
    
    # Progress and results
    progress: Optional[RunProgress] = None
    results: Dict[str, TestResult] = {}
    
    # Execution info
    environment_url: Optional[str] = None
    worker_count: int = 0
    total_duration: Optional[float] = None
    
    # Metadata
    metadata: Dict[str, Any] = {}


class RunExecutionRequest(BaseModel):
    """Run execution request"""
    config_overrides: Optional[RunConfiguration] = None
    dry_run: bool = False


# Create router
router = APIRouter()

# In-memory storage (in production, use database)
runs_storage: Dict[str, TestRun] = {}
active_websockets: Dict[str, List[WebSocket]] = {}


def generate_run_id() -> str:
    """Generate unique run ID"""
    return f"run_{uuid.uuid4().hex[:8]}"


def calculate_progress(run: TestRun) -> RunProgress:
    """Calculate run execution progress"""
    results = list(run.results.values())
    total = len(run.test_ids)
    completed = len([r for r in results if r.status in [TestStatus.PASSED, TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]])
    passed = len([r for r in results if r.status == TestStatus.PASSED])
    failed = len([r for r in results if r.status in [TestStatus.FAILED, TestStatus.ERROR, TestStatus.TIMEOUT]])
    skipped = len([r for r in results if r.status == TestStatus.SKIPPED])
    
    success_rate = (passed / completed * 100) if completed > 0 else 0.0
    
    # Calculate average duration
    durations = [r.duration for r in results if r.duration is not None]
    average_duration = sum(durations) / len(durations) if durations else None
    
    # Estimate completion time
    estimated_completion = None
    if completed > 0 and run.started_at and average_duration:
        remaining_tests = total - completed
        estimated_seconds = remaining_tests * average_duration
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
    
    # Find current test
    current_test = None
    for result in results:
        if result.status == TestStatus.RUNNING:
            current_test = result.test_id
            break
    
    return RunProgress(
        total_tests=total,
        completed_tests=completed,
        passed_tests=passed,
        failed_tests=failed,
        skipped_tests=skipped,
        success_rate=success_rate,
        average_duration=average_duration,
        estimated_completion=estimated_completion,
        current_test=current_test
    )


async def broadcast_run_update(run_id: str, update_data: Dict[str, Any]):
    """Broadcast run update to all connected WebSocket clients"""
    if run_id in active_websockets:
        disconnected = []
        for websocket in active_websockets[run_id]:
            try:
                await websocket.send_json({
                    "type": "run_update",
                    "run_id": run_id,
                    "timestamp": datetime.now().isoformat(),
                    "data": update_data
                })
            except:
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for ws in disconnected:
            active_websockets[run_id].remove(ws)


async def execute_single_test(run_id: str, test_id: str, config: RunConfiguration) -> TestResult:
    """Execute a single test and return result"""
    run = runs_storage[run_id]
    
    # Create test result
    result = TestResult(
        test_id=test_id,
        test_name=f"Test {test_id}",
        suite="unknown",
        status=TestStatus.RUNNING,
        started_at=datetime.now()
    )
    
    # Update run results
    run.results[test_id] = result
    
    # Broadcast update
    await broadcast_run_update(run_id, {
        "test_started": test_id,
        "progress": calculate_progress(run).dict()
    })
    
    try:
        # Get environment URL
        environment_url = f"http://localhost:{6000 + config.environment_id}"
        
        # Mock test execution (in production, this would make actual API calls)
        start_time = time.time()
        
        # Simulate network call
        if HTTPX_AVAILABLE:
            async with httpx.AsyncClient(timeout=config.timeout_per_test) as client:
                try:
                    # Try to call the actual ML server health endpoint first
                    health_response = await client.get(f"{environment_url}/health")
                    if health_response.status_code == 200:
                        # Server is running, simulate a test call
                        # This is where you'd make the actual test API call
                        await asyncio.sleep(0.5)  # Simulate processing time
                        
                        result.response_status_code = 200
                        result.response_data = {"output": "Mock test response", "status": "success"}
                        result.success = True
                        result.status = TestStatus.PASSED
                        result.score = 0.85
                    else:
                        raise Exception("ML server not responding")
                        
                except Exception:
                    # Server not running, use mock data
                    await asyncio.sleep(0.2)  # Simulate quick mock execution
                    
                    # Mock success/failure (70% success rate)
                    success = hash(test_id) % 10 < 7
                    
                    result.response_status_code = 200 if success else 500
                    result.response_data = {
                        "output": f"Mock response for {test_id}",
                        "status": "success" if success else "error"
                    }
                    result.success = success
                    result.status = TestStatus.PASSED if success else TestStatus.FAILED
                    result.score = 0.75 if success else 0.25
                    
                    if not success:
                        result.error_message = "Mock test failure for demonstration"
                        result.error_type = "MockError"
        else:
            # No httpx available, use mock data
            await asyncio.sleep(0.2)  # Simulate quick mock execution
            
            # Mock success/failure (70% success rate)
            success = hash(test_id) % 10 < 7
            
            result.response_status_code = 200 if success else 500
            result.response_data = {
                "output": f"Mock response for {test_id}",
                "status": "success" if success else "error"
            }
            result.success = success
            result.status = TestStatus.PASSED if success else TestStatus.FAILED
            result.score = 0.75 if success else 0.25
            
            if not success:
                result.error_message = "Mock test failure for demonstration"
                result.error_type = "MockError"
        
        # Calculate duration
        result.duration = time.time() - start_time
        result.completed_at = datetime.now()
        
        # Add some mock logs
        result.logs = [
            {
                "timestamp": result.started_at.isoformat(),
                "level": "INFO",
                "message": f"Starting test {test_id}"
            },
            {
                "timestamp": result.completed_at.isoformat(),
                "level": "INFO" if result.success else "ERROR",
                "message": f"Test {test_id} {'passed' if result.success else 'failed'}"
            }
        ]
        
        # Mock validation results
        result.response_validation = {
            "status_code_match": result.response_status_code == 200,
            "output_contains_check": result.success,
            "length_check": True
        }
        
        result.performance_validation = {
            "response_time_ok": result.duration < config.timeout_per_test,
            "memory_usage_ok": True
        }
        
    except asyncio.TimeoutError:
        result.status = TestStatus.TIMEOUT
        result.error_message = "Test execution timeout"
        result.error_type = "TimeoutError"
        result.completed_at = datetime.now()
        result.duration = config.timeout_per_test
        
    except Exception as e:
        result.status = TestStatus.ERROR
        result.error_message = str(e)
        result.error_type = type(e).__name__
        result.completed_at = datetime.now()
        result.duration = time.time() - start_time if 'start_time' in locals() else 0
    
    # Update run results
    run.results[test_id] = result
    
    # Broadcast update
    await broadcast_run_update(run_id, {
        "test_completed": test_id,
        "result": result.dict(),
        "progress": calculate_progress(run).dict()
    })
    
    return result


@router.get("/", response_model=List[TestRun])
@router.get("", response_model=List[TestRun])
async def list_runs(
    status: Optional[RunStatus] = None,
    job_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """List test runs with optional filtering"""
    runs = list(runs_storage.values())
    
    # Apply filters
    if status:
        runs = [r for r in runs if r.status == status]
    if job_id:
        runs = [r for r in runs if r.job_id == job_id]
    
    # Sort by creation time (newest first)
    runs.sort(key=lambda x: x.created_at, reverse=True)
    
    # Update progress for running runs
    for run in runs:
        if run.status == RunStatus.RUNNING:
            run.progress = calculate_progress(run)
    
    # Apply pagination
    return runs[offset:offset + limit]


@router.post("/", response_model=TestRun)
async def create_run(run_create: RunCreate):
    """Create a new test run"""
    run_id = generate_run_id()
    now = datetime.now()
    
    # Generate name if not provided
    name = run_create.name or f"Test Run {now.strftime('%Y-%m-%d %H:%M:%S')}"
    
    run = TestRun(
        id=run_id,
        name=name,
        job_id=run_create.job_id,
        status=RunStatus.CREATED,
        created_at=now,
        config=run_create.config,
        test_ids=run_create.test_ids,
        tags=run_create.tags,
        environment_url=f"http://localhost:{6000 + run_create.config.environment_id}"
    )
    
    runs_storage[run_id] = run
    
    return run


@router.get("/{run_id}", response_model=TestRun)
async def get_run(run_id: str):
    """Get specific run details"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    # Update progress if running
    if run.status == RunStatus.RUNNING:
        run.progress = calculate_progress(run)
        runs_storage[run_id] = run
    
    return run


@router.post("/{run_id}/execute")
async def execute_run(run_id: str, execution: RunExecutionRequest, background_tasks: BackgroundTasks):
    """Execute a test run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    # Check if already running
    if run.status == RunStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Run is already executing")
    
    # Apply config overrides
    config = run.config
    if execution.config_overrides:
        config = execution.config_overrides
    
    # Update run status
    run.status = RunStatus.RUNNING if not execution.dry_run else RunStatus.CREATED
    run.started_at = datetime.now()
    run.worker_count = min(config.max_parallel_workers, len(run.test_ids))
    
    # Initialize results
    for test_id in run.test_ids:
        run.results[test_id] = TestResult(
            test_id=test_id,
            test_name=f"Test {test_id}",
            suite="unknown",
            status=TestStatus.PENDING
        )
    
    runs_storage[run_id] = run
    
    if not execution.dry_run:
        # Start execution in background
        background_tasks.add_task(execute_run_background, run_id, config)
    
    return {
        "message": f"Run {run_id} {'dry-run started' if execution.dry_run else 'execution started'}",
        "run_id": run_id,
        "test_count": len(run.test_ids),
        "worker_count": run.worker_count,
        "estimated_duration": f"{len(run.test_ids) * config.timeout_per_test / run.worker_count} seconds",
        "dry_run": execution.dry_run
    }


@router.post("/{run_id}/stop")
async def stop_run(run_id: str):
    """Stop a running test run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    if run.status != RunStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Run is not executing")
    
    # Update run status
    run.status = RunStatus.CANCELLED
    run.completed_at = datetime.now()
    
    # Calculate total duration
    if run.started_at:
        run.total_duration = (run.completed_at - run.started_at).total_seconds()
    
    # Update progress
    run.progress = calculate_progress(run)
    
    runs_storage[run_id] = run
    
    # Broadcast final update
    await broadcast_run_update(run_id, {
        "run_stopped": True,
        "status": run.status,
        "progress": run.progress.dict()
    })
    
    return {
        "message": f"Run {run_id} stopped successfully",
        "run_id": run_id,
        "final_status": run.status
    }


@router.post("/{run_id}/pause")
async def pause_run(run_id: str):
    """Pause a running test run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    if run.status != RunStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Run is not executing") 
    
    run.status = RunStatus.PAUSED
    runs_storage[run_id] = run
    
    await broadcast_run_update(run_id, {
        "run_paused": True,
        "status": run.status
    })
    
    return {"message": f"Run {run_id} paused"}


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, background_tasks: BackgroundTasks):
    """Resume a paused test run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    if run.status != RunStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Run is not paused")
    
    run.status = RunStatus.RUNNING
    runs_storage[run_id] = run
    
    # Resume execution
    background_tasks.add_task(execute_run_background, run_id, run.config)
    
    await broadcast_run_update(run_id, {
        "run_resumed": True,
        "status": run.status
    })
    
    return {"message": f"Run {run_id} resumed"}


@router.get("/{run_id}/progress", response_model=RunProgress)
async def get_run_progress(run_id: str):
    """Get run execution progress"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    return calculate_progress(run)


@router.get("/{run_id}/results")
async def get_run_results(run_id: str):
    """Get run test results"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    results = list(run.results.values())
    
    # Sort by completion time
    results.sort(key=lambda x: x.completed_at or datetime.min)
    
    return {
        "run_id": run_id,
        "status": run.status,
        "results": results,
        "summary": {
            "total": len(results),
            "passed": len([r for r in results if r.status == TestStatus.PASSED]),
            "failed": len([r for r in results if r.status == TestStatus.FAILED]),
            "error": len([r for r in results if r.status == TestStatus.ERROR]),
            "timeout": len([r for r in results if r.status == TestStatus.TIMEOUT]),
            "pending": len([r for r in results if r.status == TestStatus.PENDING])
        }
    }


@router.get("/{run_id}/results/{test_id}", response_model=TestResult)
async def get_test_result(run_id: str, test_id: str):
    """Get specific test result from run"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    
    if test_id not in run.results:
        raise HTTPException(status_code=404, detail="Test result not found")
    
    return run.results[test_id]


@router.get("/{run_id}/logs")
async def get_run_logs(run_id: str, test_id: Optional[str] = None, limit: int = 100):
    """Get run execution logs"""
    if run_id not in runs_storage:
        raise HTTPException(status_code=404, detail="Run not found")
    
    run = runs_storage[run_id]
    all_logs = []
    
    # Collect logs from all test results or specific test
    if test_id:
        if test_id in run.results:
            all_logs.extend(run.results[test_id].logs)
    else:
        for result in run.results.values():
            all_logs.extend(result.logs)
    
    # Sort by timestamp
    all_logs.sort(key=lambda x: x.get('timestamp', ''))
    
    return {
        "run_id": run_id,
        "test_id": test_id,
        "logs": all_logs[-limit:] if limit else all_logs,
        "total": len(all_logs)
    }


@router.websocket("/{run_id}/ws")
async def websocket_endpoint(websocket: WebSocket, run_id: str):
    """WebSocket endpoint for real-time run updates"""
    await websocket.accept()
    
    # Add to active connections
    if run_id not in active_websockets:
        active_websockets[run_id] = []
    active_websockets[run_id].append(websocket)
    
    try:
        # Send initial state
        if run_id in runs_storage:
            run = runs_storage[run_id]
            await websocket.send_json({
                "type": "initial_state",
                "run_id": run_id,
                "data": {
                    "status": run.status,
                    "progress": calculate_progress(run).dict() if run.status == RunStatus.RUNNING else None
                }
            })
        
        # Keep connection alive
        while True:
            try:
                data = await websocket.receive_text()
                # Handle any client messages if needed
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Remove from active connections
        if run_id in active_websockets:
            try:
                active_websockets[run_id].remove(websocket)
            except ValueError:
                pass
            if not active_websockets[run_id]:
                del active_websockets[run_id]


async def execute_run_background(run_id: str, config: RunConfiguration):
    """Background run execution with parallel workers"""
    if run_id not in runs_storage:
        return
    
    run = runs_storage[run_id]
    
    try:
        # Get pending tests (resume support)
        pending_tests = [tid for tid in run.test_ids if run.results[tid].status == TestStatus.PENDING]
        
        if not pending_tests:
            return
        
        # Execute tests with limited parallelism
        semaphore = asyncio.Semaphore(config.max_parallel_workers)
        
        async def execute_with_semaphore(test_id: str):
            async with semaphore:
                # Check if run was cancelled/paused
                current_run = runs_storage.get(run_id)
                if not current_run or current_run.status in [RunStatus.CANCELLED, RunStatus.PAUSED]:
                    return
                
                await execute_single_test(run_id, test_id, config)
        
        # Execute all tests
        await asyncio.gather(*[execute_with_semaphore(tid) for tid in pending_tests])
        
        # Complete run if not cancelled/paused
        current_run = runs_storage.get(run_id)
        if current_run and current_run.status == RunStatus.RUNNING:
            current_run.status = RunStatus.COMPLETED
            current_run.completed_at = datetime.now()
            
            if current_run.started_at:
                current_run.total_duration = (current_run.completed_at - current_run.started_at).total_seconds()
            
            current_run.progress = calculate_progress(current_run)
            runs_storage[run_id] = current_run
            
            # Broadcast completion
            await broadcast_run_update(run_id, {
                "run_completed": True,
                "status": current_run.status,
                "progress": current_run.progress.dict(),
                "total_duration": current_run.total_duration
            })
            
    except Exception as e:
        # Handle execution errors
        run = runs_storage.get(run_id)
        if run:
            run.status = RunStatus.FAILED
            run.completed_at = datetime.now()
            if run.started_at:
                run.total_duration = (run.completed_at - run.started_at).total_seconds()
            runs_storage[run_id] = run
            
            await broadcast_run_update(run_id, {
                "run_failed": True,
                "status": run.status,
                "error": str(e)
            })


@router.get("/stats/overview")
async def get_runs_overview():
    """Get runs overview statistics"""
    runs = list(runs_storage.values())
    
    stats = {
        "total_runs": len(runs),
        "by_status": {
            "created": len([r for r in runs if r.status == RunStatus.CREATED]),
            "running": len([r for r in runs if r.status == RunStatus.RUNNING]),
            "completed": len([r for r in runs if r.status == RunStatus.COMPLETED]),
            "failed": len([r for r in runs if r.status == RunStatus.FAILED]),
            "cancelled": len([r for r in runs if r.status == RunStatus.CANCELLED])
        },
        "recent_activity": {
            "created_today": len([r for r in runs if r.created_at.date() == datetime.now().date()]),
            "running_now": len([r for r in runs if r.status == RunStatus.RUNNING]),
            "completed_today": len([r for r in runs if r.completed_at and r.completed_at.date() == datetime.now().date()])
        },
        "performance": {
            "average_duration": sum([r.total_duration for r in runs if r.total_duration]) / len([r for r in runs if r.total_duration]) if any(r.total_duration for r in runs) else 0,
            "total_tests_executed": sum([len(r.results) for r in runs]),
            "overall_success_rate": sum([len([res for res in r.results.values() if res.success]) for r in runs]) / sum([len(r.results) for r in runs]) * 100 if any(r.results for r in runs) else 0
        }
    }
    
    return {"statistics": stats}