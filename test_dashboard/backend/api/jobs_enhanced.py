"""
Enhanced Job Execution with Server Log Capture
==============================================

This module provides enhanced job execution functionality with full ML server log capture
and proper response parsing for the test dashboard.

Multi-Instance Support:
- Each worker gets its own ML server instance with isolated database
- Instance allocation managed by InstancePool
- Separate log capture per instance
"""

import json
import os
import time
import asyncio
import subprocess
import tempfile
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel
import logging
from concurrent.futures import ThreadPoolExecutor
try:
    import psutil
except ImportError:
    psutil = None

# Import instance pool for multi-instance support
from test_dashboard.backend.api.instances import instance_pool, InstancePool, MLServerInstance, InstanceStatus

logger = logging.getLogger(__name__)


class TestCaseLog(BaseModel):
    """Test case execution log with full server logs"""
    test_case_id: str
    test_case_name: str
    status: str  # passed, failed, skipped
    execution_time: float
    request_data: Dict[str, Any]
    response_data: Dict[str, Any]
    server_logs: List[str]
    error_message: Optional[str] = None
    instance_digit: Optional[int] = None  # ML server instance used
    ml_port: Optional[int] = None  # ML server port used
    db_port: Optional[int] = None  # Database port used


async def capture_ml_server_logs(log_capture_info: Dict[str, Any]) -> None:
    """
    Capture ML server logs from multiple sources
    
    Args:
        log_capture_info: Dictionary containing:
            - log_list: List to append captured logs to
            - process: Optional subprocess.Popen instance if we started the server
            - log_file_path: Path to temporary log file
            - start_time: When to start capturing logs from
    """
    log_list = log_capture_info['log_list']
    process = log_capture_info.get('process')
    log_file_path = log_capture_info.get('log_file_path')
    start_time = log_capture_info.get('start_time', datetime.now())
    
    try:
        import aiofiles
        
        # Monitor multiple log sources
        log_sources = []
        
        # 1. If we have a subprocess, capture its output
        if process and process.poll() is None:
            # Process is running
            log_sources.append(('subprocess', process))
        
        # 2. Check for existing ML server log files
        ml_server_log_locations = [
            "/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/logs/ml_server.log",
            "/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/ml_server.log",
            "./logs/ml_server.log",
            "./ml_server.log",
            f"/tmp/ml_server_{log_capture_info.get('port', 6001)}.log",
            # Add more potential log locations
            f"/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/logs/humansa_{log_capture_info.get('port', 6001)}.log",
            f"/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1/humansa.log"
        ]
        
        for log_path in ml_server_log_locations:
            if os.path.exists(log_path):
                log_sources.append(('file', log_path))
                logger.info(f"📋 Found ML server log file at: {log_path}")
        
        # 3. Add temporary log file if specified
        if log_file_path and os.path.exists(log_file_path):
            log_sources.append(('file', log_file_path))
        
        # Start monitoring all sources
        file_positions = {}
        
        # Initialize file positions to end of file (only capture new content)
        for source_type, source in log_sources:
            if source_type == 'file':
                try:
                    file_positions[source] = os.path.getsize(source)
                except:
                    file_positions[source] = 0
        
        # Main monitoring loop
        consecutive_empty_reads = 0
        max_empty_reads = 50  # Stop after 5 seconds of no activity
        
        while consecutive_empty_reads < max_empty_reads:
            found_new_content = False
            
            # Check each log source
            for source_type, source in log_sources:
                try:
                    if source_type == 'file':
                        # Read new content from file
                        async with aiofiles.open(source, 'r') as f:
                            await f.seek(file_positions.get(source, 0))
                            new_content = await f.read()
                            
                            if new_content:
                                found_new_content = True
                                consecutive_empty_reads = 0
                                
                                # Process and add new lines
                                for line in new_content.strip().split('\n'):
                                    if line.strip():
                                        # Parse log line - handle various formats
                                        if ' - ' in line and line[:19].replace('-', '').replace(' ', '').replace(':', '').replace('.', '').isdigit():
                                            # Standard log format: 2024-01-01 12:00:00.123 - INFO - message
                                            log_list.append(line)
                                        elif any(emoji in line for emoji in ['🤔', '💭', '🔧', '📊', '✅', '❌', '⚠️', '🏃', '📋']):
                                            # Enhanced logging with emojis (agent thinking)
                                            log_list.append(line)
                                        elif line.startswith('[') and ']' in line[:20]:
                                            # Bracketed format like [ML Server], [SERVER], etc.
                                            log_list.append(line)
                                        else:
                                            # Raw output - preserve as is for agent thinking
                                            log_list.append(line)
                                
                                # Update position
                                file_positions[source] = await f.tell()
                    
                    elif source_type == 'subprocess' and source.poll() is None:
                        # Read from subprocess stdout/stderr if available
                        # This is handled by the file redirect, so we just check if process is alive
                        pass
                        
                except Exception as e:
                    logger.debug(f"Error reading from {source_type} {source}: {e}")
            
            if not found_new_content:
                consecutive_empty_reads += 1
            
            await asyncio.sleep(0.1)  # Check every 100ms
        
        logger.info(f"📋 Log capture completed. Captured {len(log_list)} log lines")
        
    except asyncio.CancelledError:
        logger.info("Log capture task cancelled")
    except Exception as e:
        logger.error(f"Error in log capture: {e}")


async def execute_test_with_log_capture(
    test_case: Any,
    test_ref: Any,
    ml_server_url: str,
    ml_server_logs: List[str],
    instance: Optional[MLServerInstance] = None
) -> TestCaseLog:
    """
    Execute a single test case with full log capture and response parsing
    
    Args:
        test_case: Test case definition
        test_ref: Test reference with overrides
        ml_server_url: Base URL of ML server
        ml_server_logs: List to collect server logs
        instance: Optional ML server instance (for multi-instance mode)
        
    Returns:
        TestCaseLog with complete execution details
    """
    # Extract test details
    test_endpoint = test_case.execution.endpoint
    test_payload = test_case.execution.payload.copy()
    test_headers = test_case.execution.headers.copy()
    test_method = test_case.execution.method
    test_timeout = test_case.config.timeout
    
    # Apply any overrides from test_ref
    if test_ref.config_overrides:
        test_payload.update(test_ref.config_overrides)
    
    # Log request details
    request_start_time = datetime.now()
    ml_server_logs.append(f"\n{'='*80}")
    ml_server_logs.append(f"TEST: {test_case.name} ({test_case.id})")
    ml_server_logs.append(f"TIME: {request_start_time.isoformat()}")
    ml_server_logs.append(f"REQUEST URL: {ml_server_url}{test_endpoint}")
    ml_server_logs.append(f"REQUEST METHOD: {test_method}")
    ml_server_logs.append(f"REQUEST HEADERS: {json.dumps(test_headers, indent=2)}")
    ml_server_logs.append(f"REQUEST PAYLOAD: {json.dumps(test_payload, indent=2)}")
    ml_server_logs.append(f"{'='*80}\n")
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(test_timeout)) as client:
            start_time = time.time()
            
            # Check if streaming endpoint
            is_streaming = test_payload.get("stream", False) or "/stream" in test_endpoint
            
            if is_streaming:
                # Handle streaming response
                response_chunks = []
                response_events = []
                
                async with client.stream(
                    test_method,
                    f"{ml_server_url}{test_endpoint}",
                    headers=test_headers,
                    json=test_payload
                ) as response:
                    response.raise_for_status()
                    status_code = response.status_code
                    
                    ml_server_logs.append(f"\n[RESPONSE] Status: {status_code}")
                    ml_server_logs.append("[RESPONSE] Streaming response received:")
                    
                    async for chunk in response.aiter_text():
                        if chunk:
                            response_chunks.append(chunk)
                            # Log first few chunks for debugging
                            if len(response_chunks) <= 3:
                                ml_server_logs.append(f"[STREAM CHUNK {len(response_chunks)}]: {chunk[:200]}...")
                
                response_time = time.time() - start_time
                
                # Parse streaming response
                full_response_text = ""
                response_data = {"output": [], "streaming": True}
                
                for chunk in response_chunks:
                    for line in chunk.strip().split('\n'):
                        if line.startswith('data: '):
                            data_str = line[6:]
                            if data_str == '[DONE]':
                                continue
                            try:
                                event_data = json.loads(data_str)
                                response_events.append(event_data)
                                
                                # Extract text content based on format
                                if 'event' in event_data and event_data['event'] == 'response.output_item.done':
                                    # OpenAI Responses API format
                                    if 'data' in event_data and 'item' in event_data['data']:
                                        item = event_data['data']['item']
                                        if item.get('type') in ['text', 'output_text']:
                                            text = item.get('text', '')
                                            full_response_text += text
                                            response_data['output'].append(item)
                                elif 'choices' in event_data:
                                    # Standard OpenAI streaming format
                                    for choice in event_data.get('choices', []):
                                        if 'delta' in choice and 'content' in choice['delta']:
                                            content = choice['delta']['content']
                                            full_response_text += content
                                elif 'data' in event_data and 'output' in event_data['data']:
                                    # Direct output format
                                    response_data = event_data['data']
                                    
                            except json.JSONDecodeError as e:
                                ml_server_logs.append(f"[WARNING] Failed to parse chunk: {data_str[:100]}")
                
                # Store complete response
                response_data['full_text'] = full_response_text
                response_data['events'] = response_events
                
                ml_server_logs.append(f"\n[RESPONSE] Streaming complete:")
                ml_server_logs.append(f"  - Total chunks: {len(response_chunks)}")
                ml_server_logs.append(f"  - Total events: {len(response_events)}")
                ml_server_logs.append(f"  - Response text length: {len(full_response_text)}")
                ml_server_logs.append(f"  - Response text preview: {full_response_text[:200]}...")
                
            else:
                # Handle non-streaming response
                response = await client.request(
                    test_method,
                    f"{ml_server_url}{test_endpoint}",
                    headers=test_headers,
                    json=test_payload
                )
                response.raise_for_status()
                status_code = response.status_code
                response_time = time.time() - start_time
                
                response_data = response.json()
                ml_server_logs.append(f"\n[RESPONSE] Status: {status_code}")
                ml_server_logs.append(f"[RESPONSE] Time: {response_time:.2f}s")
                ml_server_logs.append(f"[RESPONSE] Data: {json.dumps(response_data, indent=2)}")
                
                # Extract text content
                full_response_text = ""
                if isinstance(response_data, dict):
                    if "output" in response_data:
                        for item in response_data["output"]:
                            if item.get("type") in ["text", "output_text"]:
                                full_response_text += item.get("text", "")
                    elif "choices" in response_data:
                        for choice in response_data["choices"]:
                            if "message" in choice:
                                full_response_text += choice["message"].get("content", "")
                    elif "message" in response_data:
                        full_response_text = response_data["message"]
                    elif "content" in response_data:
                        full_response_text = response_data["content"]
                
                response_data['full_text'] = full_response_text
        
        # Validate response
        validation_passed = True
        validation_errors = []
        
        # Check status code
        expected_status = test_case.expectations.response.status_code
        if status_code != expected_status:
            validation_passed = False
            validation_errors.append(f"Status code mismatch: expected {expected_status}, got {status_code}")
        
        # Check response content
        response_text = response_data.get('full_text', str(response_data))
        
        for keyword in test_case.expectations.response.output_contains:
            if keyword.lower() not in response_text.lower():
                validation_passed = False
                validation_errors.append(f"Response missing expected keyword: '{keyword}'")
        
        for keyword in test_case.expectations.response.output_excludes:
            if keyword.lower() in response_text.lower():
                validation_passed = False
                validation_errors.append(f"Response contains excluded keyword: '{keyword}'")
        
        # Check response length
        min_length = test_case.expectations.response.min_length
        if len(response_text) < min_length:
            validation_passed = False
            validation_errors.append(f"Response too short: {len(response_text)} chars, expected at least {min_length}")
        
        # Log validation results
        ml_server_logs.append(f"\n[VALIDATION] Status: {'PASSED' if validation_passed else 'FAILED'}")
        if validation_errors:
            ml_server_logs.append("[VALIDATION] Errors:")
            for error in validation_errors:
                ml_server_logs.append(f"  - {error}")
        
        # Create test log
        return TestCaseLog(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status="passed" if validation_passed else "failed",
            execution_time=response_time,
            request_data=test_payload,
            response_data=response_data,
            server_logs=ml_server_logs.copy(),
            error_message="\n".join(validation_errors) if validation_errors else None,
            instance_digit=instance.digit if instance else None,
            ml_port=instance.ml_port if instance else None,
            db_port=instance.db_port if instance else None
        )
        
    except httpx.HTTPError as e:
        ml_server_logs.append(f"\n[ERROR] HTTP error: {str(e)}")
        return TestCaseLog(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status="failed",
            execution_time=time.time() - start_time if 'start_time' in locals() else 0,
            request_data=test_payload,
            response_data={"error": str(e), "type": "http_error"},
            server_logs=ml_server_logs.copy(),
            error_message=f"HTTP Error: {str(e)}",
            instance_digit=instance.digit if instance else None,
            ml_port=instance.ml_port if instance else None,
            db_port=instance.db_port if instance else None
        )
    except Exception as e:
        ml_server_logs.append(f"\n[ERROR] Exception: {str(e)}")
        return TestCaseLog(
            test_case_id=test_case.id,
            test_case_name=test_case.name,
            status="failed",
            execution_time=time.time() - start_time if 'start_time' in locals() else 0,
            request_data=test_payload,
            response_data={"error": str(e), "type": type(e).__name__},
            server_logs=ml_server_logs.copy(),
            error_message=str(e),
            instance_digit=instance.digit if instance else None,
            ml_port=instance.ml_port if instance else None,
            db_port=instance.db_port if instance else None
        )


async def ensure_ml_server_running(ml_port: int, ml_server_logs: List[str]) -> Dict[str, Any]:
    """
    Ensure ML server is running, start it if needed
    
    Returns:
        Dict with:
            - running: bool
            - process: Optional subprocess.Popen instance
            - log_file_path: Optional path to log file
    """
    ml_url = f"http://localhost:{ml_port}"
    
    # Check if already running
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{ml_url}/health")
            if resp.status_code == 200:
                # Check if server has enhanced logging enabled
                health_data = resp.json() if resp.headers.get('content-type', '').startswith('application/json') else {}
                enhanced_logging_enabled = health_data.get('enhanced_logging', False)
                
                if enhanced_logging_enabled:
                    logger.info(f"✅ ML server already running on port {ml_port} with enhanced logging")
                    ml_server_logs.append(f"[SERVER] ML server already running on port {ml_port} with enhanced logging")
                    return {"running": True, "process": None, "log_file_path": None}
                else:
                    logger.warning(f"⚠️ ML server running on port {ml_port} but WITHOUT enhanced logging")
                    ml_server_logs.append(f"[SERVER] ML server running but WITHOUT enhanced logging - restarting...")
                    # Try to stop the existing server
                    try:
                        if psutil:
                            # Find and kill the process using psutil
                            for proc in psutil.process_iter(['pid', 'cmdline']):
                                try:
                                    cmdline = proc.info['cmdline']
                                    if cmdline and 'src.main' in ' '.join(cmdline) and f'--port {ml_port}' in ' '.join(cmdline):
                                        logger.info(f"Stopping ML server process {proc.info['pid']}")
                                        proc.terminate()
                                        proc.wait(timeout=5)
                                        break
                                except (psutil.NoSuchProcess, psutil.AccessDenied):
                                    pass
                        else:
                            # Fallback to shell commands if psutil not available
                            logger.warning("psutil not available, using shell commands to stop server")
                            ml_server_logs.append("[SERVER] Warning: psutil not available, using shell commands")
                            # Try lsof to find the process
                            try:
                                result = subprocess.run(
                                    ["lsof", "-t", "-i", f"tcp:{ml_port}"],
                                    capture_output=True,
                                    text=True
                                )
                                if result.returncode == 0 and result.stdout.strip():
                                    pid = result.stdout.strip()
                                    subprocess.run(["kill", "-TERM", pid])
                                    await asyncio.sleep(2)
                                    logger.info(f"Stopped ML server process {pid}")
                            except Exception as e:
                                logger.warning(f"Failed to stop server using lsof: {e}")
                    except Exception as e:
                        logger.warning(f"Could not stop existing ML server: {e}")
                        ml_server_logs.append(f"[SERVER] Warning: Could not stop existing server: {e}")
    except:
        logger.info(f"ML server not running on port {ml_port}, starting it...")
    
    # Start ML server
    try:
        # Create log file for server output
        log_fd, log_file_path = tempfile.mkstemp(suffix=f"_ml_server_{ml_port}.log", text=True)
        os.close(log_fd)
        
        ml_server_logs.append(f"[SERVER] Starting ML server on port {ml_port}")
        ml_server_logs.append(f"[SERVER] Log file: {log_file_path}")
        ml_server_logs.append(f"[SERVER] Enhanced logging: ENABLED")
        ml_server_logs.append(f"[SERVER] Pattern 2 orchestrator: ENABLED")
        
        # Prepare environment
        env = os.environ.copy()
        env["ENVIRONMENT"] = "test"
        env["ML_SERVER_PORT"] = str(ml_port)
        env["HUMANSA_USE_PATTERN2"] = "true"  # Enable Pattern 2 orchestrator
        env["HUMANSA_ENHANCED_LOGGING"] = "true"  # Enable agent thinking logs
        
        # Start server with output redirection
        with open(log_file_path, 'w') as log_file:
            process = subprocess.Popen(
                ["python3", "-m", "src.main", "--port", str(ml_port)],
                env=env,
                cwd="/Users/shonnli/Non-icloudFile/YouWoAI/Code_Copy/Copy-1/YouWoAI-ML-Server-1",
                stdout=log_file,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=True
            )
        
        # Wait for server to start
        start_time = datetime.now()
        timeout = 60  # seconds
        
        while (datetime.now() - start_time).seconds < timeout:
            await asyncio.sleep(2)
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    resp = await client.get(f"{ml_url}/health")
                    if resp.status_code == 200:
                        logger.info(f"✅ ML server started successfully on port {ml_port}")
                        ml_server_logs.append(f"[SERVER] ML server started successfully (PID: {process.pid})")
                        return {
                            "running": True,
                            "process": process,
                            "log_file_path": log_file_path
                        }
            except:
                if process.poll() is not None:
                    # Process died
                    ml_server_logs.append(f"[SERVER] ERROR: Process died with code {process.returncode}")
                    # Try to read error from log file
                    try:
                        with open(log_file_path, 'r') as f:
                            error_logs = f.read()
                            ml_server_logs.append("[SERVER] Error output:")
                            ml_server_logs.extend(error_logs.split('\n')[:20])  # First 20 lines
                    except:
                        pass
                    raise Exception(f"ML server process died with code {process.returncode}")
                continue
        
        raise Exception("ML server failed to start within timeout")
        
    except Exception as e:
        logger.error(f"Failed to start ML server: {e}")
        ml_server_logs.append(f"[SERVER] ERROR: Failed to start ML server: {e}")
        raise


async def execute_test_worker(
    worker_id: int,
    test_queue: asyncio.Queue,
    job: Any,
    run_id: str,
    run_data: Dict[str, Any],
    shared_logs: Dict[int, List[str]],
    config: Any
) -> None:
    """
    Worker function that processes tests from queue with dedicated ML server instance
    
    Args:
        worker_id: Worker identifier
        test_queue: Queue of test references to process
        job: Job object
        run_id: Run identifier
        run_data: Shared run data dictionary
        shared_logs: Dictionary mapping worker_id to their logs
        config: Job configuration
    """
    from test_dashboard.backend.core.config import settings
    from test_dashboard.backend.core.database import execute_query, execute_update, is_database_available
    from test_dashboard.backend.api.jobs import JobStatus
    
    # Allocate an instance for this worker
    instance = await instance_pool.allocate_instance(f"worker_{worker_id}_job_{job.id}", worker_id)
    if not instance:
        logger.error(f"Worker {worker_id}: No available instance")
        return
    
    # Initialize worker-specific logs
    worker_logs = []
    shared_logs[worker_id] = worker_logs
    
    try:
        logger.info(f"🎯 Worker {worker_id} allocated instance {instance.digit} (ML port {instance.ml_port}, DB port {instance.db_port})")
        worker_logs.append(f"[WORKER {worker_id}] Allocated instance {instance.digit}")
        
        # Set up log capture for this instance
        log_capture_info = {
            'log_list': worker_logs,
            'process': instance.process,
            'log_file_path': f"/tmp/ml_server_instance_{instance.digit}.log",
            'start_time': datetime.now(),
            'port': instance.ml_port
        }
        
        # Start log capture task
        log_capture_task = asyncio.create_task(capture_ml_server_logs(log_capture_info))
        
        ml_url = f"http://localhost:{instance.ml_port}"
        
        while True:
            try:
                # Get next test from queue (non-blocking with timeout)
                test_ref = await asyncio.wait_for(test_queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                # No more tests
                break
            
            if test_ref is None:
                # Sentinel value to stop worker
                break
            
            # Check if job was cancelled/paused
            if job.status in [JobStatus.CANCELLED, JobStatus.PAUSED]:
                await test_queue.put(test_ref)  # Put it back for potential resume
                break
            
            # Execute test
            test_start_time = datetime.now()
            
            # Update test as running
            run_data["results"][test_ref.test_id] = {
                "test_id": test_ref.test_id,
                "status": "running",
                "started_at": test_start_time.isoformat(),
                "worker_id": worker_id,
                "instance_digit": instance.digit
            }
            
            # Get test definition
            test_def = None
            if is_database_available():
                query = "SELECT * FROM test_management.test_definitions WHERE id = %(id)s"
                rows = await execute_query(query, {'id': test_ref.test_id})
                if rows:
                    test_def = rows[0]
            
            if not test_def:
                # Try to get from memory
                from test_dashboard.backend.api.tests import test_definitions
                test_def = test_definitions.get(test_ref.test_id)
            
            if not test_def:
                # Test not found
                logger.error(f"Worker {worker_id}: Test definition not found: {test_ref.test_id}")
                test_log = TestCaseLog(
                    test_case_id=test_ref.test_id,
                    test_case_name=test_ref.test_id,
                    status="failed",
                    execution_time=0,
                    request_data={},
                    response_data={"error": "Test definition not found"},
                    server_logs=worker_logs.copy(),
                    error_message=f"Test definition not found: {test_ref.test_id}",
                    instance_digit=instance.digit,
                    ml_port=instance.ml_port,
                    db_port=instance.db_port
                )
            else:
                # Create test case object
                if isinstance(test_def, dict):
                    # Convert dict to object
                    test_case = type('TestCase', (), {
                        'id': test_def['id'],
                        'name': test_def['name'],
                        'suite': test_def.get('suite', 'unknown'),
                        'type': test_def.get('type', 'single'),
                        'config': type('Config', (), {
                            'timeout': test_def.get('config', {}).get('timeout', 30)
                        })(),
                        'execution': type('Execution', (), {
                            'endpoint': test_def.get('execution', {}).get('endpoint', '/v2/humansa/responses/create'),
                            'method': test_def.get('execution', {}).get('method', 'POST'),
                            'headers': test_def.get('execution', {}).get('headers', {'Content-Type': 'application/json'}),
                            'payload': test_def.get('execution', {}).get('payload', {})
                        })(),
                        'expectations': type('Expectations', (), {
                            'response': type('ResponseExpectations', (), {
                                'status_code': test_def.get('expectations', {}).get('response', {}).get('status_code', 200),
                                'output_contains': test_def.get('expectations', {}).get('response', {}).get('output_contains', []),
                                'output_excludes': test_def.get('expectations', {}).get('response', {}).get('output_excludes', []),
                                'min_length': test_def.get('expectations', {}).get('response', {}).get('min_length', 0)
                            })()
                        })(),
                        'setup': test_def.get('setup', {})
                    })()
                else:
                    test_case = test_def
                
                # Update payload with instance-specific database connection
                if hasattr(test_case.execution.payload, 'update'):
                    test_case.execution.payload.update({
                        "db_port": instance.db_port,
                        "instance_id": instance.digit
                    })
                
                # Handle multi-turn tests
                if test_case.type == 'multi_turn':
                    setup = test_case.setup if hasattr(test_case, 'setup') else {}
                    if isinstance(setup, dict):
                        previous_turns = setup.get('previous_turns', [])
                    else:
                        previous_turns = getattr(setup, 'previous_turns', [])
                    
                    # Execute previous turns
                    worker_logs.append(f"\n[MULTI-TURN] Setting up {len(previous_turns)} previous turns")
                    previous_response_id = None
                    
                    for i, turn in enumerate(previous_turns):
                        # Handle both dict and object access patterns
                        if isinstance(turn, dict):
                            role = turn.get('role')
                            content = turn.get('content', '')
                        else:
                            role = getattr(turn, 'role', None)
                            content = getattr(turn, 'content', '')
                        
                        if role == 'user':
                            turn_payload = {
                                "model": test_case.execution.payload.get("model", "gpt-4.1"),
                                "input": content,
                                "user_id": test_case.execution.payload.get("user_id", f"test_user_{test_ref.test_id}"),
                                "metadata": {
                                    "test_id": test_ref.test_id,
                                    "turn": f"setup_{i+1}",
                                    "instance_id": instance.digit
                                },
                                "db_port": instance.db_port
                            }
                            
                            if previous_response_id:
                                turn_payload["previous_response_id"] = previous_response_id
                            
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    turn_response = await client.post(
                                        f"{ml_url}{test_case.execution.endpoint}",
                                        json=turn_payload
                                    )
                                    if turn_response.status_code == 200:
                                        turn_data = turn_response.json()
                                        # Extract response ID
                                        if 'id' in turn_data:
                                            previous_response_id = turn_data['id']
                                        elif 'response_id' in turn_data:
                                            previous_response_id = turn_data['response_id']
                                        worker_logs.append(f"[MULTI-TURN] Turn {i+1} completed, response_id: {previous_response_id}")
                                    else:
                                        worker_logs.append(f"[MULTI-TURN] Turn {i+1} failed: {turn_response.status_code}")
                            except Exception as e:
                                worker_logs.append(f"[MULTI-TURN] Turn {i+1} error: {str(e)}")
                    
                    # Update payload with previous response ID
                    if previous_response_id:
                        test_case.execution.payload["previous_response_id"] = previous_response_id
                
                # Execute test with enhanced log capture
                test_log = await execute_test_with_log_capture(
                    test_case=test_case,
                    test_ref=test_ref,
                    ml_server_url=ml_url,
                    ml_server_logs=worker_logs,
                    instance=instance
                )
            
            # Update run data with results
            run_data["results"][test_ref.test_id] = {
                "test_id": test_log.test_case_id,
                "test_name": test_log.test_case_name,
                "suite": test_case.suite if 'test_case' in locals() else 'unknown',
                "status": "completed" if test_log.status == "passed" else "failed",
                "started_at": test_start_time.isoformat(),
                "completed_at": datetime.now().isoformat(),
                "duration": test_log.execution_time,
                "success": test_log.status == "passed",
                "error": test_log.error_message,
                "response": test_log.response_data,
                "worker_id": worker_id,
                "instance_digit": instance.digit,
                "ml_port": instance.ml_port,
                "db_port": instance.db_port
            }
            
            # Update database if available
            if is_database_available():
                # Insert result
                result_query = """
                    INSERT INTO test_management.results
                    (run_id, test_id, suite_name, test_name, status, started_at, completed_at, execution_time, error_message)
                    VALUES (%(run_id)s, %(test_id)s, %(suite)s, %(test_name)s, %(status)s, %(started_at)s, %(completed_at)s, %(duration)s, %(error)s)
                """
                
                await execute_update(result_query, {
                    'run_id': run_id,
                    'test_id': test_log.test_case_id,
                    'suite': test_case.suite if 'test_case' in locals() else 'unknown',
                    'test_name': test_log.test_case_name,
                    'status': test_log.status,
                    'started_at': test_start_time,
                    'completed_at': datetime.now(),
                    'duration': test_log.execution_time,
                    'error': test_log.error_message
                })
                
                # Store full test logs with instance info
                logs_query = """
                    INSERT INTO test_management.test_case_logs
                    (result_id, request, response, server_logs, performance_metrics)
                    VALUES (
                        (SELECT id FROM test_management.results WHERE run_id = %(run_id)s AND test_id = %(test_id)s LIMIT 1),
                        %(request)s, %(response)s, %(server_logs)s, %(performance_metrics)s
                    )
                """
                
                request_data = {
                    "endpoint": test_case.execution.endpoint if 'test_case' in locals() else "unknown",
                    "method": test_case.execution.method if 'test_case' in locals() else "POST",
                    "headers": test_case.execution.headers if 'test_case' in locals() else {},
                    "payload": test_log.request_data
                }
                
                server_logs_data = {
                    "logs": test_log.server_logs,
                    "ml_server_logs": test_log.server_logs,
                    "backend_logs": [],
                    "log_count": len(test_log.server_logs),
                    "ml_server_port": instance.ml_port,
                    "db_port": instance.db_port,
                    "instance_digit": instance.digit,
                    "worker_id": worker_id,
                    "captured_at": datetime.now().isoformat()
                }
                
                performance_metrics = {
                    "execution_time_seconds": test_log.execution_time,
                    "test_status": test_log.status,
                    "validation_passed": test_log.status == "passed",
                    "worker_id": worker_id,
                    "instance_digit": instance.digit
                }
                
                await execute_update(logs_query, {
                    'run_id': run_id,
                    'test_id': test_log.test_case_id,
                    'request': json.dumps(request_data),
                    'response': json.dumps(test_log.response_data),
                    'server_logs': json.dumps(server_logs_data),
                    'performance_metrics': json.dumps(performance_metrics)
                })
            
            # Update job stats
            if test_log.status == "failed":
                job.failed_tests = (job.failed_tests or 0) + 1
            
            # Update completed tests count
            job.completed_tests = len([r for r in run_data["results"].values() if r.get("status") in ["completed", "failed"]])
            job.updated_at = datetime.now()
            
            logger.info(f"Worker {worker_id}: Completed test {test_ref.test_id} - {test_log.status}")
    
    except Exception as e:
        logger.error(f"Worker {worker_id} error: {e}", exc_info=True)
        worker_logs.append(f"[WORKER {worker_id}] ERROR: {str(e)}")
    
    finally:
        # Clean up
        if 'log_capture_task' in locals() and not log_capture_task.done():
            log_capture_task.cancel()
            try:
                await log_capture_task
            except asyncio.CancelledError:
                pass
        
        # Release instance back to pool
        if instance:
            await instance_pool.release_instance(instance.digit)
            logger.info(f"🔄 Worker {worker_id} released instance {instance.digit}")


async def execute_job_background_multi_instance(job_id: str, run_id: str, config: Any):
    """Multi-instance background job execution with worker pool"""
    from test_dashboard.backend.core.config import settings
    from test_dashboard.backend.core.database import execute_query, execute_update, is_database_available
    from test_dashboard.backend.api.jobs import get_job, jobs_storage, job_runs, JobStatus, job_service
    
    # Initialize shared data structures
    shared_logs = {}  # Maps worker_id to their logs
    
    try:
        # Get job from database or memory
        job = await get_job(job_id)
        
        # Get or create run data
        if run_id not in job_runs:
            job_runs[run_id] = {
                "job_id": job_id,
                "run_id": run_id,
                "started_at": datetime.now(),
                "completed_at": None,
                "status": "running",
                "environment_id": config.environment_id,
                "config": config.dict() if hasattr(config, 'dict') else config,
                "results": {},
                "dry_run": False
            }
        run_data = job_runs[run_id]
        
        # Start job
        await job_service.update_job_status(job_id, run_id, "running")
        logger.info(f"🏃 Starting multi-instance job execution for {job_id}/{run_id}")
        
        # Initialize instance pool if needed
        if not instance_pool.instances:
            num_workers = config.max_workers if hasattr(config, 'max_workers') else 8
            await instance_pool.initialize(num_workers)
        
        # Determine number of workers based on available instances
        available_instances = await instance_pool.get_status()
        num_workers = min(
            available_instances['available'],
            config.max_workers if hasattr(config, 'max_workers') else 8,
            len(job.tests)  # Don't create more workers than tests
        )
        
        logger.info(f"Using {num_workers} workers with {available_instances['available']} available instances")
        
        # Create test queue
        test_queue = asyncio.Queue()
        for test_ref in job.tests:
            await test_queue.put(test_ref)
        
        # Create worker tasks
        workers = []
        for worker_id in range(num_workers):
            worker = asyncio.create_task(
                execute_test_worker(
                    worker_id=worker_id,
                    test_queue=test_queue,
                    job=job,
                    run_id=run_id,
                    run_data=run_data,
                    shared_logs=shared_logs,
                    config=config
                )
            )
            workers.append(worker)
        
        # Wait for all workers to complete
        await asyncio.gather(*workers, return_exceptions=True)
        
        # Consolidate logs from all workers
        consolidated_logs = []
        for worker_id in sorted(shared_logs.keys()):
            consolidated_logs.extend(shared_logs[worker_id])
        
        # Complete job
        if job.status != JobStatus.CANCELLED:
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.total_tests = len(job.tests)
            job.completed_tests = len([r for r in run_data["results"].values() if r.get("status") in ["completed", "failed"]])
            run_data["status"] = "completed"
            run_data["completed_at"] = datetime.now()
            
            # Update database
            if is_database_available():
                passed = len([r for r in run_data["results"].values() if r.get("success") == True])
                failed = len([r for r in run_data["results"].values() if r.get("success") == False])
                
                await execute_update("""
                    UPDATE test_management.runs
                    SET status = %(status)s, completed_at = %(completed_at)s,
                        total_tests = %(total)s, passed_tests = %(passed)s, failed_tests = %(failed)s
                    WHERE id = %(run_id)s
                """, {
                    'status': 'completed',
                    'completed_at': job.completed_at,
                    'total': len(job.tests),
                    'passed': passed,
                    'failed': failed,
                    'run_id': run_id
                })
        
        jobs_storage[job_id] = job
        await job_service.update_job_status(job_id, run_id, "completed")
        logger.info(f"✅ Multi-instance job {job_id}/{run_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Multi-instance job execution failed: {e}", exc_info=True)
        
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.failed_tests = len(job.tests) if hasattr(job, 'tests') else 0
            jobs_storage[job_id] = job
        
        if 'run_data' in locals():
            run_data["status"] = "failed"
            run_data["error"] = str(e)
            run_data["completed_at"] = datetime.now()
        
        # Update database
        if is_database_available():
            await execute_update("""
                UPDATE test_management.runs
                SET status = %(status)s, completed_at = %(completed_at)s, error_message = %(error)s
                WHERE id = %(run_id)s
            """, {
                'status': 'failed',
                'completed_at': datetime.now(),
                'error': str(e),
                'run_id': run_id
            })
        
        await job_service.update_job_status(job_id, run_id, "failed", error=str(e))


async def execute_job_background_enhanced(job_id: str, run_id: str, config: Any):
    """Enhanced background job execution with full server log capture"""
    from test_dashboard.backend.core.config import settings
    from test_dashboard.backend.core.database import execute_query, execute_update, is_database_available
    from test_dashboard.backend.api.jobs import get_job, jobs_storage, job_runs, JobStatus, job_service
    import subprocess
    
    # Initialize log capture
    ml_server_logs = []
    log_capture_task = None
    server_info = None
    
    try:
        # Get job from database or memory
        job = await get_job(job_id)
        
        # Get or create run data
        if run_id not in job_runs:
            job_runs[run_id] = {
                "job_id": job_id,
                "run_id": run_id,
                "started_at": datetime.now(),
                "completed_at": None,
                "status": "running",
                "environment_id": config.environment_id,
                "config": config.dict() if hasattr(config, 'dict') else config,
                "results": {},
                "dry_run": False
            }
        run_data = job_runs[run_id]
        
        # Start job
        await job_service.update_job_status(job_id, run_id, "running")
        logger.info(f"🏃 Starting enhanced job execution for {job_id}/{run_id}")
        
        # Check/start ML server
        ml_port = settings.ML_SERVER_PORT or 6001
        ml_url = f"http://localhost:{ml_port}"
        
        # Ensure ML server is running with log capture
        server_info = await ensure_ml_server_running(ml_port, ml_server_logs)
        if not server_info['running']:
            error_msg = "Failed to start ML server"
            logger.error(error_msg)
            await job_service.update_job_status(job_id, run_id, "failed", error=error_msg)
            return
        
        # Set up log capture
        log_capture_info = {
            'log_list': ml_server_logs,
            'process': server_info.get('process'),
            'log_file_path': server_info.get('log_file_path'),
            'start_time': datetime.now(),
            'port': ml_port
        }
        
        # Start log capture task
        log_capture_task = asyncio.create_task(capture_ml_server_logs(log_capture_info))
        
        total_tests = len(job.tests)
        
        # Execute each test
        for i, test_ref in enumerate(job.tests):
            # Check if job was cancelled/paused
            if job.status in [JobStatus.CANCELLED, JobStatus.PAUSED]:
                break
            
            # Update test as running
            run_data["results"][test_ref.test_id] = {
                "test_id": test_ref.test_id,
                "status": "running",
                "started_at": datetime.now().isoformat()
            }
            
            # Update job progress
            job.completed_tests = i
            job.updated_at = datetime.now()
            jobs_storage[job_id] = job
            
            # Get test definition
            test_def = None
            if is_database_available():
                query = "SELECT * FROM test_management.test_definitions WHERE id = %(id)s"
                rows = await execute_query(query, {'id': test_ref.test_id})
                if rows:
                    test_def = rows[0]
            
            if not test_def:
                # Try to get from memory
                from test_dashboard.backend.api.tests import test_definitions
                test_def = test_definitions.get(test_ref.test_id)
            
            if not test_def:
                # Test not found
                logger.error(f"Test definition not found: {test_ref.test_id}")
                test_log = TestCaseLog(
                    test_case_id=test_ref.test_id,
                    test_case_name=test_ref.test_id,
                    status="failed",
                    execution_time=0,
                    request_data={},
                    response_data={"error": "Test definition not found"},
                    server_logs=ml_server_logs.copy(),
                    error_message=f"Test definition not found: {test_ref.test_id}"
                )
            else:
                # Create test case object for enhanced execution
                if isinstance(test_def, dict):
                    # Convert dict to object
                    test_case = type('TestCase', (), {
                        'id': test_def['id'],
                        'name': test_def['name'],
                        'suite': test_def.get('suite', 'unknown'),
                        'type': test_def.get('type', 'single'),
                        'config': type('Config', (), {
                            'timeout': test_def.get('config', {}).get('timeout', 30)
                        })(),
                        'execution': type('Execution', (), {
                            'endpoint': test_def.get('execution', {}).get('endpoint', '/v2/humansa/responses/create'),
                            'method': test_def.get('execution', {}).get('method', 'POST'),
                            'headers': test_def.get('execution', {}).get('headers', {'Content-Type': 'application/json'}),
                            'payload': test_def.get('execution', {}).get('payload', {})
                        })(),
                        'expectations': type('Expectations', (), {
                            'response': type('ResponseExpectations', (), {
                                'status_code': test_def.get('expectations', {}).get('response', {}).get('status_code', 200),
                                'output_contains': test_def.get('expectations', {}).get('response', {}).get('output_contains', []),
                                'output_excludes': test_def.get('expectations', {}).get('response', {}).get('output_excludes', []),
                                'min_length': test_def.get('expectations', {}).get('response', {}).get('min_length', 0)
                            })()
                        })(),
                        'setup': test_def.get('setup', {})
                    })()
                else:
                    # Already a proper object
                    test_case = test_def
                
                # Handle multi-turn tests
                if test_case.type == 'multi_turn':
                    setup = test_case.setup if hasattr(test_case, 'setup') else {}
                    if isinstance(setup, dict):
                        previous_turns = setup.get('previous_turns', [])
                    else:
                        previous_turns = getattr(setup, 'previous_turns', [])
                    
                    # Execute previous turns
                    ml_server_logs.append(f"\n[MULTI-TURN] Setting up {len(previous_turns)} previous turns")
                    previous_response_id = None
                    
                    for i, turn in enumerate(previous_turns):
                        # Handle both dict and object access patterns
                        if isinstance(turn, dict):
                            role = turn.get('role')
                            content = turn.get('content', '')
                        else:
                            role = getattr(turn, 'role', None)
                            content = getattr(turn, 'content', '')
                        
                        if role == 'user':
                            turn_payload = {
                                "model": test_case.execution.payload.get("model", "gpt-4.1"),
                                "input": content,
                                "user_id": test_case.execution.payload.get("user_id", f"test_user_{test_ref.test_id}"),
                                "metadata": {
                                    "test_id": test_ref.test_id,
                                    "turn": f"setup_{i+1}"
                                }
                            }
                            
                            if previous_response_id:
                                turn_payload["previous_response_id"] = previous_response_id
                            
                            try:
                                async with httpx.AsyncClient(timeout=30.0) as client:
                                    turn_response = await client.post(
                                        f"{ml_url}{test_case.execution.endpoint}",
                                        json=turn_payload
                                    )
                                    if turn_response.status_code == 200:
                                        turn_data = turn_response.json()
                                        # Extract response ID
                                        if 'id' in turn_data:
                                            previous_response_id = turn_data['id']
                                        elif 'response_id' in turn_data:
                                            previous_response_id = turn_data['response_id']
                                        ml_server_logs.append(f"[MULTI-TURN] Turn {i+1} completed, response_id: {previous_response_id}")
                                    else:
                                        ml_server_logs.append(f"[MULTI-TURN] Turn {i+1} failed: {turn_response.status_code}")
                            except Exception as e:
                                ml_server_logs.append(f"[MULTI-TURN] Turn {i+1} error: {str(e)}")
                    
                    # Update payload with previous response ID
                    if previous_response_id:
                        test_case.execution.payload["previous_response_id"] = previous_response_id
                
                # Execute test with enhanced log capture
                test_log = await execute_test_with_log_capture(
                    test_case=test_case,
                    test_ref=test_ref,
                    ml_server_url=ml_url,
                    ml_server_logs=ml_server_logs
                )
            
            # Update run data with results
            run_data["results"][test_ref.test_id] = {
                "test_id": test_log.test_case_id,
                "test_name": test_log.test_case_name,
                "suite": test_case.suite if 'test_case' in locals() else 'unknown',
                "status": "completed" if test_log.status == "passed" else "failed",
                "started_at": datetime.now().isoformat(),
                "completed_at": datetime.now().isoformat(),
                "duration": test_log.execution_time,
                "success": test_log.status == "passed",
                "error": test_log.error_message,
                "response": test_log.response_data
            }
            
            # Update database if available
            if is_database_available():
                # Insert result
                result_query = """
                    INSERT INTO test_management.results
                    (run_id, test_id, suite_name, test_name, status, started_at, completed_at, execution_time, error_message)
                    VALUES (%(run_id)s, %(test_id)s, %(suite)s, %(test_name)s, %(status)s, %(started_at)s, %(completed_at)s, %(duration)s, %(error)s)
                """
                
                await execute_update(result_query, {
                    'run_id': run_id,
                    'test_id': test_log.test_case_id,
                    'suite': test_case.suite if 'test_case' in locals() else 'unknown',
                    'test_name': test_log.test_case_name,
                    'status': test_log.status,
                    'started_at': datetime.now() - timedelta(seconds=test_log.execution_time),
                    'completed_at': datetime.now(),
                    'duration': test_log.execution_time,
                    'error': test_log.error_message
                })
                
                # Store full test logs
                logs_query = """
                    INSERT INTO test_management.test_case_logs
                    (result_id, request, response, server_logs, performance_metrics)
                    VALUES (
                        (SELECT id FROM test_management.results WHERE run_id = %(run_id)s AND test_id = %(test_id)s LIMIT 1),
                        %(request)s, %(response)s, %(server_logs)s, %(performance_metrics)s
                    )
                """
                
                request_data = {
                    "endpoint": test_case.execution.endpoint if 'test_case' in locals() else "unknown",
                    "method": test_case.execution.method if 'test_case' in locals() else "POST",
                    "headers": test_case.execution.headers if 'test_case' in locals() else {},
                    "payload": test_log.request_data
                }
                
                server_logs_data = {
                    "logs": test_log.server_logs,  # ML server logs with agent thinking
                    "ml_server_logs": test_log.server_logs,  # Explicitly labeled ML logs
                    "backend_logs": [],  # Backend API logs (if any)
                    "log_count": len(test_log.server_logs),
                    "ml_server_port": ml_port,
                    "captured_at": datetime.now().isoformat()
                }
                
                performance_metrics = {
                    "execution_time_seconds": test_log.execution_time,
                    "test_status": test_log.status,
                    "validation_passed": test_log.status == "passed"
                }
                
                await execute_update(logs_query, {
                    'run_id': run_id,
                    'test_id': test_log.test_case_id,
                    'request': json.dumps(request_data),
                    'response': json.dumps(test_log.response_data),
                    'server_logs': json.dumps(server_logs_data),
                    'performance_metrics': json.dumps(performance_metrics)
                })
            
            # Update job stats
            if test_log.status == "failed":
                job.failed_tests = (job.failed_tests or 0) + 1
            
            # Add log entry
            if "logs" not in run_data:
                run_data["logs"] = []
            run_data["logs"].append({
                "timestamp": datetime.now().isoformat(),
                "level": "INFO",
                "message": f"Test {test_ref.test_id} {test_log.status}: {test_log.test_case_name}"
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
            
            # Update database
            if is_database_available():
                passed = len([r for r in run_data["results"].values() if r.get("success") == True])
                failed = len([r for r in run_data["results"].values() if r.get("success") == False])
                
                await execute_update("""
                    UPDATE test_management.runs
                    SET status = %(status)s, completed_at = %(completed_at)s,
                        total_tests = %(total)s, passed_tests = %(passed)s, failed_tests = %(failed)s
                    WHERE id = %(run_id)s
                """, {
                    'status': 'completed',
                    'completed_at': job.completed_at,
                    'total': total_tests,
                    'passed': passed,
                    'failed': failed,
                    'run_id': run_id
                })
        
        jobs_storage[job_id] = job
        await job_service.update_job_status(job_id, run_id, "completed")
        logger.info(f"✅ Enhanced job {job_id}/{run_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job execution failed: {e}", exc_info=True)
        
        if 'job' in locals():
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.updated_at = datetime.now()
            job.failed_tests = len(job.tests) if hasattr(job, 'tests') else 0
            jobs_storage[job_id] = job
        
        if 'run_data' in locals():
            run_data["status"] = "failed"
            run_data["error"] = str(e)
            run_data["completed_at"] = datetime.now()
        
        # Update database
        if is_database_available():
            await execute_update("""
                UPDATE test_management.runs
                SET status = %(status)s, completed_at = %(completed_at)s, error_message = %(error)s
                WHERE id = %(run_id)s
            """, {
                'status': 'failed',
                'completed_at': datetime.now(),
                'error': str(e),
                'run_id': run_id
            })
        
        await job_service.update_job_status(job_id, run_id, "failed", error=str(e))
    
    finally:
        # Clean up
        if log_capture_task and not log_capture_task.done():
            log_capture_task.cancel()
            try:
                await log_capture_task
            except asyncio.CancelledError:
                pass
        
        # Clean up server process if we started it
        if server_info and server_info.get('process'):
            process = server_info['process']
            if process.poll() is None:
                logger.info(f"Terminating ML server process (PID: {process.pid})")
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
        
        # Clean up log files
        if server_info and server_info.get('log_file_path'):
            try:
                os.remove(server_info['log_file_path'])
            except:
                pass