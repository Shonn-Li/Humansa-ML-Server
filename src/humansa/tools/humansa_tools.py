"""
Humansa Agentic Tools Manager with Real Database Integration

Provides fully agentic tool execution using LlamaIndex FunctionTool.from_defaults
with Pydantic schemas for ALL tool arguments. NO heuristic argument extraction.

All business/safety rules are enforced in the system prompt and post-processing,
NOT in the tool code. Tools are pure functions that expect structured arguments.

All read operations use real PostgreSQL database. Booking operations are simulated
(non-writing) to prevent actual data modification during agent testing.
"""

from ..postgres.database import db
import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
import os
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Import web search processor for real web search
try:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from chat.websearch.web_search_processor import WebSearchProcessor
    WEB_SEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"WebSearchProcessor not available: {e}")
    WEB_SEARCH_AVAILABLE = False

# Import our database utility
from ..postgres.database import db

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    logger.warning("psycopg2 not available - database functions may not work")
    DB_AVAILABLE = False

# LlamaIndex imports for agentic tools
try:
    from llama_index.core.tools import FunctionTool
    from llama_index.core.llms import LLM
    from llama_index.llms.openai import OpenAI
    try:
        from llama_index.llms.azure_openai import AzureOpenAI
    except ImportError:
        AzureOpenAI = None
    from llama_index.core.callbacks import CallbackManager, CBEventType
    from llama_index.core.callbacks.base import BaseCallbackHandler
    from llama_index.core import Settings
    LLAMAINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not fully available: {e}")
    LLAMAINDEX_AVAILABLE = False
    # Fallback definitions

    class BaseCallbackHandler:
        def __init__(self, *args, **kwargs):
            pass


# ====== PYDANTIC SCHEMAS FOR STRUCTURED TOOL ARGUMENTS ======

class DoctorSearchArgs(BaseModel):
    """Arguments for finding doctor information with intelligent fuzzy matching."""
    name: Optional[str] = Field(
        None, description="Doctor's actual Chinese family name or personal name (e.g., '张', '王', '李明'). Do NOT include titles like '医生', '主任', 'Dr.', etc. Use only the actual name for searching. Supports fuzzy matching - even single characters will find relevant doctors. If no specific name, returns top 5 available doctors.")
    specialty: Optional[str] = Field(
        None, description="Medical specialty (e.g., 'cardiology', '心内科', '儿科'). Helps filter doctors by department. If no matches, returns doctors from all specialties.")
    city: Optional[str] = Field(
        None, description="City name (e.g., 'Beijing', '北京', 'Shanghai'). Helps filter doctors by location. If no matches, returns doctors from all locations.")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")


class DoctorAvailabilityArgs(BaseModel):
    """Arguments for checking doctor availability with flexible date range support."""
    doctor_name: str = Field(..., description="Doctor's actual Chinese family name or personal name (e.g., '张', '王', '李明'). Do NOT include titles like '医生', '主任', 'Dr.', etc. Use only the actual name for searching. Supports fuzzy matching - even partial names will find relevant doctors.")
    start_date: Optional[str] = Field(None, description="Start date for availability search in ISO format (YYYY-MM-DD). If not provided, defaults to today.")
    end_date: Optional[str] = Field(None, description="End date for availability search in ISO format (YYYY-MM-DD). If not provided, defaults to 30 days from start_date. Maximum range is 30 days.")
    specialty: Optional[str] = Field(None, description="Medical specialty filter (optional). Helps narrow down search when doctor name is ambiguous.")
    days_ahead: Optional[int] = Field(None, description="Alternative to date range: number of days ahead to search (1-30). Use this for requests like 'next week' (7), 'this month' (30), etc.")

    @validator('start_date')
    def validate_start_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('Start date must be in YYYY-MM-DD format')
        return v

    @validator('end_date')
    def validate_end_date(cls, v):
        if v:
            try:
                datetime.strptime(v, '%Y-%m-%d')
                return v
            except ValueError:
                raise ValueError('End date must be in YYYY-MM-DD format')
        return v

    @validator('days_ahead')
    def validate_days_ahead(cls, v):
        if v is not None:
            if not isinstance(v, int) or v < 1 or v > 30:
                raise ValueError('days_ahead must be an integer between 1 and 30')
        return v


class PricingArgs(BaseModel):
    """Arguments for getting service pricing with intelligent fallback."""
    service_type: str = Field(..., description="Type of medical service (e.g., '体检', '心脏检查', 'consultation'). Supports fuzzy matching - even partial terms will find relevant services.")
    clinic_name: Optional[str] = Field(None, description="Specific clinic name (optional). Supports fuzzy matching. If not found, returns pricing from all available clinics.")
    specialty: Optional[str] = Field(None, description="Medical specialty filter (optional). Helps narrow down pricing when service type is broad.")
    currency: str = Field("CNY", description="Currency for pricing")


class ClinicSearchArgs(BaseModel):
    """Arguments for searching available clinics with intelligent matching."""
    clinic_name: Optional[str] = Field(None, description="Clinic name to search for. Supports fuzzy matching - even partial names will find relevant clinics. If not provided, returns top 5 available clinics.")
    city: Optional[str] = Field(None, description="City or location filter (optional). Helps narrow down clinics by location.")
    specialty: Optional[str] = Field(None, description="Medical specialty offered at clinic (optional). Helps find clinics that offer specific services.")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")


class ServiceSearchArgs(BaseModel):
    """Arguments for searching available medical services with intelligent matching."""
    service_name: Optional[str] = Field(None, description="Medical service to search for (e.g., '体检', '心脏检查', 'MRI'). Supports fuzzy matching - even partial terms will find relevant services.")
    specialty: Optional[str] = Field(None, description="Medical specialty filter (optional). Helps narrow down services by department.")
    clinic_name: Optional[str] = Field(None, description="Specific clinic filter (optional). Shows services available at specific clinic.")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")


class BookingArgs(BaseModel):
    """Arguments for booking appointments."""
    doctor_name: str = Field(..., description="Doctor's actual Chinese family name or personal name (e.g., '张', '王', '李明'). Do NOT include titles like '医生', '主任', 'Dr.', etc. Use only the actual name.")
    date_iso: str = Field(..., description="Appointment date (YYYY-MM-DD)")
    time_hhmm: str = Field(...,
                           description="Appointment time (HH:MM, 24-hour format)")
    patient_name: str = Field(..., description="Patient's full name")
    phone: str = Field(..., description="Patient's phone number")
    service_type: str = Field(..., description="Type of medical service")

    @validator('date_iso')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

    @validator('time_hhmm')
    def validate_time(cls, v):
        try:
            datetime.strptime(v, '%H:%M')
            return v
        except ValueError:
            raise ValueError('Time must be in HH:MM format')


class CallArgs(BaseModel):
    """Arguments for placing calls."""
    phone_number: str = Field(..., description="Phone number to call")
    purpose: str = Field(..., description="Purpose of the call")
    urgency: str = Field(
        "normal", description="Urgency level: 'normal', 'urgent', 'emergency'")


class ProductRecommendationArgs(BaseModel):
    """Arguments for recommending products."""
    product_category: str = Field(...,
                                  description="Category of product to recommend")
    reason: str = Field(..., description="Reason for recommendation")
    price_range: Optional[str] = Field(
        None, description="Preferred price range")


class ContentPushArgs(BaseModel):
    """Arguments for pushing content."""
    content_type: str = Field(...,
                              description="Type of content: 'article', 'video', 'post'")
    topic: str = Field(..., description="Content topic")
    target_audience: str = Field(..., description="Target audience")


class SearchArgs(BaseModel):
    """Arguments for search operations."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Search category")
    language: str = Field("zh", description="Search language: 'zh' or 'en'")


class ClinicSearchArgs(BaseModel):
    """Arguments for searching clinic information."""
    name: Optional[str] = Field(
        None, description="Clinic name or partial name (e.g., '仁和', '北京医院'). Supports fuzzy matching.")
    city: Optional[str] = Field(
        None, description="City or area name (e.g., 'Beijing', '北京', '朝阳区')")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")


class ServiceSearchArgs(BaseModel):
    """Arguments for searching medical services."""
    service_name: Optional[str] = Field(
        None, description="Medical service name or type (e.g., '体检', 'checkup', '心电图'). Supports fuzzy matching.")
    clinic_name: Optional[str] = Field(
        None, description="Clinic name to filter services by")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")


# ====== CALLBACK HANDLER FOR OBSERVABILITY ======

class ReActTraceHandler(BaseCallbackHandler):
    """
    Captures every 'Thought / Action / Observation' chunk that the ReAct agent
    streams while it plans, so we can replay the full chain-of-thought later.
    """
    def __init__(self):
        super().__init__([], [])
        self.trace: List[str] = []
        self.current_observation = None

    def on_event_start(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        """Required abstract method - we don't need to capture start events for trace"""
        return kwargs.get('event_id', f"trace_event_{len(self.trace)}")

    def on_event_end(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        if event_type == CBEventType.LLM:
            # The raw text the LLM just produced
            txt = payload.get("response", "") if payload else ""
            if hasattr(txt, 'message') and hasattr(txt.message, 'content'):
                txt = txt.message.content
            elif hasattr(txt, 'content'):
                txt = txt.content
            else:
                txt = str(txt)
            
            # Only keep the parts that look like ReAct lines
            if any(t in txt for t in ("Thought:", "Action:", "Observation:", "Answer:")):
                self.trace.append(txt)
                logger.info(f"🧠 TRACE CAPTURED: {txt[:100]}...")
        
        elif event_type == CBEventType.FUNCTION_CALL:
            # This captures function calls and their results
            if payload:
                tool_name = payload.get("function_call", {}).get("name", "unknown_tool")
                tool_args = payload.get("function_call", {}).get("arguments", {})
                tool_result = payload.get("function_call_response", "")
                
                # Create observation text
                observation_text = f"Observation: {tool_result}"
                self.trace.append(observation_text)
                logger.info(f"🔍 OBSERVATION CAPTURED: {observation_text[:100]}...")
        
        elif event_type == CBEventType.AGENT_STEP:
            # This might capture agent steps including observations
            if payload:
                step_output = payload.get("response", "")
                if step_output and "Observation:" in str(step_output):
                    self.trace.append(str(step_output))
                    logger.info(f"🤖 AGENT STEP CAPTURED: {str(step_output)[:100]}...")

    def get_trace(self) -> str:
        """Get the full reasoning trace."""
        return "\n".join(self.trace)

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a new trace."""
        pass

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, List[str]]] = None) -> None:
        """End a trace."""
        pass


class HumansaCallbackHandler(BaseCallbackHandler):
    """Callback handler to observe all tool calls and events."""

    def __init__(self):
        super().__init__([], [])
        self.tool_calls = []
        self.events = []

    def on_event_start(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> str:
        event_id = kwargs.get('event_id', f"event_{len(self.events)}")
        event_data = {
            'event_id': event_id,
            'event_type': str(event_type),
            'payload': payload or {},
            'timestamp': datetime.now().isoformat(),
            'phase': 'start'
        }
        self.events.append(event_data)

        # Specifically capture tool calls
        if event_type == CBEventType.FUNCTION_CALL:
            tool_call = {
                'event_id': event_id,
                'tool_name': payload.get('function_call_name', 'unknown'),
                'arguments': payload.get('function_call_kwargs', {}),
                'timestamp': datetime.now().isoformat()
            }
            self.tool_calls.append(tool_call)
            logger.info(
                f"🔧 TOOL CALL OBSERVED: {tool_call['tool_name']} with args: {tool_call['arguments']}")

        return event_id

    def on_event_end(self, event_type: CBEventType, payload: Optional[Dict[str, Any]] = None, **kwargs) -> None:
        event_id = kwargs.get('event_id', 'unknown')
        event_data = {
            'event_id': event_id,
            'event_type': str(event_type),
            'payload': payload or {},
            'timestamp': datetime.now().isoformat(),
            'phase': 'end'
        }
        self.events.append(event_data)

        # Update tool call with result
        if event_type == CBEventType.FUNCTION_CALL:
            for tool_call in self.tool_calls:
                if tool_call['event_id'] == event_id:
                    tool_call['result'] = payload.get(
                        'function_call_response', 'unknown')
                    tool_call['completed'] = True
                    logger.info(
                        f"✅ TOOL CALL COMPLETED: {tool_call['tool_name']}")
                    break

    def get_tool_calls(self) -> List[Dict]:
        """Get all observed tool calls."""
        return self.tool_calls.copy()

    def get_events(self) -> List[Dict]:
        """Get all observed events."""
        return self.events.copy()

    def start_trace(self, trace_id: Optional[str] = None) -> None:
        """Start a new trace."""
        pass

    def end_trace(self, trace_id: Optional[str] = None, trace_map: Optional[Dict[str, List[str]]] = None) -> None:
        """End a trace."""
        pass


class HumansaAgenticToolManager:
    """
    Fully Agentic Tool Manager for Humansa AI-Agent.

    ALL tool arguments are structured using Pydantic schemas.
    NO heuristic argument extraction or business logic in tools.
    Business rules enforced in system prompt and post-processing.
    """

    def __init__(self, db_config: Optional[Dict] = None):
        """Initialize the agentic tool manager."""
        self.db_config = db_config or {}
        self.llm = None
        self.trace_handler = ReActTraceHandler()
        self.callback_handler = HumansaCallbackHandler()
        self.callback_manager = CallbackManager([self.callback_handler, self.trace_handler])

        # Initialize database connection
        self._initialize_database()

        # Initialize LLM
        self._initialize_llm()

        # Set global callback manager
        if LLAMAINDEX_AVAILABLE:
            Settings.callback_manager = self.callback_manager

        logger.info(
            "🛠️ HumansaAgenticToolManager initialized with structured schemas")
        logger.info("📊 CallbackManager configured for tool call observability")

    def _initialize_database(self):
        """Initialize database connection."""
        try:
            # Test database connection using health check
            if db.health_check():
                logger.info("✅ Database connection verified")
            else:
                logger.warning("⚠️ Database connection test failed")
        except Exception as e:
            logger.warning(f"⚠️ Database initialization failed: {e}")

    def _initialize_llm(self):
        """Initialize the LLM for the agentic tools."""
        try:
            # Try Azure OpenAI first
            if AzureOpenAI and os.getenv("AZURE_OPENAI_API_KEY"):
                self.llm = AzureOpenAI(
                    engine=os.getenv(
                        "AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-nano"),
                    model=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4.1-nano"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_version=os.getenv(
                        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
                    temperature=0.1,
                    callback_manager=self.callback_manager
                )
                logger.info("🔵 Azure OpenAI LLM initialized for agentic tools")
            # Fall back to OpenAI
            elif os.getenv("OPENAI_API_KEY"):
                self.llm = OpenAI(
                    model="gpt-4.1-nano",
                    api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.1,
                    callback_manager=self.callback_manager
                )
                logger.info("🟢 OpenAI LLM initialized for agentic tools")
            else:
                logger.warning("⚠️ No API keys found for LLM initialization")
                self.llm = None
        except Exception as e:
            logger.error(f"❌ LLM initialization failed: {e}")
            self.llm = None

    def get_llamaindex_tools(self) -> List[FunctionTool]:
        """Get all tools as LlamaIndex FunctionTools with Pydantic schemas."""
        if not LLAMAINDEX_AVAILABLE:
            logger.error(
                "❌ LlamaIndex not available - cannot create agentic tools")
            return []

        tools = []

        # Medical tools with structured schemas and intelligent fallbacks
        tools.extend([
            FunctionTool.from_defaults(
                fn=self.find_doctor_info_structured,
                name="find_doctor_info",
                description="Find Humansa doctors by name, specialty, or city with fuzzy matching. Returns doctor details including specialties, clinic information, and registration fees/consultation prices. Always returns relevant results. For doctor names, use only actual Chinese family/personal names (e.g., '张', '王', '李明') - do NOT include titles like '医生', '主任', 'Dr.', etc. If no exact match, returns similar doctors from our network.",
                fn_schema=DoctorSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.find_doctor_availability_structured,
                name="find_doctor_availability",
                description="Check Humansa doctor availability across flexible date ranges (up to 30 days). Returns available time slots along with doctor information including registration fees. Supports 'next week', 'this month' requests. Uses fuzzy matching for doctor names. Always returns helpful results - if doctor not found, suggests similar available doctors with time slots and pricing. For doctor names, use only actual Chinese family/personal names (e.g., '张', '王', '李明') - do NOT include titles.",
                fn_schema=DoctorAvailabilityArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_clinics_structured,
                name="search_clinics",
                description="Search Humansa clinics by name, location, or specialty. Always returns 5 relevant clinics from our network. Uses intelligent fuzzy matching - even partial names find relevant results. If no matches, returns top available clinics.",
                fn_schema=ClinicSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_services_structured,
                name="search_services", 
                description="Search Humansa medical services by type, specialty, or clinic. Always returns 5 relevant services with pricing. Uses intelligent fuzzy matching - even partial service names find relevant results. If no matches, returns popular available services.",
                fn_schema=ServiceSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.get_pricing_structured,
                name="get_pricing",
                description="Get pricing information for Humansa medical services with fuzzy matching. Always returns relevant pricing from our clinics. If no exact match, returns available services with prices.",
                fn_schema=PricingArgs
            ),
            FunctionTool.from_defaults(
                fn=self.book_appointment_structured,
                name="book_appointment",
                description="Book appointments with Humansa doctors. For doctor names, use only actual Chinese family/personal names (e.g., '张', '王', '李明') - do NOT include titles like '医生', '主任', 'Dr.', etc. Validates doctor exists before booking.",
                fn_schema=BookingArgs
            ),
            FunctionTool.from_defaults(
                fn=self.place_call_structured,
                name="place_call",
                description="Place phone calls for urgent medical consultations or follow-ups",
                fn_schema=CallArgs
            ),
            FunctionTool.from_defaults(
                fn=self.recommend_product_structured,
                name="recommend_product",
                description="Recommend health products relevant to medical services",
                fn_schema=ProductRecommendationArgs
            ),
            FunctionTool.from_defaults(
                fn=self.push_content_structured,
                name="push_content",
                description="Push health education content and medical articles",
                fn_schema=ContentPushArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_web_structured,
                name="search_web",
                description="Search external web for news, research, general health information - NOT for Humansa services. Use internal tools (find_doctor_info, find_clinic_info, find_medical_services) for our clinical services.",
                fn_schema=SearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.find_clinic_info_structured,
                name="find_clinic_info",
                description="Find clinic information by name or location. Supports fuzzy matching for clinic names and exact matching for cities or areas.",
                fn_schema=ClinicSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_services_structured,
                name="search_services", 
                description="Search Humansa medical services by type, specialty, or clinic. Always returns 5 relevant services with pricing. Uses intelligent fuzzy matching - even partial service names find relevant results. If no matches, returns popular available services.",
                fn_schema=ServiceSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_clinics_structured,
                name="search_clinics",
                description="Search available Humansa clinics by name, city, or specialty with intelligent fuzzy matching. Always returns relevant clinic results. If no specific criteria, returns top 5 available clinics.",
                fn_schema=ClinicSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_services_structured,
                name="search_services",
                description="Search available Humansa medical services by name, specialty, or clinic with intelligent fuzzy matching. Always returns relevant services. If no specific criteria, returns top 5 available services.",
                fn_schema=ServiceSearchArgs
            )
        ])

        logger.info(
            f"✅ Created {len(tools)} LlamaIndex FunctionTools with Pydantic schemas")
        return tools

    # ====== STRUCTURED TOOL IMPLEMENTATIONS ======

    async def find_doctor_info_structured(self, name: Optional[str] = None, specialty: Optional[str] = None,
                                          city: Optional[str] = None, language: str = "zh") -> Dict[str, Any]:
        """
        Find doctor information with fuzzy search and intelligent fallbacks - REAL DATABASE ONLY.
        
        Returns:
            Dict containing:
            - doctors: List of doctor objects with name, specialty, clinic info, and registration_fee
            - Each doctor includes: name, title, expertise, bio, registration_fee, clinic_name, address, phone
            - total_found: Number of doctors found
            - search_type: Type of search performed (exact_match, fuzzy_match, fallback)
        """
        logger.info(
            f"🔍 find_doctor_info_structured called with: name={name}, specialty={specialty}, city={city}")

        try:
            # Use enhanced search with fallback
            doctors = db.search_doctors_with_fallback(name=name, specialty=specialty, city=city, limit=5)
            
            if doctors:
                search_type = "exact_match" if len(doctors) == 1 and name else "fuzzy_match_or_fallback"
                return {
                    "success": True,
                    "doctors": doctors,
                    "total_found": len(doctors),
                    "source": "database",
                    "search_type": search_type,
                    "message": f"Found {len(doctors)} doctor(s)" + (f" matching your criteria" if name or specialty or city else " from our available doctors")
                }
            else:
                # Even fallback failed - return available doctors
                all_doctors = db.search_doctors_with_fallback(limit=5)
                return {
                    "success": True,
                    "doctors": all_doctors,
                    "total_found": len(all_doctors),
                    "source": "database",
                    "search_type": "general_fallback",
                    "search_criteria": {"name": name, "specialty": specialty, "city": city},
                    "message": f"No exact matches found. Here are {len(all_doctors)} available doctors from our network."
                }
        except Exception as e:
            logger.error(f"❌ find_doctor_info_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def find_doctor_availability_structured(self, doctor_name: str, start_date: Optional[str] = None,
                                                  end_date: Optional[str] = None, specialty: Optional[str] = None,
                                                  days_ahead: Optional[int] = None) -> Dict[str, Any]:
        """
        Check doctor availability with flexible date ranges, fuzzy search and intelligent suggestions - REAL DATABASE ONLY.
        
        Returns:
            Dict containing:
            - doctor_name: Found doctor's name (may be fuzzy matched)
            - availability: List of available time slots with dates and times
            - doctor info: Includes registration_fee and clinic details
            - suggested_doctors: Alternative doctors with availability if original not found
            - Each suggested doctor includes pricing and availability information
        """
        
        # Calculate date range
        today = datetime.now().date()
        
        if days_ahead:
            start_date_obj = today
            end_date_obj = today + timedelta(days=min(days_ahead, 30))
        elif start_date:
            start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
            if end_date:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                # Limit to 30 days maximum
                if (end_date_obj - start_date_obj).days > 30:
                    end_date_obj = start_date_obj + timedelta(days=30)
            else:
                end_date_obj = start_date_obj + timedelta(days=30)
        else:
            start_date_obj = today
            end_date_obj = today + timedelta(days=30)
        
        start_date_str = start_date_obj.strftime('%Y-%m-%d')
        end_date_str = end_date_obj.strftime('%Y-%m-%d')
        
        logger.info(f"📅 find_doctor_availability_structured called with: doctor={doctor_name}, range={start_date_str} to {end_date_str}")

        try:
            # Validate doctor_name is not empty
            if not doctor_name or doctor_name.strip() == "":
                return {
                    "success": False,
                    "error": "Doctor name is required and cannot be empty",
                    "doctor_name": doctor_name,
                    "date_range": f"{start_date_str} to {end_date_str}",
                    "source": "validation_error"
                }

            # Use enhanced availability search with date range
            availability_result = db.find_doctor_availability_range_with_fallback(
                doctor_name, start_date_str, end_date_str
            )
            
            if availability_result['doctor_found']:
                return {
                    "success": True,
                    "doctor_name": availability_result.get('found_doctor_name', doctor_name),
                    "date_range": f"{start_date_str} to {end_date_str}",
                    "availability": availability_result['availability'],
                    "total_slots": len(availability_result['availability']),
                    "available_dates": availability_result.get('available_dates', []),
                    "source": "database",
                    "search_method": availability_result['search_method'],
                    "exact_match": availability_result['exact_match'],
                    "message": f"Found {len(availability_result['availability'])} available slots across {len(availability_result.get('available_dates', []))} days" if availability_result['availability'] else f"No available slots found in date range {start_date_str} to {end_date_str}"
                }
            else:
                # Doctor not found, suggest alternatives
                return {
                    "success": True,
                    "doctor_name": doctor_name,
                    "date_range": f"{start_date_str} to {end_date_str}",
                    "availability": [],
                    "total_slots": 0,
                    "doctor_found": False,
                    "suggested_doctors": availability_result.get('suggested_doctors', []),
                    "source": "database",
                    "search_method": "suggestion",
                    "message": f"Doctor '{doctor_name}' not found. Here are similar available doctors with slots in the requested time range."
                }

        except Exception as e:
            logger.error(f"❌ find_doctor_availability_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def get_pricing_structured(self, service_type: str, clinic_name: Optional[str] = None,
                                     specialty: Optional[str] = None, currency: str = "CNY") -> Dict[str, Any]:
        """Get pricing information with fuzzy search and intelligent fallbacks - REAL DATABASE ONLY."""
        logger.info(
            f"💰 get_pricing_structured called with: service={service_type}, clinic={clinic_name}")

        try:
            # Use enhanced service search with fallback
            services = db.search_services_with_fallback(
                service_name=service_type, clinic_name=clinic_name, limit=5
            )
            
            if services:
                return {
                    "success": True,
                    "service_type": service_type,
                    "clinic_name": clinic_name,
                    "pricing": services,
                    "total_services": len(services),
                    "source": "database",
                    "message": f"Found {len(services)} service(s) with pricing information"
                }
            else:
                # Even fallback failed - return available services
                all_services = db.search_services_with_fallback(limit=5)
                return {
                    "success": True,
                    "service_type": service_type,
                    "clinic_name": clinic_name,
                    "pricing": all_services,
                    "total_services": len(all_services),
                    "source": "database",
                    "search_type": "general_fallback",
                    "message": f"No exact service matches found. Here are {len(all_services)} available services from our clinics."
                }

        except Exception as e:
            logger.error(f"❌ get_pricing_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def book_appointment_structured(self, doctor_name: str, date_iso: str, time_hhmm: str,
                                          patient_name: str, phone: str, service_type: str) -> Dict[str, Any]:
        """Book appointment using structured arguments - REAL DATABASE VALIDATION, SIMULATED BOOKING."""
        logger.info(
            f"📅 book_appointment_structured called with: doctor={doctor_name}, date={date_iso}, time={time_hhmm}")

        try:
            # Validate required fields are not empty
            if not doctor_name or doctor_name.strip() == "":
                return {
                    "success": False,
                    "error": "Doctor name is required and cannot be empty",
                    "source": "validation_error"
                }
            
            if not patient_name or patient_name.strip() == "":
                return {
                    "success": False,
                    "error": "Patient name is required and cannot be empty",
                    "source": "validation_error"
                }

            # Check if doctor exists in REAL database first
            doctor_info = db.find_doctor_by_name(doctor_name)
            if not doctor_info:
                return {
                    "success": False,
                    "error": f"Doctor {doctor_name} not found in system",
                    "source": "database_validation"
                }

            # Check if appointment slot is available
            availability = db.find_doctor_availability(doctor_name, date_iso)
            if not availability:
                return {
                    "success": False,
                    "error": f"No available slots found for {doctor_name} on {date_iso}",
                    "source": "database_validation"
                }

            # Simulate successful booking (no actual database writes per requirements)
            booking_id = f"BOOK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            return {
                "success": True,
                "booking_id": booking_id,
                "doctor_name": doctor_name,
                "appointment_date": date_iso,
                "appointment_time": time_hhmm,
                "patient_name": patient_name,
                "phone": phone,
                "service_type": service_type,
                "clinic": doctor_info.get('clinic_name', 'Unknown Clinic'),
                "registration_fee": doctor_info.get('registration_fee', 0),
                "status": "confirmed",
                "confirmation_sent": True,
                "source": "simulated_booking",
                "message": f"Appointment successfully booked with {doctor_name}"
            }

        except Exception as e:
            logger.error(f"❌ book_appointment_structured failed: {e}")
            return {"error": str(e), "success": False}

    def place_call_structured(self, phone_number: str, purpose: str, urgency: str = "normal") -> Dict[str, Any]:
        """Place call using structured arguments - NO heuristic extraction."""
        logger.info(
            f"📞 place_call_structured called with: number={phone_number}, purpose={purpose}")

        try:
            # Pure function - expects structured arguments
            # In real implementation, this would integrate with calling service
            return {
                "success": True,
                "action": "call_initiated",
                "phone_number": phone_number,
                "purpose": purpose,
                "urgency": urgency,
                "call_id": f"call_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "message": f"Initiating {urgency} call to {phone_number} for: {purpose}"
            }
        except Exception as e:
            logger.error(f"❌ place_call_structured failed: {e}")
            return {"error": str(e), "success": False}

    def recommend_product_structured(self, product_category: str, reason: str,
                                     price_range: Optional[str] = None) -> Dict[str, Any]:
        """Recommend products using structured arguments - NO heuristic extraction."""
        logger.info(
            f"🛍️ recommend_product_structured called with: category={product_category}")

        try:
            # Mock product recommendations
            products = {
                "supplements": ["Vitamin D3", "Omega-3", "Multivitamin"],
                "equipment": ["Blood Pressure Monitor", "Thermometer", "Pulse Oximeter"],
                "skincare": ["Medical Grade Moisturizer", "Sunscreen SPF 50", "Gentle Cleanser"]
            }

            category_products = products.get(product_category.lower(), [
                                             "General Health Products"])

            return {
                "success": True,
                "category": product_category,
                "reason": reason,
                "price_range": price_range,
                "recommended_products": category_products,
                "message": f"Recommended {len(category_products)} products in {product_category} category"
            }
        except Exception as e:
            logger.error(f"❌ recommend_product_structured failed: {e}")
            return {"error": str(e), "success": False}

    def push_content_structured(self, content_type: str, topic: str, target_audience: str) -> Dict[str, Any]:
        """Push content using structured arguments - NO heuristic extraction."""
        logger.info(
            f"📱 push_content_structured called with: type={content_type}, topic={topic}")

        try:
            # Mock content push
            return {
                "success": True,
                "content_type": content_type,
                "topic": topic,
                "target_audience": target_audience,
                "content_id": f"content_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "message": f"Pushed {content_type} about '{topic}' to {target_audience}",
                "engagement_expected": "high" if "health" in topic.lower() else "medium"
            }
        except Exception as e:
            logger.error(f"❌ push_content_structured failed: {e}")
            return {"error": str(e), "success": False}



    async def search_web_structured(self, query: str, category: Optional[str] = None,
                              language: str = "zh") -> Dict[str, Any]:
        """Search external web content for news, research, and general information - NOT for Humansa services."""
        logger.info(f"🌐 search_web_structured called with: query={query}")

        try:
            # Safety check: Prevent searching for internal services
            internal_terms = ["医生", "诊所", "预约", "挂号", "doctor", "clinic", "appointment", "booking", 
                            "价格", "pricing", "费用", "医疗服务", "medical service"]
            
            query_lower = query.lower()
            if any(term in query_lower for term in internal_terms):
                return {
                    "success": False,
                    "error": "Web search is for external information only. Use find_doctor_info, find_clinic_info, or find_medical_services for Humansa clinical services.",
                    "query": query,
                    "suggestion": "Try using our internal search tools instead"
                }

            if not WEB_SEARCH_AVAILABLE:
                return {
                    "success": False,
                    "error": "Web search not available in this environment",
                    "query": query
                }

            # Use real web search processor for external information only
            web_search = WebSearchProcessor()
            search_results = await web_search.search_web_content(query, num_results=5)
            
            # Convert to our format
            formatted_results = []
            for result in search_results.results:
                formatted_results.append({
                    "url": result.link,
                    "title": result.title,
                    "snippet": result.snippet,
                    "source": result.source,
                    "cached": result.cached
                })

            return {
                "success": True,
                "query": query,
                "language": language,
                "results": formatted_results,
                "total_results": len(formatted_results),
                "search_performed": search_results.search_performed,
                "cache_hit": search_results.cache_hit,
                "source": "real_web_search",
                "message": f"Found {len(formatted_results)} external web results for: {query}",
                "note": "This is external information. Use internal tools for Humansa services."
            }
        except Exception as e:
            logger.error(f"❌ search_web_structured failed: {e}")
            return {"error": str(e), "success": False}



    # ====== OBSERVABILITY METHODS ======

    def get_tool_calls_observed(self) -> List[Dict]:
        """Get all tool calls observed by the callback manager."""
        return self.callback_handler.get_tool_calls()

    def get_all_events_observed(self) -> List[Dict]:
        """Get all events observed by the callback manager."""
        return self.callback_handler.get_events()

    def reset_observations(self):
        """Reset the callback handler observations."""
        self.trace_handler = ReActTraceHandler()
        self.callback_handler = HumansaCallbackHandler()
        self.callback_manager = CallbackManager([self.callback_handler, self.trace_handler])
        if LLAMAINDEX_AVAILABLE:
            Settings.callback_manager = self.callback_manager

    async def find_clinic_info_structured(self, name: Optional[str] = None, city: Optional[str] = None,
                                          language: str = "zh") -> Dict[str, Any]:
        """Find clinic information with fuzzy search and intelligent fallbacks - REAL DATABASE ONLY."""
        logger.info(
            f"🏥 find_clinic_info_structured called with: name={name}, city={city}")

        try:
            # Use enhanced clinic search with fallback
            clinic_result = db.search_clinics_with_fallback(clinic_name=name, city=city, limit=5)
            
            if clinic_result['clinics_found']:
                return {
                    "success": True,
                    "clinics": clinic_result['clinics'],
                    "total_found": clinic_result['total_found'],
                    "source": "database",
                    "search_type": clinic_result['search_method'],
                    "message": f"Found {clinic_result['total_found']} clinic(s)" + (f" matching your criteria" if name or city else " from our network")
                }
            else:
                return {
                    "success": False,
                    "error": clinic_result.get('error', 'No clinics found'),
                    "clinics": [],
                    "total_found": 0,
                    "source": "database"
                }
        except Exception as e:
            logger.error(f"❌ find_clinic_info_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def find_medical_services_structured(self, service_name: Optional[str] = None, clinic_name: Optional[str] = None,
                                             language: str = "zh") -> Dict[str, Any]:
        """Find medical services with fuzzy search and intelligent fallbacks - REAL DATABASE ONLY."""
        logger.info(
            f"🩺 find_medical_services_structured called with: service={service_name}, clinic={clinic_name}")

        try:
            # Use enhanced service search with fallback
            services = db.search_services_with_fallback(
                service_name=service_name, clinic_name=clinic_name, limit=5
            )
            
            if services:
                search_type = "specific_match" if service_name or clinic_name else "general_listing"
                return {
                    "success": True,
                    "services": services,
                    "total_found": len(services),
                    "source": "database",
                    "search_type": search_type,
                    "message": f"Found {len(services)} medical service(s)" + (f" matching your criteria" if service_name or clinic_name else " from our clinics")
                }
            else:
                # Even fallback failed - return available services
                all_services = db.search_services_with_fallback(limit=5)
                return {
                    "success": True,
                    "services": all_services,
                    "total_found": len(all_services),
                    "source": "database",
                    "search_type": "general_fallback",
                    "search_criteria": {"service_name": service_name, "clinic_name": clinic_name},
                    "message": f"No exact matches found. Here are {len(all_services)} available services from our network."
                }
        except Exception as e:
            logger.error(f"❌ find_medical_services_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def search_clinics_structured(self, clinic_name: Optional[str] = None, city: Optional[str] = None,
                                       specialty: Optional[str] = None, language: str = "zh") -> Dict[str, Any]:
        """Search available Humansa clinics with intelligent fuzzy matching and fallback - REAL DATABASE ONLY."""
        logger.info(f"🏥 search_clinics_structured called with: clinic={clinic_name}, city={city}, specialty={specialty}")
        
        try:
            # Use enhanced clinic search with fallback
            clinic_result = db.search_clinics_with_fallback(
                clinic_name=clinic_name, city=city, specialty=specialty, limit=5
            )
            
            if clinic_result['clinics_found']:
                return {
                    "success": True,
                    "clinics": clinic_result['clinics'],
                    "total_found": clinic_result['total_found'],
                    "search_method": clinic_result['search_method'],
                    "filters_applied": clinic_result.get('filters_applied', {}),
                    "source": "database",
                    "message": f"Found {clinic_result['total_found']} clinic(s) matching your criteria" if clinic_result['search_method'] != 'fallback' else clinic_result.get('message', 'Here are our available clinics')
                }
            else:
                return {
                    "success": False,
                    "error": clinic_result.get('error', 'Failed to search clinics'),
                    "clinics": [],
                    "total_found": 0,
                    "source": "database"
                }
                
        except Exception as e:
            logger.error(f"❌ search_clinics_structured failed: {e}")
            return {"error": str(e), "success": False}

    async def search_services_structured(self, service_name: Optional[str] = None, specialty: Optional[str] = None,
                                       clinic_name: Optional[str] = None, language: str = "zh") -> Dict[str, Any]:
        """Search available Humansa medical services with intelligent fuzzy matching and fallback - REAL DATABASE ONLY."""
        logger.info(f"🩺 search_services_structured called with: service={service_name}, specialty={specialty}, clinic={clinic_name}")
        
        try:
            # Use enhanced service search with fallback
            service_result = db.search_services_with_fallback(
                service_name=service_name, specialty=specialty, clinic_name=clinic_name, limit=5
            )
            
            if service_result['services_found']:
                return {
                    "success": True,
                    "services": service_result['services'],
                    "total_found": service_result['total_found'],
                    "search_method": service_result['search_method'],
                    "filters_applied": service_result.get('filters_applied', {}),
                    "source": "database",
                    "message": f"Found {service_result['total_found']} service(s) matching your criteria" if service_result['search_method'] != 'fallback' else service_result.get('message', 'Here are our available services')
                }
            else:
                return {
                    "success": False,
                    "error": service_result.get('error', 'Failed to search services'),
                    "services": [],
                    "total_found": 0,
                    "source": "database"
                }
                
        except Exception as e:
            logger.error(f"❌ search_services_structured failed: {e}")
            return {"error": str(e), "success": False}
