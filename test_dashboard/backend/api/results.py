"""
Results Management API
======================

Handles test result analysis, reporting, and historical data management.
"""

import json
import statistics
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import asyncio


# Enums
class ResultStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


class AggregationPeriod(str, Enum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


# Pydantic models
class ResultSummary(BaseModel):
    """Test result summary"""
    run_id: str
    test_id: str
    test_name: str
    suite: str
    status: ResultStatus
    success: bool
    score: Optional[float] = None
    duration: Optional[float] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class SuiteAnalytics(BaseModel):
    """Test suite analytics"""
    suite: str
    total_tests: int
    total_runs: int
    success_rate: float
    average_duration: float
    average_score: Optional[float] = None
    failure_rate: float
    most_common_failures: List[Dict[str, Any]] = []
    trend: Dict[str, float] = {}


class TestAnalytics(BaseModel):
    """Individual test analytics"""
    test_id: str
    test_name: str
    suite: str
    total_runs: int
    success_rate: float
    average_duration: float
    average_score: Optional[float] = None
    best_score: Optional[float] = None
    worst_score: Optional[float] = None
    recent_trend: str  # "improving", "declining", "stable"
    failure_patterns: List[str] = []
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None


class PerformanceMetrics(BaseModel):
    """Performance metrics"""
    metric: str
    value: float
    unit: str
    timestamp: datetime
    test_id: Optional[str] = None
    run_id: Optional[str] = None


class TrendData(BaseModel):
    """Trend data point"""
    timestamp: datetime
    value: float
    label: str


class ResultsFilter(BaseModel):
    """Results filtering parameters"""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    suites: List[str] = []
    test_ids: List[str] = []
    run_ids: List[str] = []
    status: Optional[ResultStatus] = None
    min_score: Optional[float] = None
    max_score: Optional[float] = None
    min_duration: Optional[float] = None
    max_duration: Optional[float] = None


class ComparisonReport(BaseModel):
    """Comparison report between two time periods or runs"""
    comparison_type: str  # "time_period" or "runs"
    baseline: Dict[str, Any]
    current: Dict[str, Any]
    changes: Dict[str, Any]
    significant_changes: List[Dict[str, Any]] = []


# Create router
router = APIRouter()

# Import database utilities
from test_dashboard.backend.core.database import execute_query, is_database_available

# Import runs storage from runs module
# In production, this would be a proper database query
from .runs import runs_storage


def get_all_results() -> List[ResultSummary]:
    """Get all test results from runs storage"""
    results = []
    
    for run in runs_storage.values():
        for test_result in run.results.values():
            if test_result.completed_at:
                status = ResultStatus.PASSED if test_result.success else ResultStatus.FAILED
                if test_result.status.value in ["error", "timeout", "skipped"]:
                    status = ResultStatus(test_result.status.value)
                
                results.append(ResultSummary(
                    run_id=run.id,
                    test_id=test_result.test_id,
                    test_name=test_result.test_name,
                    suite=test_result.suite,
                    status=status,
                    success=test_result.success,
                    score=test_result.score,
                    duration=test_result.duration,
                    started_at=test_result.started_at,
                    completed_at=test_result.completed_at,
                    error_message=test_result.error_message
                ))
    
    return results


def filter_results(results: List[ResultSummary], filters: ResultsFilter) -> List[ResultSummary]:
    """Apply filters to results"""
    filtered = results
    
    if filters.start_date:
        filtered = [r for r in filtered if r.started_at >= filters.start_date]
    if filters.end_date:
        filtered = [r for r in filtered if r.started_at <= filters.end_date]
    if filters.suites:
        filtered = [r for r in filtered if r.suite in filters.suites]
    if filters.test_ids:
        filtered = [r for r in filtered if r.test_id in filters.test_ids]
    if filters.run_ids:
        filtered = [r for r in filtered if r.run_id in filters.run_ids]
    if filters.status:
        filtered = [r for r in filtered if r.status == filters.status]
    if filters.min_score is not None:
        filtered = [r for r in filtered if r.score is not None and r.score >= filters.min_score]
    if filters.max_score is not None:
        filtered = [r for r in filtered if r.score is not None and r.score <= filters.max_score]
    if filters.min_duration is not None:
        filtered = [r for r in filtered if r.duration is not None and r.duration >= filters.min_duration]
    if filters.max_duration is not None:
        filtered = [r for r in filtered if r.duration is not None and r.duration <= filters.max_duration]
    
    return filtered


@router.get("/", response_model=List[ResultSummary])
@router.get("", response_model=List[ResultSummary])
async def list_results(
    suite: Optional[str] = None,
    test_id: Optional[str] = None,
    run_id: Optional[str] = None,
    status: Optional[ResultStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0
):
    """List test results with filtering"""
    results = get_all_results()
    
    # Apply filters
    filters = ResultsFilter(
        start_date=start_date,
        end_date=end_date,
        suites=[suite] if suite else [],
        test_ids=[test_id] if test_id else [],
        run_ids=[run_id] if run_id else [],
        status=status
    )
    
    filtered_results = filter_results(results, filters)
    
    # Sort by start time (newest first)
    filtered_results.sort(key=lambda x: x.started_at, reverse=True)
    
    # Apply pagination
    return filtered_results[offset:offset + limit]


@router.get("/summary")
async def get_results_summary(
    suite: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get results summary statistics"""
    results = get_all_results()
    
    # Apply filters
    filters = ResultsFilter(
        start_date=start_date,
        end_date=end_date,
        suites=[suite] if suite else []
    )
    filtered_results = filter_results(results, filters)
    
    if not filtered_results:
        return {
            "total_results": 0,
            "success_rate": 0,
            "failure_rate": 0,
            "error_rate": 0,
            "average_duration": 0,
            "average_score": 0
        }
    
    total = len(filtered_results)
    passed = len([r for r in filtered_results if r.status == ResultStatus.PASSED])
    failed = len([r for r in filtered_results if r.status == ResultStatus.FAILED])
    errors = len([r for r in filtered_results if r.status in [ResultStatus.ERROR, ResultStatus.TIMEOUT]])
    
    durations = [r.duration for r in filtered_results if r.duration is not None]
    scores = [r.score for r in filtered_results if r.score is not None]
    
    return {
        "total_results": total,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "success_rate": (passed / total * 100) if total > 0 else 0,
        "failure_rate": (failed / total * 100) if total > 0 else 0,
        "error_rate": (errors / total * 100) if total > 0 else 0,
        "average_duration": statistics.mean(durations) if durations else 0,
        "median_duration": statistics.median(durations) if durations else 0,
        "average_score": statistics.mean(scores) if scores else None,
        "median_score": statistics.median(scores) if scores else None,
        "date_range": {
            "start": min([r.started_at for r in filtered_results]).isoformat() if filtered_results else None,
            "end": max([r.started_at for r in filtered_results]).isoformat() if filtered_results else None
        }
    }


@router.get("/suites/analytics", response_model=List[SuiteAnalytics])
async def get_suite_analytics(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get analytics for all test suites"""
    results = get_all_results()
    
    # Apply date filters
    if start_date:
        results = [r for r in results if r.started_at >= start_date]
    if end_date:
        results = [r for r in results if r.started_at <= end_date]
    
    # Group by suite
    suite_data = {}
    for result in results:
        if result.suite not in suite_data:
            suite_data[result.suite] = []
        suite_data[result.suite].append(result)
    
    analytics = []
    for suite, suite_results in suite_data.items():
        total_tests = len(set([r.test_id for r in suite_results]))
        total_runs = len(suite_results)
        passed = len([r for r in suite_results if r.status == ResultStatus.PASSED])
        
        durations = [r.duration for r in suite_results if r.duration is not None]
        scores = [r.score for r in suite_results if r.score is not None]
        
        # Find most common failures
        failures = [r for r in suite_results if r.status != ResultStatus.PASSED]
        failure_messages = {}
        for failure in failures:
            if failure.error_message:
                key = failure.error_message[:100]  # Truncate long messages
                failure_messages[key] = failure_messages.get(key, 0) + 1
        
        most_common_failures = [
            {"message": msg, "count": count}
            for msg, count in sorted(failure_messages.items(), key=lambda x: x[1], reverse=True)[:5]
        ]
        
        analytics.append(SuiteAnalytics(
            suite=suite,
            total_tests=total_tests,
            total_runs=total_runs,
            success_rate=(passed / total_runs * 100) if total_runs > 0 else 0,
            failure_rate=((total_runs - passed) / total_runs * 100) if total_runs > 0 else 0,
            average_duration=statistics.mean(durations) if durations else 0,
            average_score=statistics.mean(scores) if scores else None,
            most_common_failures=most_common_failures,
            trend={}  # TODO: Implement trend calculation
        ))
    
    # Sort by success rate (best first)
    analytics.sort(key=lambda x: x.success_rate, reverse=True)
    
    return analytics


@router.get("/tests/analytics", response_model=List[TestAnalytics])
async def get_test_analytics(
    suite: Optional[str] = None,
    limit: int = 50
):
    """Get analytics for individual tests"""
    results = get_all_results()
    
    # Filter by suite if specified
    if suite:
        results = [r for r in results if r.suite == suite]
    
    # Group by test_id
    test_data = {}
    for result in results:
        if result.test_id not in test_data:
            test_data[result.test_id] = []
        test_data[result.test_id].append(result)
    
    analytics = []
    for test_id, test_results in test_data.items():
        if not test_results:
            continue
            
        total_runs = len(test_results)
        passed = len([r for r in test_results if r.status == ResultStatus.PASSED])
        
        durations = [r.duration for r in test_results if r.duration is not None]
        scores = [r.score for r in test_results if r.score is not None]
        
        # Find last success and failure
        successes = [r for r in test_results if r.status == ResultStatus.PASSED]
        failures = [r for r in test_results if r.status != ResultStatus.PASSED]
        
        last_success = max([r.started_at for r in successes]) if successes else None
        last_failure = max([r.started_at for r in failures]) if failures else None
        
        # Determine trend (simple heuristic)
        recent_results = sorted(test_results, key=lambda x: x.started_at)[-5:]  # Last 5 runs
        recent_success_rate = len([r for r in recent_results if r.status == ResultStatus.PASSED]) / len(recent_results) if recent_results else 0
        overall_success_rate = passed / total_runs if total_runs > 0 else 0
        
        if recent_success_rate > overall_success_rate + 0.1:
            trend = "improving"
        elif recent_success_rate < overall_success_rate - 0.1:
            trend = "declining"
        else:
            trend = "stable"
        
        # Find failure patterns
        failure_patterns = []
        for failure in failures:
            if failure.error_message:
                pattern = failure.error_message.split()[0] if failure.error_message.split() else "Unknown"
                if pattern not in failure_patterns:
                    failure_patterns.append(pattern)
        
        analytics.append(TestAnalytics(
            test_id=test_id,
            test_name=test_results[0].test_name,
            suite=test_results[0].suite,
            total_runs=total_runs,
            success_rate=(passed / total_runs * 100) if total_runs > 0 else 0,
            average_duration=statistics.mean(durations) if durations else 0,
            average_score=statistics.mean(scores) if scores else None,
            best_score=max(scores) if scores else None,
            worst_score=min(scores) if scores else None,
            recent_trend=trend,
            failure_patterns=failure_patterns[:3],  # Top 3 patterns
            last_success=last_success,
            last_failure=last_failure
        ))
    
    # Sort by success rate (worst first for attention)
    analytics.sort(key=lambda x: x.success_rate)
    
    return analytics[:limit]


@router.get("/trends/{metric}")
async def get_trend_data(
    metric: str,
    period: AggregationPeriod = AggregationPeriod.DAY,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    suite: Optional[str] = None
):
    """Get trend data for a specific metric"""
    results = get_all_results()
    
    # Apply filters
    if start_date:
        results = [r for r in results if r.started_at >= start_date]
    if end_date:
        results = [r for r in results if r.started_at <= end_date]
    if suite:
        results = [r for r in results if r.suite == suite]
    
    # Default date range if not specified
    if not start_date:
        start_date = datetime.now() - timedelta(days=30)
    if not end_date:
        end_date = datetime.now()
    
    # Group results by time period
    def get_period_key(dt: datetime) -> str:
        if period == AggregationPeriod.HOUR:
            return dt.strftime("%Y-%m-%d %H:00")
        elif period == AggregationPeriod.DAY:
            return dt.strftime("%Y-%m-%d")
        elif period == AggregationPeriod.WEEK:
            # Get Monday of the week
            monday = dt - timedelta(days=dt.weekday())
            return monday.strftime("%Y-%m-%d")
        elif period == AggregationPeriod.MONTH:
            return dt.strftime("%Y-%m")
    
    grouped_data = {}
    for result in results:
        key = get_period_key(result.started_at)
        if key not in grouped_data:
            grouped_data[key] = []
        grouped_data[key].append(result)
    
    # Calculate metric values
    trend_data = []
    for period_key, period_results in sorted(grouped_data.items()):
        if metric == "success_rate":
            passed = len([r for r in period_results if r.status == ResultStatus.PASSED])
            value = (passed / len(period_results) * 100) if period_results else 0
        elif metric == "average_duration":
            durations = [r.duration for r in period_results if r.duration is not None]
            value = statistics.mean(durations) if durations else 0
        elif metric == "average_score":
            scores = [r.score for r in period_results if r.score is not None]
            value = statistics.mean(scores) if scores else 0
        elif metric == "test_count":
            value = len(period_results)
        else:
            value = 0
        
        # Convert period key back to datetime for response
        if period == AggregationPeriod.HOUR:
            timestamp = datetime.strptime(period_key, "%Y-%m-%d %H:00")
        elif period in [AggregationPeriod.DAY, AggregationPeriod.WEEK]:
            timestamp = datetime.strptime(period_key, "%Y-%m-%d")
        elif period == AggregationPeriod.MONTH:
            timestamp = datetime.strptime(period_key + "-01", "%Y-%m-%d")
        
        trend_data.append(TrendData(
            timestamp=timestamp,
            value=value,
            label=period_key
        ))
    
    return {
        "metric": metric,
        "period": period,
        "data": trend_data,
        "summary": {
            "min_value": min([d.value for d in trend_data]) if trend_data else 0,
            "max_value": max([d.value for d in trend_data]) if trend_data else 0,
            "average_value": statistics.mean([d.value for d in trend_data]) if trend_data else 0,
            "total_periods": len(trend_data)
        }
    }


@router.get("/failures/analysis")
async def get_failure_analysis(
    suite: Optional[str] = None,
    days: int = 7
):
    """Analyze test failures"""
    results = get_all_results()
    
    # Filter to recent failures
    cutoff_date = datetime.now() - timedelta(days=days)
    failures = [
        r for r in results 
        if r.started_at >= cutoff_date 
        and r.status != ResultStatus.PASSED
        and (not suite or r.suite == suite)
    ]
    
    if not failures:
        return {
            "total_failures": 0,
            "analysis_period_days": days,
            "failure_patterns": [],
            "most_failing_tests": [],
            "failure_distribution": {}
        }
    
    # Analyze failure patterns
    error_patterns = {}
    for failure in failures:
        if failure.error_message:
            # Extract pattern from error message
            words = failure.error_message.split()
            if words:
                pattern = words[0]  # First word as pattern
                if pattern not in error_patterns:
                    error_patterns[pattern] = {
                        "pattern": pattern,
                        "count": 0,
                        "tests": set(),
                        "example_message": failure.error_message
                    }
                error_patterns[pattern]["count"] += 1
                error_patterns[pattern]["tests"].add(failure.test_id)
    
    # Convert sets to lists for JSON serialization
    failure_patterns = []
    for pattern_data in error_patterns.values():
        failure_patterns.append({
            "pattern": pattern_data["pattern"],
            "count": pattern_data["count"],
            "affected_tests": len(pattern_data["tests"]),
            "example_message": pattern_data["example_message"]
        })
    
    failure_patterns.sort(key=lambda x: x["count"], reverse=True)
    
    # Find most failing tests
    test_failures = {}
    for failure in failures:
        if failure.test_id not in test_failures:
            test_failures[failure.test_id] = {
                "test_id": failure.test_id,
                "test_name": failure.test_name,
                "suite": failure.suite,
                "failure_count": 0,
                "last_failure": failure.started_at
            }
        test_failures[failure.test_id]["failure_count"] += 1
        if failure.started_at > test_failures[failure.test_id]["last_failure"]:
            test_failures[failure.test_id]["last_failure"] = failure.started_at
    
    most_failing_tests = list(test_failures.values())
    most_failing_tests.sort(key=lambda x: x["failure_count"], reverse=True)
    
    # Failure distribution by status
    failure_distribution = {}
    for failure in failures:
        status = failure.status.value
        failure_distribution[status] = failure_distribution.get(status, 0) + 1
    
    return {
        "total_failures": len(failures),
        "analysis_period_days": days,
        "failure_patterns": failure_patterns[:10],  # Top 10 patterns
        "most_failing_tests": most_failing_tests[:10],  # Top 10 failing tests
        "failure_distribution": failure_distribution,
        "suites_affected": len(set([f.suite for f in failures])),
        "tests_affected": len(set([f.test_id for f in failures]))
    }


@router.get("/performance/metrics")
async def get_performance_metrics(
    metric_name: str = "response_time",
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    suite: Optional[str] = None
):
    """Get performance metrics"""
    results = get_all_results()
    
    # Apply filters
    if start_date:
        results = [r for r in results if r.started_at >= start_date]
    if end_date:
        results = [r for r in results if r.started_at <= end_date]
    if suite:
        results = [r for r in results if r.suite == suite]
    
    metrics = []
    for result in results:
        if metric_name == "response_time" and result.duration is not None:
            metrics.append(PerformanceMetrics(
                metric="response_time",
                value=result.duration,
                unit="seconds",
                timestamp=result.started_at,
                test_id=result.test_id,
                run_id=result.run_id
            ))
        elif metric_name == "score" and result.score is not None:
            metrics.append(PerformanceMetrics(
                metric="score",
                value=result.score,
                unit="percentage",
                timestamp=result.started_at,
                test_id=result.test_id,
                run_id=result.run_id
            ))
    
    # Calculate statistics
    values = [m.value for m in metrics]
    stats = {
        "count": len(values),
        "min": min(values) if values else 0,
        "max": max(values) if values else 0,
        "mean": statistics.mean(values) if values else 0,
        "median": statistics.median(values) if values else 0,
        "std_dev": statistics.stdev(values) if len(values) > 1 else 0
    }
    
    return {
        "metric_name": metric_name,
        "statistics": stats,
        "data_points": len(metrics),
        "time_range": {
            "start": min([m.timestamp for m in metrics]).isoformat() if metrics else None,
            "end": max([m.timestamp for m in metrics]).isoformat() if metrics else None
        }
    }


@router.get("/export/{format}")
async def export_results(
    format: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    suite: Optional[str] = None
):
    """Export results in various formats"""
    if format not in ["json", "csv"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Use 'json' or 'csv'")
    
    results = get_all_results()
    
    # Apply filters
    filters = ResultsFilter(
        start_date=start_date,
        end_date=end_date,
        suites=[suite] if suite else []
    )
    filtered_results = filter_results(results, filters)
    
    if format == "json":
        return {
            "export_format": "json",
            "generated_at": datetime.now().isoformat(),
            "total_results": len(filtered_results),
            "results": [r.dict() for r in filtered_results]
        }
    elif format == "csv":
        # Convert to CSV-like structure
        csv_data = []
        for result in filtered_results:
            csv_data.append({
                "run_id": result.run_id,
                "test_id": result.test_id,
                "test_name": result.test_name,
                "suite": result.suite,
                "status": result.status,
                "success": result.success,
                "score": result.score,
                "duration": result.duration,
                "started_at": result.started_at.isoformat(),
                "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                "error_message": result.error_message
            })
        
        return {
            "export_format": "csv",
            "generated_at": datetime.now().isoformat(),
            "total_results": len(csv_data),
            "data": csv_data,
            "headers": list(csv_data[0].keys()) if csv_data else []
        }


@router.get("/stats/overview")
async def get_results_overview():
    """Get comprehensive results overview"""
    results = get_all_results()
    
    if not results:
        return {
            "total_results": 0,
            "suites": 0,
            "tests": 0,
            "runs": 0,
            "success_rate": 0,
            "recent_activity": {}
        }
    
    total_results = len(results)
    unique_suites = len(set([r.suite for r in results]))
    unique_tests = len(set([r.test_id for r in results]))
    unique_runs = len(set([r.run_id for r in results]))
    
    passed = len([r for r in results if r.status == ResultStatus.PASSED])
    success_rate = (passed / total_results * 100) if total_results > 0 else 0
    
    # Recent activity (last 24 hours)
    cutoff_24h = datetime.now() - timedelta(hours=24)
    recent_results = [r for r in results if r.started_at >= cutoff_24h]
    
    recent_activity = {
        "results_24h": len(recent_results),
        "success_rate_24h": (len([r for r in recent_results if r.status == ResultStatus.PASSED]) / len(recent_results) * 100) if recent_results else 0,
        "runs_24h": len(set([r.run_id for r in recent_results])),
        "tests_24h": len(set([r.test_id for r in recent_results]))
    }
    
    return {
        "total_results": total_results,
        "suites": unique_suites,
        "tests": unique_tests,
        "runs": unique_runs,
        "success_rate": success_rate,
        "recent_activity": recent_activity,
        "statistics": {
            "passed": len([r for r in results if r.status == ResultStatus.PASSED]),
            "failed": len([r for r in results if r.status == ResultStatus.FAILED]),
            "errors": len([r for r in results if r.status in [ResultStatus.ERROR, ResultStatus.TIMEOUT]]),
            "average_duration": statistics.mean([r.duration for r in results if r.duration is not None]) if any(r.duration for r in results) else 0
        }
    }


@router.get("/{job_id}/{run_id}/{test_id}/logs")
async def get_test_result_logs(job_id: str, run_id: str, test_id: str):
    """Get detailed logs for a specific test result"""
    if is_database_available():
        # Get test case logs from database
        logs_query = """
            SELECT tcl.request, tcl.response, tcl.server_logs, 
                   tcl.context_snapshot, tcl.performance_metrics,
                   tcl.validation_details
            FROM test_management.test_case_logs tcl
            JOIN test_management.results r ON tcl.result_id = r.id
            WHERE r.run_id = %(run_id)s AND r.test_id = %(test_id)s
            LIMIT 1
        """
        log_rows = await execute_query(logs_query, {'run_id': run_id, 'test_id': test_id})
        
        # Get execution logs
        exec_logs_query = """
            SELECT l.log_type, l.level, l.message, l.timestamp, l.metadata
            FROM test_management.logs l
            JOIN test_management.results r ON l.result_id = r.id
            WHERE r.run_id = %(run_id)s AND r.test_id = %(test_id)s
            ORDER BY l.timestamp
        """
        exec_log_rows = await execute_query(exec_logs_query, {'run_id': run_id, 'test_id': test_id})
        
        # Build response
        logs_data = {
            "test_id": test_id,
            "run_id": run_id,
            "job_id": job_id,
            "execution_logs": [
                {
                    "timestamp": log['timestamp'].isoformat() if log['timestamp'] else None,
                    "level": log['level'],
                    "type": log['log_type'],
                    "message": log['message'],
                    "metadata": log['metadata']
                }
                for log in exec_log_rows
            ]
        }
        
        # Add test case details if available
        if log_rows:
            log_data = log_rows[0]
            logs_data.update({
                "request": log_data['request'],
                "response": log_data['response'],
                "server_logs": log_data['server_logs'],
                "context_snapshot": log_data['context_snapshot'],
                "performance_metrics": log_data['performance_metrics'],
                "validation_details": log_data['validation_details']
            })
        else:
            # For mock data, create some sample logs
            logs_data.update({
                "server_logs": f"Mock server logs for test {test_id}\n[INFO] Test started\n[INFO] Processing request\n[INFO] Test completed",
                "execution_logs": [
                    {
                        "timestamp": datetime.now().isoformat(),
                        "level": "INFO",
                        "type": "execution",
                        "message": f"Starting test {test_id}",
                        "metadata": {}
                    },
                    {
                        "timestamp": (datetime.now() + timedelta(seconds=1)).isoformat(),
                        "level": "INFO",
                        "type": "execution",
                        "message": "Test execution completed",
                        "metadata": {"duration": "2.0s"}
                    }
                ],
                "request": {
                    "endpoint": "/v1/chat/completions",
                    "method": "POST",
                    "payload": {"messages": [{"role": "user", "content": "Test message"}]}
                },
                "response": {
                    "status": 200,
                    "data": {"choices": [{"message": {"content": "Test response"}}]}
                }
            })
        
        return logs_data
    else:
        # Return mock data for development
        return {
            "test_id": test_id,
            "run_id": run_id,
            "job_id": job_id,
            "server_logs": "Mock server logs (database not available)",
            "execution_logs": [],
            "request": {},
            "response": {}
        }