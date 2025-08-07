"""
Test Management API
===================

Handles test discovery, validation, catalog management, and test definitions.
"""

import os
import json
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field, validator
try:
    import jsonschema
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
import glob


# Pydantic models
class TestConfig(BaseModel):
    """Test configuration"""
    timeout: float = 30.0
    retries: int = 0
    parallel_safe: bool = True
    requirements: List[str] = []


class UserContext(BaseModel):
    """User context for test execution"""
    user_id: str = "test_user"
    profile: Dict[str, Any] = {}


class ConversationTurn(BaseModel):
    """Conversation turn for multi-turn tests"""
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class TestSetup(BaseModel):
    """Test setup configuration"""
    user_context: Optional[UserContext] = None
    previous_turns: List[ConversationTurn] = []
    environment: Dict[str, str] = {}


class TestExecution(BaseModel):
    """Test execution parameters"""
    endpoint: str
    method: str = "POST"
    headers: Dict[str, str] = {}
    payload: Dict[str, Any]


class ResponseExpectations(BaseModel):
    """Response validation expectations"""
    status_code: int = 200
    headers: Optional[Dict[str, str]] = None
    output_contains: List[str] = []
    output_excludes: List[str] = []
    output_regex: List[str] = []
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    custom_validators: List[str] = []


class ReasoningExpectations(BaseModel):
    """Reasoning validation expectations"""
    steps_min: Optional[int] = None
    steps_max: Optional[int] = None
    contains_keywords: List[str] = []
    excludes_keywords: List[str] = []
    tool_calls: List[str] = []
    tool_results_contain: Dict[str, Any] = {}


class AgentExpectations(BaseModel):
    """Agent interaction expectations"""
    touched: List[str] = []
    not_touched: List[str] = []
    call_order: List[str] = []
    max_agents: Optional[int] = None


class PerformanceExpectations(BaseModel):
    """Performance expectations"""
    response_time_max: Optional[float] = None
    memory_usage_max: Optional[str] = None
    token_usage_max: Optional[int] = None
    database_queries_max: Optional[int] = None


class TestExpectations(BaseModel):
    """All test expectations"""
    response: Optional[ResponseExpectations] = None
    reasoning: Optional[ReasoningExpectations] = None
    agents: Optional[AgentExpectations] = None
    performance: Optional[PerformanceExpectations] = None


class TestCleanup(BaseModel):
    """Test cleanup configuration"""
    commands: List[str] = []
    reset_context: bool = False


class TestDefinition(BaseModel):
    """Complete test definition"""
    id: str = Field(..., pattern="^[A-Z]{3}_\\d{3}$")
    name: str
    suite: str
    type: str = Field(..., pattern="^(single|multi_turn)$")
    priority: int = Field(default=3, ge=1, le=5)
    tags: List[str] = []
    config: TestConfig = TestConfig()
    setup: Optional[TestSetup] = None
    execution: TestExecution
    expectations: TestExpectations
    cleanup: Optional[TestCleanup] = None
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    author: str = "dashboard_user"
    version: str = "1.0"
    
    @validator('suite')
    def validate_suite(cls, v):
        valid_suites = [
            "appointment", "medical_consultation", "product", "identity", 
            "emergency", "multi_turn", "edge_case", "performance", "integration",
            "orchestrator", "streaming", "memory", "form", "workflow", "pattern2"
        ]
        if v not in valid_suites:
            raise ValueError(f"Suite must be one of: {', '.join(valid_suites)}")
        return v


class TestCatalogEntry(BaseModel):
    """Test catalog entry with metadata"""
    id: str
    name: str
    suite: str
    type: str
    priority: int
    tags: List[str]
    file_path: str
    size_bytes: int
    created_at: datetime
    updated_at: datetime
    checksum: Optional[str] = None
    valid: bool = True
    validation_errors: List[str] = []


class TestValidationResult(BaseModel):
    """Test validation result"""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    test_id: Optional[str] = None
    suite: Optional[str] = None


class TestDiscoveryResult(BaseModel):
    """Test discovery result"""
    total_files: int
    valid_tests: int
    invalid_tests: int
    new_tests: int
    updated_tests: int
    tests: List[TestCatalogEntry]
    errors: List[str] = []


class TestSearchFilter(BaseModel):
    """Test search and filter parameters"""
    suite: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[int] = None
    tags: List[str] = []
    search_term: Optional[str] = None
    valid_only: bool = True


# Create router
router = APIRouter()

# In-memory test catalog (in production, use database)
test_catalog: Dict[str, TestCatalogEntry] = {}
test_definitions: Dict[str, TestDefinition] = {}

# Load JSON schema for validation
import os
from pathlib import Path

# Get the repository root (4 levels up from backend/api/)
REPO_ROOT = Path(__file__).parent.parent.parent.parent
TEST_SCHEMA_PATH = str(REPO_ROOT / "test_definitions" / "test_schema.json")
test_schema = None

def load_test_schema():
    """Load the test JSON schema"""
    global test_schema
    try:
        if os.path.exists(TEST_SCHEMA_PATH):
            with open(TEST_SCHEMA_PATH, 'r') as f:
                test_schema = json.load(f)
        else:
            # Fallback minimal schema
            test_schema = {
                "type": "object",
                "required": ["id", "name", "suite", "type", "execution", "expectations"],
                "properties": {
                    "id": {"type": "string", "pattern": "^[A-Z]{3}_\\d{3}$"},
                    "name": {"type": "string"},
                    "suite": {"type": "string"},
                    "type": {"type": "string", "enum": ["single", "multi_turn"]},
                    "execution": {"type": "object"},
                    "expectations": {"type": "object"}
                }
            }
    except Exception as e:
        print(f"Failed to load test schema: {e}")
        test_schema = {"type": "object"}

# Load schema on startup
load_test_schema()


def validate_test_definition(test_data: Dict[str, Any]) -> TestValidationResult:
    """Validate test definition against schema"""
    errors = []
    warnings = []
    
    try:
        # JSON schema validation
        if test_schema and JSONSCHEMA_AVAILABLE:
            jsonschema.validate(test_data, test_schema)
        
        # Pydantic model validation
        test_def = TestDefinition(**test_data)
        
        # Additional business logic validation
        if test_def.config.timeout > 300:
            warnings.append("Timeout > 300 seconds may cause job failures")
        
        if test_def.type == "multi_turn" and not test_def.setup:
            warnings.append("Multi-turn tests should have setup with previous_turns")
        
        if not test_def.expectations.response and not test_def.expectations.reasoning:
            warnings.append("Test has no response or reasoning expectations")
        
        return TestValidationResult(
            valid=True,
            errors=errors,
            warnings=warnings,
            test_id=test_def.id,
            suite=test_def.suite
        )
        
    except Exception as e:
        # Handle jsonschema ValidationError if available
        if JSONSCHEMA_AVAILABLE and "ValidationError" in str(type(e)):
            errors.append(f"Schema validation error: {str(e)}")
        else:
            errors.append(f"Validation error: {str(e)}")
    
    return TestValidationResult(
        valid=False,
        errors=errors,
        warnings=warnings
    )


async def discover_test_files(directory: str = None) -> List[str]:
    """Discover test definition files"""
    if not directory:
        directory = str(REPO_ROOT / "test_definitions")
    
    test_files = []
    
    if os.path.exists(directory):
        # Find all JSON files recursively
        pattern = os.path.join(directory, "**", "*.json")
        test_files = glob.glob(pattern, recursive=True)
        
        # Filter out schema files and non-test files
        test_files = [f for f in test_files if not f.endswith('test_schema.json')]
        test_files = [f for f in test_files if not f.endswith('conversion_summary.json')]
    
    return test_files


async def load_test_definitions(file_path: str) -> List[TestDefinition]:
    """Load and validate test definitions from file (supports single test or array)"""
    test_defs = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle different file formats
        tests_to_process = []
        
        if isinstance(data, list):
            # Direct array of tests
            tests_to_process = data
        elif isinstance(data, dict):
            if 'tests' in data:
                # File with metadata and tests array
                tests_to_process = data['tests']
            else:
                # Single test object
                tests_to_process = [data]
        
        file_ctime = datetime.fromtimestamp(os.path.getctime(file_path))
        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
        
        for test_data in tests_to_process:
            if not test_data:
                continue
                
            validation = validate_test_definition(test_data)
            if validation.valid:
                test_def = TestDefinition(**test_data)
                test_def.created_at = test_def.created_at or file_ctime
                test_def.updated_at = test_def.updated_at or file_mtime
                test_defs.append(test_def)
            else:
                print(f"Invalid test in {file_path}: {validation.errors}")
                
    except Exception as e:
        print(f"Failed to load test definitions from {file_path}: {e}")
        
    return test_defs


@router.get("/", response_model=List[TestCatalogEntry])
@router.get("", response_model=List[TestCatalogEntry])
async def list_tests(
    suite: Optional[str] = None,
    type: Optional[str] = None,
    priority: Optional[int] = None,
    tags: Optional[str] = None,
    search: Optional[str] = None,
    valid_only: bool = True,
    limit: int = 100,
    offset: int = 0
):
    """List tests with filtering and pagination"""
    tests = list(test_catalog.values())
    
    # Apply filters
    if suite:
        tests = [t for t in tests if t.suite == suite]
    if type:
        tests = [t for t in tests if t.type == type]
    if priority:
        tests = [t for t in tests if t.priority == priority]
    if tags:
        tag_list = [t.strip() for t in tags.split(',')]
        tests = [t for t in tests if any(tag in t.tags for tag in tag_list)]
    if search:
        search_lower = search.lower()
        tests = [t for t in tests if search_lower in t.name.lower() or search_lower in t.id.lower()]
    if valid_only:
        tests = [t for t in tests if t.valid]
    
    # Sort by suite, then priority, then name
    tests.sort(key=lambda x: (x.suite, -x.priority, x.name))
    
    # Apply pagination
    return tests[offset:offset + limit]


@router.get("/{test_id}", response_model=TestDefinition)
async def get_test(test_id: str):
    """Get specific test definition"""
    if test_id not in test_definitions:
        raise HTTPException(status_code=404, detail="Test not found")
    
    return test_definitions[test_id]


@router.post("/validate", response_model=TestValidationResult)
async def validate_test(test_data: Dict[str, Any]):
    """Validate a test definition"""
    return validate_test_definition(test_data)


@router.post("/", response_model=TestDefinition)
async def create_test(test_def: TestDefinition):
    """Create a new test definition"""
    # Check if test ID already exists
    if test_def.id in test_definitions:
        raise HTTPException(status_code=400, detail="Test ID already exists")
    
    # Set timestamps
    now = datetime.now()
    test_def.created_at = now
    test_def.updated_at = now
    
    # Store in memory
    test_definitions[test_def.id] = test_def
    
    # Create catalog entry
    catalog_entry = TestCatalogEntry(
        id=test_def.id,
        name=test_def.name,
        suite=test_def.suite,
        type=test_def.type,
        priority=test_def.priority,
        tags=test_def.tags,
        file_path=f"memory://{test_def.id}",
        size_bytes=len(json.dumps(test_def.dict())),
        created_at=now,
        updated_at=now,
        valid=True,
        validation_errors=[]
    )
    test_catalog[test_def.id] = catalog_entry
    
    return test_def


@router.put("/{test_id}", response_model=TestDefinition)
async def update_test(test_id: str, test_def: TestDefinition):
    """Update an existing test definition"""
    if test_id not in test_definitions:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Ensure ID matches
    if test_def.id != test_id:
        raise HTTPException(status_code=400, detail="Test ID in URL and body must match")
    
    # Preserve creation time, update modification time
    original = test_definitions[test_id]
    test_def.created_at = original.created_at
    test_def.updated_at = datetime.now()
    
    # Store updated definition
    test_definitions[test_id] = test_def
    
    # Update catalog entry
    if test_id in test_catalog:
        catalog_entry = test_catalog[test_id]
        catalog_entry.name = test_def.name
        catalog_entry.suite = test_def.suite
        catalog_entry.type = test_def.type
        catalog_entry.priority = test_def.priority
        catalog_entry.tags = test_def.tags
        catalog_entry.updated_at = test_def.updated_at
        catalog_entry.size_bytes = len(json.dumps(test_def.dict()))
    
    return test_def


@router.delete("/{test_id}")
async def delete_test(test_id: str):
    """Delete a test definition"""
    if test_id not in test_definitions:
        raise HTTPException(status_code=404, detail="Test not found")
    
    del test_definitions[test_id]
    if test_id in test_catalog:
        del test_catalog[test_id]
    
    return {"message": f"Test {test_id} deleted successfully"}


@router.post("/discover", response_model=TestDiscoveryResult)
async def discover_tests(directory: Optional[str] = None, force_reload: bool = False):
    """Discover and load test definitions from files"""
    test_files = await discover_test_files(directory)
    
    total_files = len(test_files)
    valid_tests = 0
    invalid_tests = 0
    new_tests = 0
    updated_tests = 0
    errors = []
    discovered_tests = []
    
    for file_path in test_files:
        try:
            # Check if already loaded (unless force reload)
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
            
            # Skip if file hasn't changed (unless force reload)
            # For multi-test files, we can't easily check individual tests
            # so we'll process the whole file if it's been modified
            if not force_reload:
                # Check if any tests from this file are already loaded
                existing_from_file = [entry for entry in test_catalog.values() 
                                     if entry.file_path == file_path]
                if existing_from_file and all(e.updated_at >= file_mtime for e in existing_from_file):
                    discovered_tests.extend(existing_from_file)
                    valid_tests += len(existing_from_file)
                    continue
            
            # Load test definitions (may be multiple per file)
            test_defs = await load_test_definitions(file_path)
            
            if test_defs:
                for test_def in test_defs:
                    valid_tests += 1
                    
                    # Check if new or updated
                    if test_def.id not in test_definitions:
                        new_tests += 1
                    else:
                        updated_tests += 1
                    
                    # Store definition
                    test_definitions[test_def.id] = test_def
                    
                    # Create catalog entry
                    catalog_entry = TestCatalogEntry(
                        id=test_def.id,
                        name=test_def.name,
                        suite=test_def.suite,
                        type=test_def.type,
                        priority=test_def.priority,
                        tags=test_def.tags,
                        file_path=file_path,
                        size_bytes=file_size,
                        created_at=test_def.created_at or datetime.fromtimestamp(file_stat.st_ctime),
                        updated_at=test_def.updated_at or file_mtime,
                        valid=True,
                        validation_errors=[]
                    )
                    test_catalog[test_def.id] = catalog_entry
                    discovered_tests.append(catalog_entry)
            else:
                # No valid tests in file
                invalid_tests += 1
                errors.append(f"No valid tests found in {file_path}")
                
        except Exception as e:
            invalid_tests += 1
            errors.append(f"Error processing {file_path}: {str(e)}")
    
    return TestDiscoveryResult(
        total_files=total_files,
        valid_tests=valid_tests,
        invalid_tests=invalid_tests,
        new_tests=new_tests,
        updated_tests=updated_tests,
        tests=discovered_tests,
        errors=errors
    )


@router.get("/suites/list")
async def list_test_suites():
    """List all available test suites"""
    suites = {}
    
    for test in test_catalog.values():
        if test.suite not in suites:
            suites[test.suite] = {
                "name": test.suite,
                "count": 0,
                "types": set(),
                "priorities": set()
            }
        
        suites[test.suite]["count"] += 1
        suites[test.suite]["types"].add(test.type)
        suites[test.suite]["priorities"].add(test.priority)
    
    # Convert sets to lists for JSON serialization
    for suite_data in suites.values():
        suite_data["types"] = list(suite_data["types"])
        suite_data["priorities"] = list(suite_data["priorities"])
    
    return {
        "suites": list(suites.values()),
        "total_suites": len(suites)
    }


@router.get("/stats/overview")
async def get_tests_overview():
    """Get test catalog overview statistics"""
    tests = list(test_catalog.values())
    
    stats = {
        "total_tests": len(tests),
        "valid_tests": len([t for t in tests if t.valid]),
        "invalid_tests": len([t for t in tests if not t.valid]),
        "by_suite": {},
        "by_type": {
            "single": len([t for t in tests if t.type == "single"]),
            "multi_turn": len([t for t in tests if t.type == "multi_turn"])
        },
        "by_priority": {
            "1": len([t for t in tests if t.priority == 1]),
            "2": len([t for t in tests if t.priority == 2]),
            "3": len([t for t in tests if t.priority == 3]),
            "4": len([t for t in tests if t.priority == 4]), 
            "5": len([t for t in tests if t.priority == 5])
        },
        "recent_activity": {
            "created_today": len([t for t in tests if t.created_at.date() == datetime.now().date()]),
            "updated_today": len([t for t in tests if t.updated_at.date() == datetime.now().date()])
        }
    }
    
    # Calculate by suite
    for test in tests:
        if test.suite not in stats["by_suite"]:
            stats["by_suite"][test.suite] = 0
        stats["by_suite"][test.suite] += 1
    
    return {"statistics": stats}


@router.post("/upload")
async def upload_test_file(file: UploadFile = File(...)):
    """Upload and process a test definition file"""
    if not file.filename.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files are supported")
    
    try:
        content = await file.read()
        data = json.loads(content.decode('utf-8'))
        
        # Handle single test or array of tests
        if isinstance(data, list):
            results = []
            for test_data in data:
                validation = validate_test_definition(test_data)
                results.append(validation)
                
                if validation.valid:
                    test_def = TestDefinition(**test_data)
                    test_def.created_at = datetime.now()
                    test_def.updated_at = datetime.now()
                    test_definitions[test_def.id] = test_def
                    
                    # Create catalog entry
                    catalog_entry = TestCatalogEntry(
                        id=test_def.id,
                        name=test_def.name,
                        suite=test_def.suite,
                        type=test_def.type,
                        priority=test_def.priority,
                        tags=test_def.tags,
                        file_path=f"upload://{file.filename}",
                        size_bytes=len(content),
                        created_at=test_def.created_at,
                        updated_at=test_def.updated_at,
                        valid=True,
                        validation_errors=[]
                    )
                    test_catalog[test_def.id] = catalog_entry
            
            return {
                "message": f"Processed {len(data)} tests from {file.filename}",
                "results": results
            }
        else:
            # Single test
            validation = validate_test_definition(data)
            if validation.valid:
                test_def = TestDefinition(**data)
                test_def.created_at = datetime.now()
                test_def.updated_at = datetime.now()
                test_definitions[test_def.id] = test_def
                
                # Create catalog entry
                catalog_entry = TestCatalogEntry(
                    id=test_def.id,
                    name=test_def.name,
                    suite=test_def.suite,
                    type=test_def.type,
                    priority=test_def.priority,
                    tags=test_def.tags,
                    file_path=f"upload://{file.filename}",
                    size_bytes=len(content),
                    created_at=test_def.created_at,
                    updated_at=test_def.updated_at,
                    valid=True,
                    validation_errors=[]
                )
                test_catalog[test_def.id] = catalog_entry
                
                return {
                    "message": f"Successfully uploaded test {test_def.id}",
                    "test_id": test_def.id,
                    "validation": validation
                }
            else:
                raise HTTPException(status_code=400, detail=f"Invalid test definition: {validation.errors}")
                
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process file: {str(e)}")


# Initialize with discovery on startup
@router.on_event("startup")
async def startup_discover_tests():
    """Discover tests on startup"""
    try:
        await discover_tests()
        print(f"Discovered {len(test_catalog)} tests on startup")
    except Exception as e:
        print(f"Failed to discover tests on startup: {e}")