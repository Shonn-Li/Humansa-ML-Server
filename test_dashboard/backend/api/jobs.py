"""
Job Management API
==================

Handles test job creation, scheduling, execution, and monitoring.
A job is a collection of tests that can be executed together.
"""

import uuid
import asyncio
import os
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from enum import Enum
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Enums
class JobStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued" 
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal" 
    HIGH = "high"
    URGENT = "urgent"


class ExecutionMode(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    MIXED = "mixed"


# Pydantic models
class TestReference(BaseModel):
    """Reference to a test to include in job"""
    test_id: str
    suite: Optional[str] = None
    priority_override: Optional[int] = None
    config_overrides: Optional[Dict[str, Any]] = None


class JobConfig(BaseModel):
    """Job execution configuration"""
    execution_mode: ExecutionMode = ExecutionMode.PARALLEL
    max_parallel_workers: int = Field(default=4, ge=1, le=20)
    timeout_per_test: int = Field(default=30, ge=5, le=300)
    retry_failed_tests: bool = True
    max_retries: int = Field(default=2, ge=0, le=5)
    continue_on_failure: bool = True
    environment_id: Optional[int] = None
    tags: List[str] = []


class JobCreate(BaseModel):
    """Job creation request"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    tests: List[TestReference] = Field(..., min_items=1)
    config: JobConfig = JobConfig()
    priority: JobPriority = JobPriority.NORMAL
    scheduled_at: Optional[datetime] = None
    recurring: Optional[str] = None  # Cron expression


class JobUpdate(BaseModel):
    """Job update request"""
    name: Optional[str] = None
    description: Optional[str] = None
    config: Optional[JobConfig] = None
    priority: Optional[JobPriority] = None
    scheduled_at: Optional[datetime] = None


class JobProgress(BaseModel):
    """Job execution progress"""
    total_tests: int
    completed_tests: int
    failed_tests: int
    skipped_tests: int
    success_rate: float
    estimated_completion: Optional[datetime] = None


class Job(BaseModel):
    """Job model"""
    id: str
    name: str
    description: Optional[str] = None
    status: JobStatus
    priority: JobPriority
    created_at: datetime
    updated_at: datetime
    created_by: str = "dashboard_user"
    tests: List[TestReference]
    config: JobConfig
    scheduled_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: Optional[JobProgress] = None
    run_id: Optional[str] = None  # Current/last run ID
    recurring: Optional[str] = None
    tags: List[str] = []
    # Execution tracking
    total_tests: Optional[int] = None
    completed_tests: Optional[int] = None
    failed_tests: Optional[int] = None


class JobExecution(BaseModel):
    """Job execution request"""
    environment_id: Optional[int] = None
    config_overrides: Optional[JobConfig] = None
    dry_run: bool = False


# Create router
router = APIRouter()

# Import database utilities
from test_dashboard.backend.core.database import execute_query, execute_update, is_database_available
import json

# In-memory storage (fallback when database not available)
jobs_storage: Dict[str, Job] = {}
job_runs: Dict[str, Dict] = {}  # job_id -> run data


def generate_job_id() -> str:
    """Generate unique job ID"""
    return str(uuid.uuid4())


async def calculate_progress(job: Job) -> JobProgress:
    """Calculate job execution progress"""
    if not job.run_id:
        return JobProgress(
            total_tests=len(job.tests),
            completed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            success_rate=0.0
        )
    
    # Try database first
    if is_database_available():
        # Get run statistics from database
        query = """
            SELECT total_tests, passed_tests, failed_tests, skipped_tests, started_at
            FROM test_management.runs
            WHERE id = %(run_id)s
        """
        rows = await execute_query(query, {'run_id': job.run_id})
        
        if rows:
            run = rows[0]
            total = run['total_tests'] or len(job.tests)
            passed = run['passed_tests'] or 0
            failed = run['failed_tests'] or 0
            skipped = run['skipped_tests'] or 0
            completed = passed + failed + skipped
            success_rate = (passed / completed * 100) if completed > 0 else 0.0
            
            # Estimate completion time
            estimated_completion = None
            if completed > 0 and run['started_at']:
                elapsed = datetime.now() - run['started_at']
                avg_time_per_test = elapsed.total_seconds() / completed
                remaining_tests = total - completed
                estimated_seconds = remaining_tests * avg_time_per_test
                estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
            
            return JobProgress(
                total_tests=total,
                completed_tests=completed,
                failed_tests=failed,
                skipped_tests=skipped,
                success_rate=success_rate,
                estimated_completion=estimated_completion
            )
    
    # Fallback to in-memory
    if job.run_id not in job_runs:
        return JobProgress(
            total_tests=len(job.tests),
            completed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            success_rate=0.0
        )
    
    run_data = job_runs[job.run_id]
    results = run_data.get("results", {})
    
    total = len(job.tests)
    completed = len([r for r in results.values() if r.get("status") in ["completed", "failed"]])
    failed = len([r for r in results.values() if r.get("status") == "failed"])
    passed = completed - failed
    success_rate = (passed / completed * 100) if completed > 0 else 0.0
    
    # Estimate completion time
    estimated_completion = None
    if completed > 0 and job.started_at:
        elapsed = datetime.now() - job.started_at
        avg_time_per_test = elapsed.total_seconds() / completed
        remaining_tests = total - completed
        estimated_seconds = remaining_tests * avg_time_per_test
        estimated_completion = datetime.now() + timedelta(seconds=estimated_seconds)
    
    return JobProgress(
        total_tests=total,
        completed_tests=completed,
        failed_tests=failed,
        skipped_tests=0,  # Not implemented yet
        success_rate=success_rate,
        estimated_completion=estimated_completion
    )


@router.get("/", response_model=List[Job])
@router.get("", response_model=List[Job])
async def list_jobs(
    status: Optional[JobStatus] = None,
    priority: Optional[JobPriority] = None,
    limit: int = 50,
    offset: int = 0
):
    """List jobs with optional filtering"""
    if is_database_available():
        # Build query
        query = "SELECT * FROM test_management.jobs WHERE 1=1"
        params = {}
        
        if status:
            # Get jobs with matching status from runs table
            query = """
                SELECT DISTINCT j.*
                FROM test_management.jobs j
                LEFT JOIN test_management.runs r ON j.id = r.job_id
                WHERE r.status = %(status)s OR (r.id IS NULL AND %(status)s = 'created')
            """
            params['status'] = status.value
            
        if priority:
            if status:
                query += " AND j.config->>'priority' = %(priority)s"
            else:
                query += " AND config->>'priority' = %(priority)s"
            params['priority'] = priority.value
            
        query += " ORDER BY created_at DESC LIMIT %(limit)s OFFSET %(offset)s"
        params['limit'] = limit
        params['offset'] = offset
        
        # Execute query
        rows = await execute_query(query, params)
        jobs = []
        
        for row in rows:
            # Get latest run status
            run_query = """
                SELECT status, id as run_id, started_at, completed_at,
                       total_tests, passed_tests, failed_tests
                FROM test_management.runs 
                WHERE job_id = %(job_id)s 
                ORDER BY started_at DESC 
                LIMIT 1
            """
            run_rows = await execute_query(run_query, {'job_id': str(row['id'])})
            
            status_val = JobStatus.CREATED
            run_id = None
            started_at = None
            completed_at = None
            total_tests = None
            completed_tests = None
            failed_tests = None
            
            if run_rows:
                run = run_rows[0]
                status_val = JobStatus(run['status'])
                run_id = str(run['run_id'])
                started_at = run['started_at']
                completed_at = run['completed_at']
                total_tests = run['total_tests']
                completed_tests = run['passed_tests'] + run['failed_tests'] if run['passed_tests'] and run['failed_tests'] else None
                failed_tests = run['failed_tests']
            
            # Convert test_items to TestReference objects
            test_refs = []
            test_items = row['test_items']
            # Handle case where test_items might be a JSON string
            if isinstance(test_items, str):
                import json
                test_items = json.loads(test_items)
            
            for item in test_items:
                test_refs.append(TestReference(
                    test_id=item['test_id'],
                    suite=item.get('suite'),
                    priority_override=item.get('priority_override'),
                    config_overrides=item.get('config_overrides')
                ))
            
            # Convert config
            config_dict = row['config'] or {}
            # Handle case where config might be a JSON string
            if isinstance(config_dict, str):
                import json
                config_dict = json.loads(config_dict)
            config = JobConfig(**config_dict)
            
            job = Job(
                id=str(row['id']),
                name=row['name'],
                description=row['description'],
                status=status_val,
                priority=JobPriority(config_dict.get('priority', 'normal')),
                created_at=row['created_at'],
                updated_at=row['updated_at'],
                created_by=row['created_by'],
                tests=test_refs,
                config=config,
                scheduled_at=None,  # TODO: Add to schema
                started_at=started_at,
                completed_at=completed_at,
                run_id=run_id,
                recurring=None,  # TODO: Add to schema
                tags=config.tags,
                total_tests=total_tests,
                completed_tests=completed_tests,
                failed_tests=failed_tests
            )
            
            # Update progress for running jobs
            if job.status == JobStatus.RUNNING:
                job.progress = await calculate_progress(job)
                
            jobs.append(job)
            
        return jobs
    else:
        # Fallback to in-memory
        jobs = list(jobs_storage.values())
        
        # Apply filters
        if status:
            jobs = [j for j in jobs if j.status == status]
        if priority:
            jobs = [j for j in jobs if j.priority == priority]
        
        # Sort by creation time (newest first)
        jobs.sort(key=lambda x: x.created_at, reverse=True)
        
        # Update progress for running jobs
        for job in jobs:
            if job.status == JobStatus.RUNNING:
                job.progress = await calculate_progress(job)
        
        # Apply pagination
        return jobs[offset:offset + limit]


@router.post("/", response_model=Job)
@router.post("", response_model=Job)
async def create_job(job_create: JobCreate):
    """Create a new test job"""
    job_id = generate_job_id()
    now = datetime.now()
    
    if is_database_available():
        # Convert tests to JSON format
        test_items = []
        for test in job_create.tests:
            test_items.append({
                'test_id': test.test_id,
                'suite': test.suite,
                'priority_override': test.priority_override,
                'config_overrides': test.config_overrides
            })
        
        # Merge priority into config
        config_dict = job_create.config.dict()
        config_dict['priority'] = job_create.priority.value
        
        # Insert into database
        query = """
            INSERT INTO test_management.jobs 
            (id, name, description, test_items, config, created_by, created_at, updated_at)
            VALUES (%(id)s, %(name)s, %(description)s, %(test_items)s, %(config)s, %(created_by)s, %(created_at)s, %(updated_at)s)
            RETURNING id
        """
        
        params = {
            'id': job_id,
            'name': job_create.name,
            'description': job_create.description,
            'test_items': json.dumps(test_items),
            'config': json.dumps(config_dict),
            'created_by': 'dashboard_user',
            'created_at': now,
            'updated_at': now
        }
        
        await execute_update(query, params)
    
    job = Job(
        id=job_id,
        name=job_create.name,
        description=job_create.description,
        status=JobStatus.CREATED,
        priority=job_create.priority,
        created_at=now,
        updated_at=now,
        tests=job_create.tests,
        config=job_create.config,
        scheduled_at=job_create.scheduled_at,
        recurring=job_create.recurring,
        tags=job_create.config.tags
    )
    
    # Also store in memory for fallback
    jobs_storage[job_id] = job
    
    return job


@router.get("/{job_id}", response_model=Job)
async def get_job(job_id: str):
    """Get specific job details"""
    if is_database_available():
        # Query database
        query = "SELECT * FROM test_management.jobs WHERE id = %(id)s"
        rows = await execute_query(query, {'id': job_id})
        
        if not rows:
            raise HTTPException(status_code=404, detail="Job not found")
            
        row = rows[0]
        
        # Get latest run status
        run_query = """
            SELECT status, id as run_id, started_at, completed_at,
                   total_tests, passed_tests, failed_tests
            FROM test_management.runs 
            WHERE job_id = %(job_id)s 
            ORDER BY started_at DESC 
            LIMIT 1
        """
        run_rows = await execute_query(run_query, {'job_id': job_id})
        
        status_val = JobStatus.CREATED
        run_id = None
        started_at = None
        completed_at = None
        total_tests = None
        completed_tests = None
        failed_tests = None
        
        if run_rows:
            run = run_rows[0]
            status_val = JobStatus(run['status'])
            run_id = str(run['run_id'])
            started_at = run['started_at']
            completed_at = run['completed_at']
            total_tests = run['total_tests']
            completed_tests = run['passed_tests'] + run['failed_tests'] if run['passed_tests'] and run['failed_tests'] else None
            failed_tests = run['failed_tests']
        
        # Convert test_items to TestReference objects
        test_refs = []
        test_items = row['test_items']
        # Handle case where test_items might be a JSON string
        if isinstance(test_items, str):
            import json
            test_items = json.loads(test_items)
        
        for item in test_items:
            test_refs.append(TestReference(
                test_id=item['test_id'],
                suite=item.get('suite'),
                priority_override=item.get('priority_override'),
                config_overrides=item.get('config_overrides')
            ))
        
        # Convert config
        config_dict = row['config'] or {}
        # Handle case where config might be a JSON string
        if isinstance(config_dict, str):
            import json
            config_dict = json.loads(config_dict)
        config = JobConfig(**config_dict)
        
        job = Job(
            id=str(row['id']),
            name=row['name'],
            description=row['description'],
            status=status_val,
            priority=JobPriority(config_dict.get('priority', 'normal')),
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            created_by=row['created_by'],
            tests=test_refs,
            config=config,
            scheduled_at=None,
            started_at=started_at,
            completed_at=completed_at,
            run_id=run_id,
            recurring=None,
            tags=config.tags,
            total_tests=total_tests,
            completed_tests=completed_tests,
            failed_tests=failed_tests
        )
        
        # Update progress if running
        if job.status == JobStatus.RUNNING:
            job.progress = await calculate_progress(job)
            
        return job
    else:
        # Fallback to in-memory
        if job_id not in jobs_storage:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job = jobs_storage[job_id]
        
        # Update progress if running
        if job.status == JobStatus.RUNNING:
            job.progress = await calculate_progress(job)
            jobs_storage[job_id] = job
        
        return job


@router.put("/{job_id}", response_model=Job)
async def update_job(job_id: str, job_update: JobUpdate):
    """Update job details"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    # Can't update running jobs
    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Cannot update running job")
    
    # Apply updates
    if job_update.name is not None:
        job.name = job_update.name
    if job_update.description is not None:
        job.description = job_update.description
    if job_update.config is not None:
        job.config = job_update.config
    if job_update.priority is not None:
        job.priority = job_update.priority
    if job_update.scheduled_at is not None:
        job.scheduled_at = job_update.scheduled_at
    
    job.updated_at = datetime.now()
    jobs_storage[job_id] = job
    
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: str):
    """Delete a job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    # Can't delete running jobs
    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Cannot delete running job. Stop it first.")
    
    del jobs_storage[job_id]
    
    # Clean up run data
    if job.run_id and job.run_id in job_runs:
        del job_runs[job.run_id]
    
    return {"message": f"Job {job_id} deleted successfully"}


@router.post("/{job_id}/execute", response_model=Dict[str, Any])
async def execute_job(job_id: str, execution: JobExecution, background_tasks: BackgroundTasks):
    """Execute a job"""
    # Get job from database or memory
    job = await get_job(job_id)
    
    # Check if already running
    if job.status == JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Job is already running")
    
    # Generate run ID
    run_id = str(uuid.uuid4())
    
    # Apply config overrides
    config = job.config
    if execution.config_overrides:
        config = execution.config_overrides
    
    if is_database_available():
        # Get environment ID
        env_id = None
        if execution.environment_id or config.environment_id:
            env_query = "SELECT id FROM test_management.environments WHERE digit = %(digit)s"
            env_rows = await execute_query(env_query, {'digit': execution.environment_id or config.environment_id or 1})
            if env_rows:
                env_id = str(env_rows[0]['id'])
        
        # Create run in database
        run_query = """
            INSERT INTO test_management.runs 
            (id, job_id, environment_id, status, started_at, execution_config)
            VALUES (%(id)s, %(job_id)s, %(env_id)s, %(status)s, %(started_at)s, %(config)s)
        """
        
        await execute_update(run_query, {
            'id': run_id,
            'job_id': job_id,
            'env_id': env_id,
            'status': 'running' if not execution.dry_run else 'pending',
            'started_at': datetime.now(),
            'config': json.dumps(config.dict())
        })
    
    # Update job status in memory
    job.status = JobStatus.RUNNING if not execution.dry_run else JobStatus.CREATED
    job.run_id = run_id
    job.started_at = datetime.now()
    job.updated_at = datetime.now()
    
    # Initialize run data in memory
    job_runs[run_id] = {
        "job_id": job_id,
        "run_id": run_id,
        "started_at": job.started_at,
        "status": "running",
        "environment_id": execution.environment_id or config.environment_id or 1,
        "config": config.dict(),
        "results": {},
        "dry_run": execution.dry_run
    }
    
    jobs_storage[job_id] = job
    
    if not execution.dry_run:
        # Start execution in background
        background_tasks.add_task(execute_job_background, job_id, run_id, config)
    
    return {
        "message": f"Job {job_id} {'dry-run started' if execution.dry_run else 'execution started'}",
        "job_id": job_id,
        "run_id": run_id,
        "estimated_duration": f"{len(job.tests) * config.timeout_per_test} seconds",
        "dry_run": execution.dry_run
    }


@router.post("/{job_id}/stop")
async def stop_job(job_id: str):
    """Stop a running job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    if job.status != JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Job is not running")
    
    # Update job status
    job.status = JobStatus.CANCELLED
    job.completed_at = datetime.now()
    job.updated_at = datetime.now()
    
    # Update run data
    if job.run_id and job.run_id in job_runs:
        job_runs[job.run_id]["status"] = "cancelled"
        job_runs[job.run_id]["completed_at"] = datetime.now()
    
    jobs_storage[job_id] = job
    
    return {
        "message": f"Job {job_id} stopped successfully",
        "job_id": job_id,
        "run_id": job.run_id
    }


@router.post("/{job_id}/pause")
async def pause_job(job_id: str):
    """Pause a running job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    if job.status != JobStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Job is not running")
    
    job.status = JobStatus.PAUSED
    job.updated_at = datetime.now()
    jobs_storage[job_id] = job
    
    return {"message": f"Job {job_id} paused"}


@router.post("/{job_id}/resume")
async def resume_job(job_id: str, background_tasks: BackgroundTasks):
    """Resume a paused job"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    if job.status != JobStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Job is not paused")
    
    job.status = JobStatus.RUNNING
    job.updated_at = datetime.now()
    jobs_storage[job_id] = job
    
    # Resume execution
    background_tasks.add_task(execute_job_background, job_id, job.run_id, job.config)
    
    return {"message": f"Job {job_id} resumed"}


@router.get("/{job_id}/progress", response_model=JobProgress)
async def get_job_progress(job_id: str):
    """Get job execution progress"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    return await calculate_progress(job)


@router.get("/{job_id}/runs/{run_id}")
async def get_job_run_details(job_id: str, run_id: str):
    """Get job run details including test results"""
    # Try database first
    if is_database_available():
        # Get run details
        run_query = """
            SELECT r.*, j.name as job_name
            FROM test_management.runs r
            JOIN test_management.jobs j ON r.job_id = j.id
            WHERE r.id = %(run_id)s AND r.job_id = %(job_id)s
        """
        run_rows = await execute_query(run_query, {'run_id': run_id, 'job_id': job_id})
        
        if not run_rows:
            raise HTTPException(status_code=404, detail="Run not found")
        
        run = run_rows[0]
        
        # Get test results
        results_query = """
            SELECT test_id, suite_name, test_name, status, 
                   started_at, completed_at, execution_time,
                   error_message
            FROM test_management.results
            WHERE run_id = %(run_id)s
            ORDER BY started_at
        """
        result_rows = await execute_query(results_query, {'run_id': run_id})
        
        # Build response
        results = {}
        for result in result_rows:
            results[result['test_id']] = {
                "test_id": result['test_id'],
                "suite": result['suite_name'],
                "name": result['test_name'],
                "status": "completed" if result['status'] == 'passed' else "failed",
                "started_at": result['started_at'].isoformat() if result['started_at'] else None,
                "completed_at": result['completed_at'].isoformat() if result['completed_at'] else None,
                "duration": result['execution_time'],
                "success": result['status'] == 'passed',
                "error": result['error_message']
            }
        
        return {
            "job_id": str(run['job_id']),
            "run_id": str(run['id']),
            "started_at": run['started_at'].isoformat() if run['started_at'] else None,
            "completed_at": run['completed_at'].isoformat() if run['completed_at'] else None,
            "status": run['status'],
            "environment_id": str(run['environment_id']) if run['environment_id'] else None,
            "config": run['execution_config'] if isinstance(run['execution_config'], dict) else {},
            "results": results,
            "dry_run": False
        }
    
    # Fallback to in-memory
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    if job.run_id != run_id:
        raise HTTPException(status_code=404, detail="Run ID does not match job")
    
    if run_id not in job_runs:
        raise HTTPException(status_code=404, detail="Run data not found")
    
    return job_runs[run_id]


@router.get("/{job_id}/logs")
async def get_job_logs(job_id: str, limit: int = 100):
    """Get job execution logs"""
    if job_id not in jobs_storage:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_storage[job_id]
    
    if not job.run_id or job.run_id not in job_runs:
        return {"logs": [], "total": 0}
    
    run_data = job_runs[job.run_id]
    logs = run_data.get("logs", [])
    
    return {
        "logs": logs[-limit:] if limit else logs,
        "total": len(logs),
        "run_id": job.run_id
    }


@router.post("/templates/{template_name}")
async def create_job_from_template(template_name: str, overrides: Optional[Dict[str, Any]] = None):
    """Create job from template"""
    # Predefined templates
    templates = {
        "smoke_test": {
            "name": "Smoke Test Suite",
            "description": "Basic functionality tests",
            "tests": [
                {"test_id": "APT_001", "suite": "appointment"},
                {"test_id": "MED_001", "suite": "medical"},
                {"test_id": "PROD_001", "suite": "product"}
            ],
            "config": {"execution_mode": "parallel", "max_parallel_workers": 2}
        },
        "regression_test": {
            "name": "Regression Test Suite", 
            "description": "Full regression testing",
            "tests": [
                {"test_id": "APT_001", "suite": "appointment"},
                {"test_id": "APT_002", "suite": "appointment"},
                {"test_id": "MED_001", "suite": "medical"},
                {"test_id": "MULTI_001", "suite": "multi_turn"}
            ],
            "config": {"execution_mode": "mixed", "max_parallel_workers": 4}
        },
        "performance_test": {
            "name": "Performance Test Suite",
            "description": "Performance and load testing",
            "tests": [
                {"test_id": "PERF_001", "suite": "performance"},
                {"test_id": "PERF_002", "suite": "performance"}
            ],
            "config": {"execution_mode": "sequential", "timeout_per_test": 60}
        }
    }
    
    if template_name not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    template = templates[template_name].copy()
    
    # Apply overrides
    if overrides:
        template.update(overrides)
    
    # Create job
    job_create = JobCreate(**template)
    return await create_job(job_create)


async def execute_job_background(job_id: str, run_id: str, config: JobConfig):
    """Background job execution with real test runner"""
    import httpx
    import subprocess
    from test_dashboard.backend.core.config import settings
    
    try:
        job = jobs_storage[job_id]
        run_data = job_runs[run_id]
        
        # Check if ML server is running
        ml_port = settings.ML_SERVER_PORT or 6001
        ml_url = f"http://localhost:{ml_port}"
        
        # Try to check ML server health
        server_running = False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{ml_url}/health")
                if resp.status_code == 200:
                    server_running = True
                    logger.info(f"ML server already running on port {ml_port}")
        except:
            logger.info(f"ML server not running on port {ml_port}")
        
        # Start ML server if not running
        if not server_running:
            logger.info("Starting ML test server...")
            try:
                # Use the test environment script
                env = os.environ.copy()
                env["ML_DIGIT"] = str(settings.ML_SERVER_DIGIT or 1)
                env["ENVIRONMENT"] = "test"
                env["ML_SERVER_PORT"] = str(ml_port)
                
                # Start the server
                process = subprocess.Popen([
                    "python3", "-m", "src.main", "--port", str(ml_port)
                ], env=env, cwd="/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1")
                
                # Wait for server to start (with timeout)
                start_time = datetime.now()
                timeout = 60  # seconds
                while (datetime.now() - start_time).seconds < timeout:
                    await asyncio.sleep(2)
                    try:
                        async with httpx.AsyncClient(timeout=5.0) as client:
                            resp = await client.get(f"{ml_url}/health")
                            if resp.status_code == 200:
                                server_running = True
                                logger.info("ML server started successfully")
                                break
                    except:
                        continue
                
                if not server_running:
                    raise Exception("Failed to start ML server within timeout")
            except Exception as e:
                logger.error(f"Failed to start ML server: {e}")
                # Update job status
                job.status = JobStatus.FAILED
                job.completed_at = datetime.now()
                jobs_storage[job_id] = job
                run_data["status"] = "failed"
                run_data["error"] = f"Failed to start ML server: {e}"
                run_data["completed_at"] = datetime.now()
                return
        
        total_tests = len(job.tests)
        
        # Get test definitions
        from test_dashboard.backend.api.tests import get_test_by_id
        
        for i, test_ref in enumerate(job.tests):
            # Check if job was cancelled/paused
            if job.status in [JobStatus.CANCELLED, JobStatus.PAUSED]:
                break
            
            # Update test as running
            run_data["results"][test_ref.test_id] = {
                "test_id": test_ref.test_id,
                "status": "running", 
                "started_at": datetime.now().isoformat(),
                "completed_at": None,
                "duration": None,
                "success": None,
                "error": None
            }
            
            # Update job progress
            job.completed_tests = i
            job.updated_at = datetime.now()
            jobs_storage[job_id] = job
            
            # Get test definition
            test_def = None
            if is_database_available():
                from test_dashboard.backend.core.database import execute_query
                query = "SELECT * FROM test_management.test_definitions WHERE id = %(id)s"
                rows = await execute_query(query, {'id': test_ref.test_id})
                if rows:
                    test_def = rows[0]
            
            if not test_def:
                # Try to get from memory or load from file
                from test_dashboard.backend.api.tests import tests_storage
                test_def = tests_storage.get(test_ref.test_id)
            
            if not test_def:
                logger.error(f"Test definition not found: {test_ref.test_id}")
                success = False
                error_msg = f"Test definition not found: {test_ref.test_id}"
            else:
                # Execute real test
                try:
                    # Prepare test request
                    test_config = test_def.get('config', {}) if isinstance(test_def, dict) else test_def.config
                    test_request = {
                        "messages": test_config.get('messages', []),
                        "model": test_config.get('model', 'gpt-4o'),
                        "stream": False,
                        "user_id": f"test_user_{run_id}",
                        "metadata": {
                            "test_id": test_ref.test_id,
                            "run_id": run_id,
                            "job_id": job_id
                        }
                    }
                    
                    # Add any config overrides
                    if test_ref.config_overrides:
                        test_request.update(test_ref.config_overrides)
                    
                    # Call the appropriate endpoint based on test type
                    test_type = test_def.get('type', 'single') if isinstance(test_def, dict) else test_def.type
                    endpoint = "/v1-humansa/chat/completions" if test_type == "single" else "/v2/humansa/responses/create"
                    
                    async with httpx.AsyncClient(timeout=config.timeout_per_test or 60.0) as client:
                        start_time = datetime.now()
                        response = await client.post(f"{ml_url}{endpoint}", json=test_request)
                        end_time = datetime.now()
                        duration = (end_time - start_time).total_seconds()
                        
                        if response.status_code == 200:
                            result_data = response.json()
                            
                            # Validate response based on test expectations
                            expectations = test_config.get('expected', {})
                            success = True
                            error_msg = None
                            
                            # Basic validation
                            if expectations:
                                # Check for required fields
                                if 'contains' in expectations:
                                    response_text = str(result_data)
                                    for term in expectations['contains']:
                                        if term.lower() not in response_text.lower():
                                            success = False
                                            error_msg = f"Response missing expected content: {term}"
                                            break
                                
                                # Check response format
                                if 'format' in expectations and success:
                                    # Add format validation logic here
                                    pass
                            
                            # Store actual response for logs
                            run_data["results"][test_ref.test_id]["response"] = result_data
                        else:
                            success = False
                            error_msg = f"API returned status {response.status_code}: {response.text}"
                            duration = (datetime.now() - start_time).total_seconds()
                    
                except asyncio.TimeoutError:
                    success = False
                    error_msg = "Test execution timeout"
                    duration = config.timeout_per_test or 60.0
                except Exception as e:
                    success = False
                    error_msg = f"Test execution error: {str(e)}"
                    duration = (datetime.now() - datetime.fromisoformat(run_data["results"][test_ref.test_id]["started_at"])).total_seconds()
            
            test_status = "passed" if success else "failed"
            started_at = datetime.fromisoformat(run_data["results"][test_ref.test_id]["started_at"])
            completed_at = datetime.now()
            duration = (completed_at - started_at).total_seconds()
            
            run_data["results"][test_ref.test_id] = {
                "test_id": test_ref.test_id,
                "status": "completed" if success else "failed", 
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
                "duration": duration,
                "success": success,
                "error": None if success else "Mock test failure"
            }
            
            # Update database if available
            if is_database_available():
                result_query = """
                    INSERT INTO test_management.results
                    (run_id, test_id, suite_name, test_name, status, started_at, completed_at, execution_time, error_message)
                    VALUES (%(run_id)s, %(test_id)s, %(suite)s, %(test_name)s, %(status)s, %(started_at)s, %(completed_at)s, %(duration)s, %(error)s)
                """
                
                await execute_update(result_query, {
                    'run_id': run_id,
                    'test_id': test_ref.test_id,
                    'suite': test_ref.suite or 'unknown',
                    'test_name': f"Test {test_ref.test_id}",
                    'status': test_status,
                    'started_at': started_at,
                    'completed_at': completed_at,
                    'duration': duration,
                    'error': None if success else "Mock test failure"
                })
            
            # Update failed count
            if not success:
                job.failed_tests = (job.failed_tests or 0) + 1
            
            # Add log entry
            if "logs" not in run_data:
                run_data["logs"] = []
            run_data["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Test {test_ref.test_id} {'completed' if success else 'failed'}"
            })
        
        # Complete job
        if job.status != JobStatus.CANCELLED:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.total_tests = total_tests
            job.completed_tests = len([r for r in run_data["results"].values() if r.get("status") in ["completed", "failed"]])
            run_data["status"] = "completed"
            run_data["completed_at"] = datetime.now()
            
            # Update run in database
            if is_database_available():
                # Count results
                passed = len([r for r in run_data["results"].values() if r.get("success") == True])
                failed = len([r for r in run_data["results"].values() if r.get("success") == False])
                
                update_query = """
                    UPDATE test_management.runs
                    SET status = %(status)s, completed_at = %(completed_at)s,
                        total_tests = %(total)s, passed_tests = %(passed)s, failed_tests = %(failed)s
                    WHERE id = %(run_id)s
                """
                
                await execute_update(update_query, {
                    'status': 'completed',
                    'completed_at': job.completed_at,
                    'total': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'run_id': run_id
                })
            
        jobs_storage[job_id] = job
        
    except Exception as e:
        # Handle execution errors
        job.status = JobStatus.FAILED
        job.completed_at = datetime.now()
        job.updated_at = datetime.now()
        jobs_storage[job_id] = job
        
        run_data["status"] = "failed"
        run_data["error"] = str(e)
        run_data["completed_at"] = datetime.now()
        
        # Update run in database
        if is_database_available():
            update_query = """
                UPDATE test_management.runs
                SET status = %(status)s, completed_at = %(completed_at)s, error_message = %(error)s
                WHERE id = %(run_id)s
            """
            
            await execute_update(update_query, {
                'status': 'failed',
                'completed_at': job.completed_at,
                'error': str(e),
                'run_id': run_id
            })


@router.get("/stats/overview")
async def get_jobs_overview():
    """Get jobs overview statistics"""
    jobs = list(jobs_storage.values())
    
    stats = {
        "total_jobs": len(jobs),
        "by_status": {
            "created": len([j for j in jobs if j.status == JobStatus.CREATED]),
            "running": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "completed": len([j for j in jobs if j.status == JobStatus.COMPLETED]),
            "failed": len([j for j in jobs if j.status == JobStatus.FAILED]),
            "cancelled": len([j for j in jobs if j.status == JobStatus.CANCELLED])
        },
        "by_priority": {
            "low": len([j for j in jobs if j.priority == JobPriority.LOW]),
            "normal": len([j for j in jobs if j.priority == JobPriority.NORMAL]),
            "high": len([j for j in jobs if j.priority == JobPriority.HIGH]),
            "urgent": len([j for j in jobs if j.priority == JobPriority.URGENT])
        },
        "recent_activity": {
            "created_today": len([j for j in jobs if j.created_at.date() == datetime.now().date()]),
            "running_now": len([j for j in jobs if j.status == JobStatus.RUNNING]),
            "completed_today": len([j for j in jobs if j.completed_at and j.completed_at.date() == datetime.now().date()])
        }
    }
    
    return {"statistics": stats}