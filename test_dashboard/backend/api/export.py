"""
Export Functionality API
=========================

Handles data export in various formats (JSON, CSV, PDF, Excel)
and report generation for test results, analytics, and dashboards.
"""

import json
import csv
import io
import base64
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from fastapi import APIRouter, HTTPException, Response, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import zipfile
import tempfile
import os


# Enums
class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"
    EXCEL = "xlsx"
    XML = "xml"


class ReportType(str, Enum):
    SUMMARY = "summary"
    DETAILED = "detailed"
    ANALYTICS = "analytics"
    COMPARISON = "comparison"
    TRENDS = "trends"


# Pydantic models
class ExportRequest(BaseModel):
    """Export request configuration"""
    format: ExportFormat
    report_type: ReportType = ReportType.SUMMARY
    
    # Data filters
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    suites: List[str] = []
    test_ids: List[str] = []
    run_ids: List[str] = []
    
    # Export options
    include_logs: bool = False
    include_errors: bool = True
    include_metadata: bool = True
    compressed: bool = False
    
    # Report customization
    title: Optional[str] = None
    description: Optional[str] = None
    include_charts: bool = True
    include_trends: bool = True


class ExportJob(BaseModel):
    """Export job status"""
    id: str
    status: str  # "created", "processing", "completed", "failed"
    created_at: datetime
    completed_at: Optional[datetime] = None
    request: ExportRequest
    file_size: Optional[int] = None
    download_url: Optional[str] = None
    error_message: Optional[str] = None


class ReportSection(BaseModel):
    """Report section"""
    title: str
    content: Union[str, Dict[str, Any], List[Any]]
    section_type: str  # "text", "table", "chart", "summary"


class GeneratedReport(BaseModel):
    """Generated report structure"""
    title: str
    generated_at: datetime
    report_type: ReportType
    sections: List[ReportSection]
    metadata: Dict[str, Any]


# Create router
router = APIRouter()

# Import other modules for data access
from .results import get_all_results, filter_results, ResultsFilter
from .runs import runs_storage
from .jobs import jobs_storage

# In-memory storage for export jobs
export_jobs: Dict[str, ExportJob] = {}


def generate_export_id() -> str:
    """Generate unique export job ID"""
    import uuid
    return f"export_{uuid.uuid4().hex[:8]}"


def create_summary_report(data: Dict[str, Any], title: str = None) -> GeneratedReport:
    """Create a summary report"""
    title = title or "Test Results Summary Report"
    
    sections = [
        ReportSection(
            title="Executive Summary",
            content=f"This report provides a summary of test execution results for the period from {data.get('period', {}).get('start', 'N/A')} to {data.get('period', {}).get('end', 'N/A')}.",
            section_type="text"
        ),
        ReportSection(
            title="Overall Statistics",
            content={
                "Total Results": data.get("total_results", 0),
                "Success Rate": f"{data.get('success_rate', 0):.1f}%",
                "Average Duration": f"{data.get('average_duration', 0):.2f}s",
                "Total Suites": data.get("total_suites", 0),
                "Total Tests": data.get("total_tests", 0)
            },
            section_type="summary"
        )
    ]
    
    if "suite_breakdown" in data:
        sections.append(ReportSection(
            title="Suite Breakdown",
            content=data["suite_breakdown"],
            section_type="table"
        ))
    
    if "recent_trends" in data:
        sections.append(ReportSection(
            title="Recent Trends",
            content=data["recent_trends"],
            section_type="chart"
        ))
    
    return GeneratedReport(
        title=title,
        generated_at=datetime.now(),
        report_type=ReportType.SUMMARY,
        sections=sections,
        metadata={
            "export_version": "1.0",
            "data_points": data.get("total_results", 0),
            "generation_time": datetime.now().isoformat()
        }
    )


def create_detailed_report(results: List[Any], title: str = None) -> GeneratedReport:
    """Create a detailed report with all test results"""
    title = title or "Detailed Test Results Report"
    
    # Group results by suite
    suite_groups = {}
    for result in results:
        suite = result.suite if hasattr(result, 'suite') else result.get('suite', 'Unknown')
        if suite not in suite_groups:
            suite_groups[suite] = []
        suite_groups[suite].append(result)
    
    sections = [
        ReportSection(
            title="Report Overview",
            content=f"This detailed report contains {len(results)} test results across {len(suite_groups)} test suites.",
            section_type="text"
        )
    ]
    
    # Add section for each suite
    for suite, suite_results in suite_groups.items():
        passed = len([r for r in suite_results if getattr(r, 'success', r.get('success', False))])
        suite_success_rate = (passed / len(suite_results) * 100) if suite_results else 0
        
        sections.append(ReportSection(
            title=f"Suite: {suite}",
            content={
                "total_tests": len(suite_results),
                "passed": passed,
                "failed": len(suite_results) - passed,
                "success_rate": f"{suite_success_rate:.1f}%",
                "results": [
                    {
                        "test_id": getattr(r, 'test_id', r.get('test_id', 'Unknown')),
                        "test_name": getattr(r, 'test_name', r.get('test_name', 'Unknown')),
                        "status": getattr(r, 'status', r.get('status', 'Unknown')),
                        "duration": getattr(r, 'duration', r.get('duration', 0)),
                        "success": getattr(r, 'success', r.get('success', False)),
                        "error": getattr(r, 'error_message', r.get('error_message')) if not getattr(r, 'success', r.get('success', False)) else None
                    }
                    for r in suite_results
                ]
            },
            section_type="table"
        ))
    
    return GeneratedReport(
        title=title,
        generated_at=datetime.now(),
        report_type=ReportType.DETAILED,
        sections=sections,
        metadata={
            "total_results": len(results),
            "suites_covered": len(suite_groups),
            "generation_time": datetime.now().isoformat()
        }
    )


def export_to_json(data: Any, pretty: bool = True) -> str:
    """Export data to JSON format"""
    if pretty:
        return json.dumps(data, indent=2, default=str, ensure_ascii=False)
    else:
        return json.dumps(data, default=str, ensure_ascii=False)


def export_to_csv(data: List[Dict[str, Any]]) -> str:
    """Export data to CSV format"""
    if not data:
        return ""
    
    output = io.StringIO()
    
    # Get all possible field names
    fieldnames = set()
    for item in data:
        fieldnames.update(item.keys())
    fieldnames = sorted(list(fieldnames))
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for item in data:
        # Flatten nested objects for CSV
        flattened = {}
        for key, value in item.items():
            if isinstance(value, (dict, list)):
                flattened[key] = json.dumps(value, default=str)
            else:
                flattened[key] = value
        writer.writerow(flattened)
    
    return output.getvalue()


def export_to_xml(data: Any, root_name: str = "export") -> str:
    """Export data to XML format"""
    def dict_to_xml(d: Dict[str, Any], parent_name: str = "item") -> str:
        xml_str = f"<{parent_name}>"
        for key, value in d.items():
            safe_key = key.replace(" ", "_").replace("-", "_")
            if isinstance(value, dict):
                xml_str += dict_to_xml(value, safe_key)
            elif isinstance(value, list):
                xml_str += f"<{safe_key}>"
                for item in value:
                    if isinstance(item, dict):
                        xml_str += dict_to_xml(item, "item")
                    else:
                        xml_str += f"<item>{item}</item>"
                xml_str += f"</{safe_key}>"
            else:
                xml_str += f"<{safe_key}>{value}</{safe_key}>"
        xml_str += f"</{parent_name}>"
        return xml_str
    
    if isinstance(data, dict):
        return f'<?xml version="1.0" encoding="UTF-8"?>\n{dict_to_xml(data, root_name)}'
    elif isinstance(data, list):
        xml_content = ""
        for item in data:
            if isinstance(item, dict):
                xml_content += dict_to_xml(item, "item")
            else:
                xml_content += f"<item>{item}</item>"
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_name}>{xml_content}</{root_name}>'
    else:
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<{root_name}>{data}</{root_name}>'


@router.post("/", response_model=ExportJob)
async def create_export(export_request: ExportRequest, background_tasks: BackgroundTasks):
    """Create a new export job"""
    export_id = generate_export_id()
    
    export_job = ExportJob(
        id=export_id,
        status="created",
        created_at=datetime.now(),
        request=export_request
    )
    
    export_jobs[export_id] = export_job
    
    # Start processing in background
    background_tasks.add_task(process_export_job, export_id)
    
    return export_job


@router.get("/jobs", response_model=List[ExportJob])
async def list_export_jobs(limit: int = 50):
    """List export jobs"""
    jobs = list(export_jobs.values())
    jobs.sort(key=lambda x: x.created_at, reverse=True)
    return jobs[:limit]


@router.get("/jobs/{export_id}", response_model=ExportJob)
async def get_export_job(export_id: str):
    """Get specific export job status"""
    if export_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    return export_jobs[export_id]


@router.get("/jobs/{export_id}/download")
async def download_export(export_id: str):
    """Download completed export file"""
    if export_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = export_jobs[export_id]
    
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Export job not completed")
    
    if not job.download_url:
        raise HTTPException(status_code=404, detail="Export file not found")
    
    # In production, this would serve the actual file
    # For now, we'll return a mock response
    return {
        "download_url": job.download_url,
        "file_size": job.file_size,
        "export_id": export_id,
        "format": job.request.format,
        "generated_at": job.completed_at
    }


@router.delete("/jobs/{export_id}")
async def delete_export_job(export_id: str):
    """Delete an export job and its files"""
    if export_id not in export_jobs:
        raise HTTPException(status_code=404, detail="Export job not found")
    
    job = export_jobs[export_id]
    
    # In production, delete the actual file here
    if job.download_url:
        # os.remove(job.download_url)  # Uncomment in production
        pass
    
    del export_jobs[export_id]
    
    return {"message": f"Export job {export_id} deleted successfully"}


@router.get("/quick/{format}")
async def quick_export(
    format: ExportFormat,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    suite: Optional[str] = None,
    limit: int = 1000
):
    """Quick export without job queue for small datasets"""
    # Get results
    results = get_all_results()
    
    # Apply filters
    filters = ResultsFilter(
        start_date=start_date,
        end_date=end_date,
        suites=[suite] if suite else []
    )
    filtered_results = filter_results(results, filters)
    
    # Limit results for quick export
    filtered_results = filtered_results[:limit]
    
    # Convert to dict format
    data = [
        {
            "run_id": r.run_id,
            "test_id": r.test_id,
            "test_name": r.test_name,
            "suite": r.suite,
            "status": r.status,
            "success": r.success,
            "score": r.score,
            "duration": r.duration,
            "started_at": r.started_at.isoformat(),
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "error_message": r.error_message
        }
        for r in filtered_results
    ]
    
    # Export based on format
    if format == ExportFormat.JSON:
        content = export_to_json({
            "export_info": {
                "format": "json",
                "generated_at": datetime.now().isoformat(),
                "total_results": len(data),
                "filters_applied": filters.dict()
            },
            "results": data
        })
        media_type = "application/json"
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
    elif format == ExportFormat.CSV:
        content = export_to_csv(data)
        media_type = "text/csv"
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
    elif format == ExportFormat.XML:
        content = export_to_xml(data, "test_results")
        media_type = "application/xml"
        filename = f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        
    else:
        raise HTTPException(status_code=400, detail=f"Quick export not supported for format: {format}")
    
    # Return as streaming response
    return StreamingResponse(
        io.StringIO(content),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/reports/generate", response_model=GeneratedReport)
async def generate_report(
    report_type: ReportType,
    title: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    suites: List[str] = [],
    include_trends: bool = True
):
    """Generate a structured report"""
    # Get and filter results
    results = get_all_results()
    
    filters = ResultsFilter(
        start_date=start_date,
        end_date=end_date,
        suites=suites
    )
    filtered_results = filter_results(results, filters)
    
    if report_type == ReportType.SUMMARY:
        # Calculate summary statistics
        total_results = len(filtered_results)
        passed = len([r for r in filtered_results if r.success])
        success_rate = (passed / total_results * 100) if total_results > 0 else 0
        
        durations = [r.duration for r in filtered_results if r.duration is not None]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Suite breakdown
        suite_stats = {}
        for result in filtered_results:
            if result.suite not in suite_stats:
                suite_stats[result.suite] = {"total": 0, "passed": 0}
            suite_stats[result.suite]["total"] += 1
            if result.success:
                suite_stats[result.suite]["passed"] += 1
        
        suite_breakdown = [
            {
                "suite": suite,
                "total": stats["total"],
                "passed": stats["passed"],
                "success_rate": f"{(stats['passed'] / stats['total'] * 100):.1f}%"
            }
            for suite, stats in suite_stats.items()
        ]
        
        data = {
            "total_results": total_results,
            "success_rate": success_rate,
            "average_duration": avg_duration,
            "total_suites": len(suite_stats),
            "total_tests": len(set([r.test_id for r in filtered_results])),
            "suite_breakdown": suite_breakdown,
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }
        
        return create_summary_report(data, title)
        
    elif report_type == ReportType.DETAILED:
        return create_detailed_report(filtered_results, title)
        
    else:
        raise HTTPException(status_code=400, detail=f"Report type {report_type} not implemented")


@router.get("/templates")
async def list_export_templates():
    """List available export templates"""
    templates = [
        {
            "id": "daily_summary",
            "name": "Daily Summary Report",
            "description": "Summary of test results for the last 24 hours",
            "format": "json",
            "report_type": "summary",
            "default_filters": {
                "start_date": (datetime.now() - timedelta(days=1)).isoformat(),
                "end_date": datetime.now().isoformat()
            }
        },
        {
            "id": "weekly_detailed",
            "name": "Weekly Detailed Report",
            "description": "Detailed test results for the last 7 days",
            "format": "csv",
            "report_type": "detailed",
            "default_filters": {
                "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                "end_date": datetime.now().isoformat()
            }
        },
        {
            "id": "suite_analytics",
            "name": "Test Suite Analytics",
            "description": "Analytics and trends by test suite",
            "format": "json",
            "report_type": "analytics",
            "default_filters": {
                "start_date": (datetime.now() - timedelta(days=30)).isoformat(),
                "end_date": datetime.now().isoformat()
            }
        },
        {
            "id": "failure_analysis",
            "name": "Failure Analysis Report",
            "description": "Analysis of failed tests and error patterns",
            "format": "json",
            "report_type": "analytics",
            "default_filters": {
                "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
                "end_date": datetime.now().isoformat()
            }
        }
    ]
    
    return {"templates": templates}


@router.post("/templates/{template_id}")
async def export_from_template(template_id: str, overrides: Optional[Dict[str, Any]] = None):
    """Create export from template"""
    templates = {
        "daily_summary": ExportRequest(
            format=ExportFormat.JSON,
            report_type=ReportType.SUMMARY,
            start_date=datetime.now() - timedelta(days=1),
            end_date=datetime.now(),
            title="Daily Summary Report"
        ),
        "weekly_detailed": ExportRequest(
            format=ExportFormat.CSV,
            report_type=ReportType.DETAILED,
            start_date=datetime.now() - timedelta(days=7),
            end_date=datetime.now(),
            title="Weekly Detailed Report"
        ),
        "suite_analytics": ExportRequest(
            format=ExportFormat.JSON,
            report_type=ReportType.ANALYTICS,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now(),
            title="Test Suite Analytics Report"
        )
    }
    
    if template_id not in templates:
        raise HTTPException(status_code=404, detail="Template not found")
    
    export_request = templates[template_id]
    
    # Apply overrides
    if overrides:
        for key, value in overrides.items():
            if hasattr(export_request, key):
                setattr(export_request, key, value)
    
    # Create export job
    return await create_export(export_request, None)


async def process_export_job(export_id: str):
    """Background task to process export job"""
    if export_id not in export_jobs:
        return
    
    job = export_jobs[export_id]
    
    try:
        job.status = "processing"
        export_jobs[export_id] = job
        
        # Get and filter data
        results = get_all_results()
        
        filters = ResultsFilter(
            start_date=job.request.start_date,
            end_date=job.request.end_date,
            suites=job.request.suites,
            test_ids=job.request.test_ids,
            run_ids=job.request.run_ids
        )
        filtered_results = filter_results(results, filters)
        
        # Generate export content based on format and type
        if job.request.report_type == ReportType.SUMMARY:
            # Create summary data
            total_results = len(filtered_results)
            success_rate = (len([r for r in filtered_results if r.success]) / total_results * 100) if total_results > 0 else 0
            
            export_data = {
                "export_info": {
                    "id": export_id,
                    "generated_at": datetime.now().isoformat(),
                    "format": job.request.format,
                    "report_type": job.request.report_type,
                    "title": job.request.title or "Export Report"
                },
                "summary": {
                    "total_results": total_results,
                    "success_rate": success_rate,
                    "suites": len(set([r.suite for r in filtered_results])),
                    "tests": len(set([r.test_id for r in filtered_results]))
                },
                "results": [r.dict() for r in filtered_results] if job.request.format == ExportFormat.JSON else None
            }
        else:
            # Detailed export
            export_data = [r.dict() for r in filtered_results]
        
        # Convert to requested format
        if job.request.format == ExportFormat.JSON:
            content = export_to_json(export_data)
            file_extension = "json"
        elif job.request.format == ExportFormat.CSV:
            if isinstance(export_data, dict) and "results" in export_data:
                csv_data = export_data["results"]
            else:
                csv_data = export_data
            content = export_to_csv(csv_data)
            file_extension = "csv"
        elif job.request.format == ExportFormat.XML:
            content = export_to_xml(export_data)
            file_extension = "xml"
        else:
            raise ValueError(f"Unsupported format: {job.request.format}")
        
        # In production, save file to storage and return download URL
        # For now, we'll simulate this
        filename = f"export_{export_id}.{file_extension}"
        
        job.status = "completed"
        job.completed_at = datetime.now()
        job.file_size = len(content.encode('utf-8'))
        job.download_url = f"/api/export/jobs/{export_id}/download"
        
        export_jobs[export_id] = job
        
    except Exception as e:
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = datetime.now()
        export_jobs[export_id] = job


@router.get("/stats/overview")
async def get_export_stats():
    """Get export statistics"""
    jobs = list(export_jobs.values())
    
    stats = {
        "total_exports": len(jobs),
        "by_status": {
            "completed": len([j for j in jobs if j.status == "completed"]),
            "processing": len([j for j in jobs if j.status == "processing"]),
            "failed": len([j for j in jobs if j.status == "failed"]),
            "created": len([j for j in jobs if j.status == "created"])
        },
        "by_format": {
            "json": len([j for j in jobs if j.request.format == ExportFormat.JSON]),
            "csv": len([j for j in jobs if j.request.format == ExportFormat.CSV]),
            "pdf": len([j for j in jobs if j.request.format == ExportFormat.PDF]),
            "xml": len([j for j in jobs if j.request.format == ExportFormat.XML])
        },
        "recent_activity": {
            "exports_today": len([j for j in jobs if j.created_at.date() == datetime.now().date()]),
            "completed_today": len([j for j in jobs if j.completed_at and j.completed_at.date() == datetime.now().date()])
        }
    }
    
    return {"statistics": stats}