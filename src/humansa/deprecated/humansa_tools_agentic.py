"""
Humansa Agentic Tools Manager with Structured Schemas

Provides fully agentic tool execution using LlamaIndex FunctionTool.from_defaults
with Pydantic schemas for ALL tool arguments. NO heuristic argument extraction.

All business/safety rules are enforced in the system prompt and post-processing,
NOT in the tool code. Tools are pure functions that expect structured arguments.
"""

import logging
from typing import Dict, Any, List, Optional, Union
import json
import asyncio
import os
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)

# Database connection
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    DB_AVAILABLE = True
except ImportError:
    logger.warning("psycopg2 not available - database functions will be mocked")
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
    from llama_index.core.callbacks import CallbackManager, BaseCallbackHandler
    from llama_index.core.callbacks.schema import CBEventType
    from llama_index.core import Settings
    LLAMAINDEX_AVAILABLE = True
except ImportError as e:
    logger.warning(f"LlamaIndex not fully available: {e}")
    LLAMAINDEX_AVAILABLE = False


# ====== PYDANTIC SCHEMAS FOR STRUCTURED TOOL ARGUMENTS ======

class DoctorSearchArgs(BaseModel):
    """Arguments for finding doctor information."""
    name: Optional[str] = Field(None, description="Doctor's name (partial match allowed)")
    specialty: Optional[str] = Field(None, description="Medical specialty (e.g., 'cardiology', '心内科')")
    city: Optional[str] = Field(None, description="City name (e.g., 'Beijing', '北京')")
    language: str = Field("zh", description="Response language: 'zh' or 'en'")

class DoctorAvailabilityArgs(BaseModel):
    """Arguments for checking doctor availability."""
    doctor_name: str = Field(..., description="Full or partial doctor name")
    date_iso: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    specialty: Optional[str] = Field(None, description="Medical specialty")
    
    @validator('date_iso')
    def validate_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Date must be in YYYY-MM-DD format')

class PricingArgs(BaseModel):
    """Arguments for getting service pricing."""
    service_type: str = Field(..., description="Type of medical service")
    clinic_name: Optional[str] = Field(None, description="Specific clinic name")
    specialty: Optional[str] = Field(None, description="Medical specialty")
    currency: str = Field("CNY", description="Currency for pricing")

class BookingArgs(BaseModel):
    """Arguments for booking appointments."""
    doctor_name: str = Field(..., description="Full doctor name")
    date_iso: str = Field(..., description="Appointment date (YYYY-MM-DD)")
    time_hhmm: str = Field(..., description="Appointment time (HH:MM, 24-hour format)")
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
    urgency: str = Field("normal", description="Urgency level: 'normal', 'urgent', 'emergency'")

class ProductRecommendationArgs(BaseModel):
    """Arguments for recommending products."""
    product_category: str = Field(..., description="Category of product to recommend")
    reason: str = Field(..., description="Reason for recommendation")
    price_range: Optional[str] = Field(None, description="Preferred price range")

class ContentPushArgs(BaseModel):
    """Arguments for pushing content."""
    content_type: str = Field(..., description="Type of content: 'article', 'video', 'post'")
    topic: str = Field(..., description="Content topic")
    target_audience: str = Field(..., description="Target audience")

class SearchArgs(BaseModel):
    """Arguments for search operations."""
    query: str = Field(..., description="Search query")
    category: Optional[str] = Field(None, description="Search category")
    language: str = Field("zh", description="Search language: 'zh' or 'en'")


# ====== CALLBACK HANDLER FOR OBSERVABILITY ======

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
            logger.info(f"🔧 TOOL CALL OBSERVED: {tool_call['tool_name']} with args: {tool_call['arguments']}")
        
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
                    tool_call['result'] = payload.get('function_call_response', 'unknown')
                    tool_call['completed'] = True
                    logger.info(f"✅ TOOL CALL COMPLETED: {tool_call['tool_name']}")
                    break
    
    def get_tool_calls(self) -> List[Dict]:
        """Get all observed tool calls."""
        return self.tool_calls.copy()
    
    def get_events(self) -> List[Dict]:
        """Get all observed events."""
        return self.events.copy()


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
        self.callback_handler = HumansaCallbackHandler()
        self.callback_manager = CallbackManager([self.callback_handler])
        
        # Initialize LLM
        self._initialize_llm()
        
        # Set global callback manager
        if LLAMAINDEX_AVAILABLE:
            Settings.callback_manager = self.callback_manager
        
        logger.info("🛠️ HumansaAgenticToolManager initialized with structured schemas")
        logger.info("📊 CallbackManager configured for tool call observability")

    def _initialize_llm(self):
        """Initialize the LLM for the agentic tools."""
        try:
            # Try Azure OpenAI first
            if AzureOpenAI and os.getenv("AZURE_OPENAI_API_KEY"):
                self.llm = AzureOpenAI(
                    engine=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4.1-nano"),
                    model=os.getenv("AZURE_OPENAI_MODEL_NAME", "gpt-4.1-nano"),
                    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
                    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
                    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
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
            logger.error("❌ LlamaIndex not available - cannot create agentic tools")
            return []
        
        tools = []
        
        # Medical tools with structured schemas
        tools.extend([
            FunctionTool.from_defaults(
                fn=self.find_doctor_info_structured,
                name="find_doctor_info",
                description="Find doctor information by name, specialty, or city using structured arguments",
                fn_schema=DoctorSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.find_doctor_availability_structured,
                name="find_doctor_availability", 
                description="Check doctor availability for specific dates using structured arguments",
                fn_schema=DoctorAvailabilityArgs
            ),
            FunctionTool.from_defaults(
                fn=self.get_pricing_structured,
                name="get_pricing",
                description="Get pricing information for medical services using structured arguments",
                fn_schema=PricingArgs
            ),
            FunctionTool.from_defaults(
                fn=self.book_appointment_structured,
                name="book_appointment",
                description="Book medical appointments using structured arguments",
                fn_schema=BookingArgs
            ),
            FunctionTool.from_defaults(
                fn=self.place_call_structured,
                name="place_call",
                description="Place phone calls using structured arguments",
                fn_schema=CallArgs
            ),
            FunctionTool.from_defaults(
                fn=self.recommend_product_structured,
                name="recommend_product",
                description="Recommend products using structured arguments",
                fn_schema=ProductRecommendationArgs
            ),
            FunctionTool.from_defaults(
                fn=self.push_content_structured,
                name="push_content",
                description="Push content recommendations using structured arguments",
                fn_schema=ContentPushArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_notes_structured,
                name="search_notes",
                description="Search medical notes and documentation using structured arguments",
                fn_schema=SearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.search_web_structured,
                name="search_web",
                description="Search web content using structured arguments",
                fn_schema=SearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.get_current_date_structured,
                name="get_current_date",
                description="Get the current date - no arguments needed",
            )
        ])
        
        logger.info(f"✅ Created {len(tools)} LlamaIndex FunctionTools with Pydantic schemas")
        return tools

    # ====== STRUCTURED TOOL IMPLEMENTATIONS ======
    
    def find_doctor_info_structured(self, name: Optional[str] = None, specialty: Optional[str] = None, 
                                   city: Optional[str] = None, language: str = "zh") -> Dict[str, Any]:
        """Find doctor information using structured arguments - NO heuristic extraction."""
        logger.info(f"🔍 find_doctor_info_structured called with: name={name}, specialty={specialty}, city={city}")
        
        try:
            # Pure function - expects structured arguments, no extraction
            if DB_AVAILABLE and self.db_config:
                return self._query_doctors_database(name, specialty, city)
            else:
                # Mock data for testing (will be removed in production)
                return self._get_mock_doctor_info(name, specialty, city, language)
        except Exception as e:
            logger.error(f"❌ find_doctor_info_structured failed: {e}")
            return {"error": str(e), "success": False}

    def find_doctor_availability_structured(self, doctor_name: str, date_iso: str, 
                                           specialty: Optional[str] = None) -> Dict[str, Any]:
        """Check doctor availability using structured arguments - NO heuristic extraction."""
        logger.info(f"📅 find_doctor_availability_structured called with: doctor={doctor_name}, date={date_iso}")
        
        try:
            # Pure function - expects structured arguments
            if DB_AVAILABLE and self.db_config:
                return self._query_doctor_availability_database(doctor_name, date_iso, specialty)
            else:
                # Mock data for testing
                return self._get_mock_availability(doctor_name, date_iso, specialty)
        except Exception as e:
            logger.error(f"❌ find_doctor_availability_structured failed: {e}")
            return {"error": str(e), "success": False}

    def get_pricing_structured(self, service_type: str, clinic_name: Optional[str] = None, 
                              specialty: Optional[str] = None, currency: str = "CNY") -> Dict[str, Any]:
        """Get pricing information using structured arguments - NO heuristic extraction."""
        logger.info(f"💰 get_pricing_structured called with: service={service_type}, clinic={clinic_name}")
        
        try:
            # Pure function - expects structured arguments
            if DB_AVAILABLE and self.db_config:
                return self._query_pricing_database(service_type, clinic_name, specialty)
            else:
                # Mock data for testing
                return self._get_mock_pricing(service_type, clinic_name, specialty, currency)
        except Exception as e:
            logger.error(f"❌ get_pricing_structured failed: {e}")
            return {"error": str(e), "success": False}

    def book_appointment_structured(self, doctor_name: str, date_iso: str, time_hhmm: str,
                                   patient_name: str, phone: str, service_type: str) -> Dict[str, Any]:
        """Book appointment using structured arguments - NO heuristic extraction."""
        logger.info(f"📅 book_appointment_structured called with: doctor={doctor_name}, date={date_iso}, time={time_hhmm}")
        
        try:
            # Pure function - expects structured arguments
            if DB_AVAILABLE and self.db_config:
                return self._book_appointment_database(doctor_name, date_iso, time_hhmm, patient_name, phone, service_type)
            else:
                # Mock booking for testing
                return self._mock_book_appointment(doctor_name, date_iso, time_hhmm, patient_name, phone, service_type)
        except Exception as e:
            logger.error(f"❌ book_appointment_structured failed: {e}")
            return {"error": str(e), "success": False}

    def place_call_structured(self, phone_number: str, purpose: str, urgency: str = "normal") -> Dict[str, Any]:
        """Place call using structured arguments - NO heuristic extraction."""
        logger.info(f"📞 place_call_structured called with: number={phone_number}, purpose={purpose}")
        
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
        logger.info(f"🛍️ recommend_product_structured called with: category={product_category}")
        
        try:
            # Mock product recommendations
            products = {
                "supplements": ["Vitamin D3", "Omega-3", "Multivitamin"],
                "equipment": ["Blood Pressure Monitor", "Thermometer", "Pulse Oximeter"],
                "skincare": ["Medical Grade Moisturizer", "Sunscreen SPF 50", "Gentle Cleanser"]
            }
            
            category_products = products.get(product_category.lower(), ["General Health Products"])
            
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
        logger.info(f"📱 push_content_structured called with: type={content_type}, topic={topic}")
        
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

    def search_notes_structured(self, query: str, category: Optional[str] = None, 
                               language: str = "zh") -> Dict[str, Any]:
        """Search notes using structured arguments - NO heuristic extraction."""
        logger.info(f"📝 search_notes_structured called with: query={query}")
        
        try:
            # Mock notes search
            mock_notes = [
                {"id": 1, "title": f"Note about {query}", "category": category or "general", "relevance": 0.9},
                {"id": 2, "title": f"Related information for {query}", "category": category or "general", "relevance": 0.7}
            ]
            
            return {
                "success": True,
                "query": query,
                "category": category,
                "results": mock_notes,
                "total_results": len(mock_notes),
                "message": f"Found {len(mock_notes)} notes for query: {query}"
            }
        except Exception as e:
            logger.error(f"❌ search_notes_structured failed: {e}")
            return {"error": str(e), "success": False}

    def search_web_structured(self, query: str, category: Optional[str] = None, 
                             language: str = "zh") -> Dict[str, Any]:
        """Search web using structured arguments - NO heuristic extraction."""
        logger.info(f"🌐 search_web_structured called with: query={query}")
        
        try:
            # Mock web search
            mock_results = [
                {"url": f"https://example.com/search?q={query}", "title": f"Web result for {query}", "relevance": 0.8},
                {"url": f"https://medical.com/info/{query}", "title": f"Medical info about {query}", "relevance": 0.9}
            ]
            
            return {
                "success": True,
                "query": query,
                "language": language,
                "results": mock_results,
                "total_results": len(mock_results),
                "message": f"Found {len(mock_results)} web results for: {query}"
            }
        except Exception as e:
            logger.error(f"❌ search_web_structured failed: {e}")
            return {"error": str(e), "success": False}

    def get_current_date_structured(self) -> Dict[str, Any]:
        """Get current date - no arguments needed."""
        try:
            current_date = datetime.now()
            return {
                "success": True,
                "date_iso": current_date.strftime("%Y-%m-%d"),
                "date_formatted": current_date.strftime("%Y年%m月%d日"),
                "day_of_week": current_date.strftime("%A"),
                "timestamp": current_date.isoformat()
            }
        except Exception as e:
            logger.error(f"❌ get_current_date_structured failed: {e}")
            return {"error": str(e), "success": False}

    # ====== MOCK DATA METHODS (for testing) ======
    
    def _get_mock_doctor_info(self, name: Optional[str], specialty: Optional[str], 
                             city: Optional[str], language: str) -> Dict[str, Any]:
        """Generate mock doctor information."""
        doctors = [
            {"name": "Dr. 李明", "specialty": "心内科", "city": "北京", "rating": 4.8, "experience": "15年"},
            {"name": "Dr. 王芳", "specialty": "儿科", "city": "上海", "rating": 4.9, "experience": "12年"},
            {"name": "Dr. 张伟", "specialty": "外科", "city": "广州", "rating": 4.7, "experience": "20年"}
        ]
        
        # Filter based on criteria
        filtered_doctors = doctors
        if name:
            filtered_doctors = [d for d in filtered_doctors if name.lower() in d["name"].lower()]
        if specialty:
            filtered_doctors = [d for d in filtered_doctors if specialty in d["specialty"]]
        if city:
            filtered_doctors = [d for d in filtered_doctors if city in d["city"]]
        
        return {
            "success": True,
            "doctors": filtered_doctors,
            "total_found": len(filtered_doctors),
            "search_criteria": {"name": name, "specialty": specialty, "city": city}
        }

    def _get_mock_availability(self, doctor_name: str, date_iso: str, specialty: Optional[str]) -> Dict[str, Any]:
        """Generate mock availability information."""
        available_slots = ["09:00", "10:30", "14:00", "15:30", "16:30"]
        
        return {
            "success": True,
            "doctor_name": doctor_name,
            "date": date_iso,
            "available_slots": available_slots,
            "total_slots": len(available_slots),
            "clinic": "Humansa医疗中心"
        }

    def _get_mock_pricing(self, service_type: str, clinic_name: Optional[str], 
                         specialty: Optional[str], currency: str) -> Dict[str, Any]:
        """Generate mock pricing information."""
        base_prices = {
            "consultation": 300,
            "checkup": 500,
            "surgery": 5000,
            "therapy": 200
        }
        
        price = base_prices.get(service_type.lower(), 250)
        
        return {
            "success": True,
            "service_type": service_type,
            "price": price,
            "currency": currency,
            "clinic": clinic_name or "Humansa医疗中心",
            "includes": ["医生咨询", "基础检查", "报告解读"],
            "valid_until": "2024-12-31"
        }

    def _mock_book_appointment(self, doctor_name: str, date_iso: str, time_hhmm: str,
                              patient_name: str, phone: str, service_type: str) -> Dict[str, Any]:
        """Generate mock booking confirmation."""
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
            "clinic": "Humansa医疗中心",
            "status": "confirmed",
            "confirmation_sent": True
        }

    # ====== DATABASE METHODS (for production) ======
    
    def _query_doctors_database(self, name: Optional[str], specialty: Optional[str], city: Optional[str]) -> Dict[str, Any]:
        """Query doctors from database - pure function, no heuristics."""
        # Implementation would go here
        return self._get_mock_doctor_info(name, specialty, city, "zh")

    def _query_doctor_availability_database(self, doctor_name: str, date_iso: str, specialty: Optional[str]) -> Dict[str, Any]:
        """Query doctor availability from database - pure function."""
        # Implementation would go here  
        return self._get_mock_availability(doctor_name, date_iso, specialty)

    def _query_pricing_database(self, service_type: str, clinic_name: Optional[str], specialty: Optional[str]) -> Dict[str, Any]:
        """Query pricing from database - pure function."""
        # Implementation would go here
        return self._get_mock_pricing(service_type, clinic_name, specialty, "CNY")

    def _book_appointment_database(self, doctor_name: str, date_iso: str, time_hhmm: str,
                                  patient_name: str, phone: str, service_type: str) -> Dict[str, Any]:
        """Book appointment in database - pure function."""
        # Implementation would go here
        return self._mock_book_appointment(doctor_name, date_iso, time_hhmm, patient_name, phone, service_type)

    # ====== OBSERVABILITY METHODS ======
    
    def get_tool_calls_observed(self) -> List[Dict]:
        """Get all tool calls observed by the callback manager."""
        return self.callback_handler.get_tool_calls()

    def get_all_events_observed(self) -> List[Dict]:
        """Get all events observed by the callback manager."""
        return self.callback_handler.get_events()

    def reset_observations(self):
        """Reset the callback handler observations."""
        self.callback_handler = HumansaCallbackHandler()
        self.callback_manager = CallbackManager([self.callback_handler])
        if LLAMAINDEX_AVAILABLE:
            Settings.callback_manager = self.callback_manager
