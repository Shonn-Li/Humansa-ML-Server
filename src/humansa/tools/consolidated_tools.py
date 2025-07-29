"""
Consolidated HUMANSA Tools - Simplified from ~15 to 7 Core Functions

This module provides a streamlined set of 7 core tools that cover all functionality
previously spread across multiple tools, reducing context usage and improving performance.

Tools:
1. unified_search - Combines doctor, clinic, service search
2. appointment_manager - Handles booking, rescheduling, cancellation  
3. medical_advisor - Health consultation and triage
4. product_recommender - All product-related queries
5. information_lookup - Pricing, hours, contact info
6. emergency_handler - Critical situations
7. conversation_memory - Store/retrieve conversation context
"""

from typing import Dict, Any, List, Optional, Union
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
import logging
import asyncio
from ..postgres.database import db
from ..utils.date_parser import ChineseDateParser

logger = logging.getLogger(__name__)

# Try to import LlamaIndex for tool creation
try:
    from llama_index.core.tools import FunctionTool
    LLAMAINDEX_AVAILABLE = True
except ImportError:
    logger.warning("LlamaIndex not available")
    LLAMAINDEX_AVAILABLE = False


# ===== PYDANTIC SCHEMAS FOR TOOLS =====

class UnifiedSearchArgs(BaseModel):
    """Arguments for unified search across doctors, clinics, and services"""
    query: str = Field(description="搜索查询，可以是医生名、诊所名、服务名、专科等")
    search_type: Optional[str] = Field(
        default=None,
        description="搜索类型：'doctor'（医生）, 'clinic'（诊所）, 'service'（服务）, 或 None（全部搜索）"
    )
    city: Optional[str] = Field(default=None, description="城市过滤，如'深圳'、'北京'等")
    specialty: Optional[str] = Field(default=None, description="专科过滤，如'内科'、'妇科'等")
    date_range: Optional[str] = Field(default=None, description="日期范围，如'明天'、'本周'、'下周'等")
    limit: int = Field(default=5, description="返回结果数量限制")


class AppointmentManagerArgs(BaseModel):
    """Arguments for appointment management operations"""
    action: str = Field(
        description="操作类型：'check'（检查信息）, 'book'（预约）, 'reschedule'（改期）, 'cancel'（取消）, 'history'（历史）"
    )
    doctor_name: Optional[str] = Field(default=None, description="医生姓名")
    patient_name: Optional[str] = Field(default=None, description="患者姓名")
    phone: Optional[str] = Field(default=None, description="联系电话")
    date: Optional[str] = Field(default=None, description="预约日期")
    time: Optional[str] = Field(default=None, description="预约时间")
    appointment_id: Optional[str] = Field(default=None, description="预约号（用于改期或取消）")
    new_date: Optional[str] = Field(default=None, description="新日期（用于改期）")
    new_time: Optional[str] = Field(default=None, description="新时间（用于改期）")
    reason: Optional[str] = Field(default=None, description="取消或改期原因")


class MedicalAdvisorArgs(BaseModel):
    """Arguments for medical consultation and triage"""
    symptoms: List[str] = Field(description="症状列表，如['头痛', '发烧', '咳嗽']")
    duration: Optional[str] = Field(default=None, description="症状持续时间，如'3天'、'一周'")
    severity: Optional[str] = Field(default=None, description="严重程度：'轻微'、'中等'、'严重'")
    patient_age: Optional[int] = Field(default=None, description="患者年龄")
    medical_history: Optional[List[str]] = Field(default=None, description="既往病史")
    current_medications: Optional[List[str]] = Field(default=None, description="当前用药")
    allergies: Optional[List[str]] = Field(default=None, description="过敏史")


class ProductRecommenderArgs(BaseModel):
    """Arguments for product recommendations"""
    category: Optional[str] = Field(
        default=None,
        description="产品类别：'supplements'（保健品）, 'devices'（医疗器械）, 'skincare'（护肤品）等"
    )
    condition: Optional[str] = Field(default=None, description="健康状况或需求，如'失眠'、'关节痛'等")
    budget: Optional[str] = Field(default=None, description="预算范围，如'100-500'")
    preferences: Optional[List[str]] = Field(default=None, description="偏好，如['天然', '进口', '无糖']")


class InformationLookupArgs(BaseModel):
    """Arguments for general information queries"""
    info_type: str = Field(
        description="信息类型：'pricing'（价格）, 'hours'（营业时间）, 'contact'（联系方式）, 'insurance'（保险）, 'location'（地址）"
    )
    entity_name: Optional[str] = Field(default=None, description="实体名称（诊所、医生或服务）")
    entity_type: Optional[str] = Field(default=None, description="实体类型：'doctor', 'clinic', 'service'")
    specific_query: Optional[str] = Field(default=None, description="具体查询，如'周末营业吗'")


class EmergencyHandlerArgs(BaseModel):
    """Arguments for emergency situations"""
    emergency_type: str = Field(
        description="紧急类型：'medical'（医疗紧急）, 'consultation'（紧急咨询）, 'hotline'（热线）"
    )
    symptoms: Optional[List[str]] = Field(default=None, description="紧急症状")
    location: Optional[str] = Field(default=None, description="当前位置")
    contact_method: Optional[str] = Field(
        default="phone",
        description="联系方式：'phone'（电话）, 'video'（视频）, 'chat'（聊天）"
    )


class ConversationMemoryArgs(BaseModel):
    """Arguments for conversation memory operations"""
    action: str = Field(
        description="操作：'save'（保存）, 'retrieve'（检索）, 'update'（更新）, 'summarize'（总结）"
    )
    user_id: str = Field(description="用户ID")
    memory_type: Optional[str] = Field(
        default="general",
        description="记忆类型：'medical_history', 'preferences', 'appointments', 'general'"
    )
    content: Optional[Dict[str, Any]] = Field(default=None, description="要保存的内容")
    time_range: Optional[str] = Field(default=None, description="时间范围，用于检索")


# ===== CONSOLIDATED TOOL MANAGER =====

class ConsolidatedHumansaTools:
    """Consolidated tool manager with 7 core functions"""
    
    def __init__(self, memory_manager=None):
        self.memory_manager = memory_manager
        self.date_parser = ChineseDateParser()
        logger.info("✅ Initialized ConsolidatedHumansaTools with 7 core functions")
    
    def get_llamaindex_tools(self) -> List[FunctionTool]:
        """Get all 7 consolidated tools as LlamaIndex FunctionTools"""
        if not LLAMAINDEX_AVAILABLE:
            logger.error("❌ LlamaIndex not available - cannot create tools")
            return []
        
        tools = [
            FunctionTool.from_defaults(
                fn=self.unified_search,
                name="unified_search",
                description="统一搜索工具：查找医生、诊所、服务。智能识别搜索意图，支持模糊匹配。可按城市、专科、日期筛选。返回相关度最高的结果。",
                fn_schema=UnifiedSearchArgs
            ),
            FunctionTool.from_defaults(
                fn=self.appointment_manager,
                name="appointment_manager",
                description="预约管理工具：处理所有预约相关操作。包括检查预约信息、创建预约、改期、取消、查询历史。自动验证信息完整性。",
                fn_schema=AppointmentManagerArgs
            ),
            FunctionTool.from_defaults(
                fn=self.medical_advisor,
                name="medical_advisor",
                description="医疗咨询工具：提供症状评估、健康建议、科室推荐。基于症状严重程度给出就医建议。考虑患者年龄、病史、用药情况。",
                fn_schema=MedicalAdvisorArgs
            ),
            FunctionTool.from_defaults(
                fn=self.product_recommender,
                name="product_recommender",
                description="产品推荐工具：推荐保健品、医疗器械、护肤品等。基于健康状况、预算、偏好给出个性化推荐。",
                fn_schema=ProductRecommenderArgs
            ),
            FunctionTool.from_defaults(
                fn=self.information_lookup,
                name="information_lookup",
                description="信息查询工具：查询价格、营业时间、联系方式、保险、地址等基础信息。支持诊所、医生、服务的信息查询。",
                fn_schema=InformationLookupArgs
            ),
            FunctionTool.from_defaults(
                fn=self.emergency_handler,
                name="emergency_handler",
                description="紧急处理工具：处理医疗紧急情况、紧急咨询需求、热线连接。提供紧急联系方式和初步指导。",
                fn_schema=EmergencyHandlerArgs
            ),
            FunctionTool.from_defaults(
                fn=self.conversation_memory,
                name="conversation_memory",
                description="对话记忆工具：保存和检索用户医疗信息、偏好、预约历史。支持对话总结和上下文管理。",
                fn_schema=ConversationMemoryArgs
            )
        ]
        
        logger.info(f"✅ Created {len(tools)} consolidated LlamaIndex tools")
        return tools
    
    # ===== TOOL IMPLEMENTATIONS =====
    
    async def unified_search(
        self,
        query: str,
        search_type: Optional[str] = None,
        city: Optional[str] = None,
        specialty: Optional[str] = None,
        date_range: Optional[str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Unified search across doctors, clinics, and services with intelligent routing
        """
        logger.info(f"🔍 Unified search: query='{query}', type={search_type}, city={city}")
        
        try:
            results = {
                "success": True,
                "query": query,
                "results": []
            }
            
            # Determine search type from query if not specified
            if not search_type:
                query_lower = query.lower()
                if any(term in query_lower for term in ['医生', '大夫', 'doctor', 'dr']):
                    search_type = 'doctor'
                elif any(term in query_lower for term in ['诊所', '医院', 'clinic', '门诊']):
                    search_type = 'clinic'
                elif any(term in query_lower for term in ['检查', '体检', '化验', 'service', '服务']):
                    search_type = 'service'
            
            # Perform appropriate search
            if search_type == 'doctor' or search_type is None:
                doctors = db.search_doctors_with_fallback(
                    name=query if search_type == 'doctor' else None,
                    specialty=specialty or query if not search_type else specialty,
                    city=city,
                    limit=limit
                )
                for doc in doctors:
                    results["results"].append({
                        "type": "doctor",
                        "name": doc.get("name"),
                        "specialty": doc.get("specialty"),
                        "clinic": doc.get("clinic_name"),
                        "price": doc.get("registration_fee"),
                        "city": doc.get("city"),
                        "availability": "Available" if date_range else "Check availability"
                    })
            
            if search_type == 'clinic' or search_type is None:
                clinic_result = db.search_clinics_with_fallback(
                    clinic_name=query if search_type == 'clinic' else None,
                    city=city,
                    specialty=specialty,
                    limit=limit
                )
                if clinic_result['clinics_found']:
                    for clinic in clinic_result['clinics']:
                        results["results"].append({
                            "type": "clinic",
                            "name": clinic.get("name"),
                            "address": clinic.get("address"),
                            "city": clinic.get("city"),
                            "phone": clinic.get("phone"),
                            "specialties": clinic.get("specialties", [])
                        })
            
            if search_type == 'service' or search_type is None:
                service_result = db.search_services_with_fallback(
                    service_name=query if search_type == 'service' else None,
                    specialty=specialty,
                    clinic_name=None,
                    limit=limit
                )
                if service_result['services_found']:
                    for service in service_result['services']:
                        results["results"].append({
                            "type": "service",
                            "name": service.get("name"),
                            "category": service.get("category"),
                            "price": service.get("price"),
                            "clinic": service.get("clinic_name"),
                            "description": service.get("description")
                        })
            
            results["total_found"] = len(results["results"])
            results["message"] = f"Found {results['total_found']} results for '{query}'"
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Unified search error: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": []
            }
    
    async def appointment_manager(
        self,
        action: str,
        doctor_name: Optional[str] = None,
        patient_name: Optional[str] = None,
        phone: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        appointment_id: Optional[str] = None,
        new_date: Optional[str] = None,
        new_time: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage all appointment-related operations
        """
        logger.info(f"📅 Appointment manager: action={action}")
        
        try:
            if action == "check":
                # Check what information is missing for booking
                missing = []
                if not doctor_name:
                    missing.append("医生姓名")
                if not patient_name:
                    missing.append("患者姓名")
                if not phone:
                    missing.append("联系电话")
                if not date:
                    missing.append("预约日期")
                if not time:
                    missing.append("预约时间")
                
                if missing:
                    return {
                        "success": True,
                        "action": "check",
                        "status": "incomplete",
                        "missing_info": missing,
                        "message": f"预约需要以下信息：{', '.join(missing)}"
                    }
                else:
                    return {
                        "success": True,
                        "action": "check",
                        "status": "complete",
                        "message": "所有预约信息已齐全，可以进行预约"
                    }
            
            elif action == "book":
                # Simulate booking
                if not all([doctor_name, patient_name, phone, date, time]):
                    return {
                        "success": False,
                        "error": "预约信息不完整，请先使用 action='check' 检查"
                    }
                
                # Parse date if needed
                parsed_date = self.date_parser.parse_chinese_date(date) if date else None
                
                return {
                    "success": True,
                    "action": "book",
                    "appointment_id": f"APT{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "doctor": doctor_name,
                    "patient": patient_name,
                    "phone": phone,
                    "date": parsed_date.strftime('%Y-%m-%d') if parsed_date else date,
                    "time": time,
                    "status": "confirmed",
                    "message": f"预约成功！已为{patient_name}预约{doctor_name}医生，时间：{date} {time}"
                }
            
            elif action == "reschedule":
                if not appointment_id:
                    return {
                        "success": False,
                        "error": "需要提供预约号或手机号"
                    }
                
                return {
                    "success": True,
                    "action": "reschedule",
                    "appointment_id": appointment_id,
                    "old_date": date,
                    "new_date": new_date,
                    "new_time": new_time,
                    "status": "rescheduled",
                    "message": f"预约已成功改期至 {new_date} {new_time}"
                }
            
            elif action == "cancel":
                if not (appointment_id or phone):
                    return {
                        "success": False,
                        "error": "需要提供预约号或手机号"
                    }
                
                return {
                    "success": True,
                    "action": "cancel",
                    "appointment_id": appointment_id,
                    "reason": reason,
                    "status": "cancelled",
                    "message": "预约已成功取消"
                }
            
            elif action == "history":
                if not phone:
                    return {
                        "success": False,
                        "error": "需要提供手机号查询预约历史"
                    }
                
                # Simulate appointment history
                return {
                    "success": True,
                    "action": "history",
                    "phone": phone,
                    "appointments": [
                        {
                            "appointment_id": "APT20240115093000",
                            "doctor": "张医生",
                            "date": "2024-01-15",
                            "time": "09:30",
                            "status": "completed"
                        }
                    ],
                    "message": f"找到 1 条预约记录"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"不支持的操作: {action}"
                }
                
        except Exception as e:
            logger.error(f"❌ Appointment manager error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def medical_advisor(
        self,
        symptoms: List[str],
        duration: Optional[str] = None,
        severity: Optional[str] = None,
        patient_age: Optional[int] = None,
        medical_history: Optional[List[str]] = None,
        current_medications: Optional[List[str]] = None,
        allergies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Provide medical consultation and triage advice
        """
        logger.info(f"🏥 Medical advisor: symptoms={symptoms}, severity={severity}")
        
        try:
            # Analyze symptoms
            urgent_symptoms = ['胸痛', '呼吸困难', '意识不清', '大出血', '严重头痛']
            is_urgent = any(symptom in urgent_symptoms for symptom in symptoms)
            
            # Determine recommended department
            department_map = {
                '头痛': '神经内科',
                '胸痛': '心内科',
                '咳嗽': '呼吸科',
                '腹痛': '消化科',
                '关节痛': '骨科',
                '皮疹': '皮肤科',
                '失眠': '神经内科',
                '焦虑': '心理科'
            }
            
            recommended_dept = None
            for symptom in symptoms:
                for key, dept in department_map.items():
                    if key in symptom:
                        recommended_dept = dept
                        break
                if recommended_dept:
                    break
            
            # Build advice
            advice = {
                "success": True,
                "symptoms_analysis": {
                    "symptoms": symptoms,
                    "duration": duration,
                    "severity": severity or "未指定",
                    "is_urgent": is_urgent
                },
                "patient_info": {
                    "age": patient_age,
                    "medical_history": medical_history or [],
                    "current_medications": current_medications or [],
                    "allergies": allergies or []
                },
                "recommendation": {
                    "urgency": "紧急" if is_urgent else "常规",
                    "department": recommended_dept or "全科",
                    "action": "立即就医" if is_urgent else "预约门诊"
                }
            }
            
            # Add specific advice
            if is_urgent:
                advice["recommendation"]["message"] = "您的症状可能需要紧急医疗处理，建议立即前往急诊或拨打120"
            else:
                advice["recommendation"]["message"] = f"建议您预约{recommended_dept or '全科'}门诊进行详细检查"
            
            # Add precautions based on medical history
            if medical_history:
                if '高血压' in medical_history and '头痛' in symptoms:
                    advice["precautions"] = ["请监测血压", "避免情绪激动"]
                elif '糖尿病' in medical_history:
                    advice["precautions"] = ["注意血糖监测", "按时用药"]
            
            return advice
            
        except Exception as e:
            logger.error(f"❌ Medical advisor error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def product_recommender(
        self,
        category: Optional[str] = None,
        condition: Optional[str] = None,
        budget: Optional[str] = None,
        preferences: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recommend health products based on needs and preferences
        """
        logger.info(f"🛍️ Product recommender: category={category}, condition={condition}")
        
        try:
            # Sample product database
            products = {
                "supplements": [
                    {
                        "name": "综合维生素片",
                        "category": "保健品",
                        "price": 168,
                        "benefits": ["增强免疫力", "补充营养"],
                        "suitable_for": ["亚健康", "营养不良"]
                    },
                    {
                        "name": "褪黑素片",
                        "category": "保健品",
                        "price": 98,
                        "benefits": ["改善睡眠", "调节生物钟"],
                        "suitable_for": ["失眠", "时差"]
                    }
                ],
                "devices": [
                    {
                        "name": "电子血压计",
                        "category": "医疗器械",
                        "price": 299,
                        "benefits": ["监测血压", "心率检测"],
                        "suitable_for": ["高血压", "心脏病"]
                    }
                ]
            }
            
            # Filter products based on criteria
            recommendations = []
            
            # If specific condition mentioned
            if condition:
                condition_lower = condition.lower()
                for category_products in products.values():
                    for product in category_products:
                        if any(condition_lower in suit.lower() for suit in product['suitable_for']):
                            recommendations.append(product)
            
            # If no specific matches, return popular products
            if not recommendations:
                for category_products in products.values():
                    recommendations.extend(category_products[:2])
            
            # Apply budget filter if provided
            if budget:
                try:
                    budget_parts = budget.split('-')
                    if len(budget_parts) == 2:
                        min_budget = int(budget_parts[0])
                        max_budget = int(budget_parts[1])
                        recommendations = [
                            p for p in recommendations 
                            if min_budget <= p['price'] <= max_budget
                        ]
                except:
                    pass
            
            return {
                "success": True,
                "condition": condition,
                "recommendations": recommendations[:5],
                "total_found": len(recommendations),
                "message": f"为您推荐了 {len(recommendations[:5])} 个产品"
            }
            
        except Exception as e:
            logger.error(f"❌ Product recommender error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def information_lookup(
        self,
        info_type: str,
        entity_name: Optional[str] = None,
        entity_type: Optional[str] = None,
        specific_query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Look up general information like pricing, hours, contacts
        """
        logger.info(f"ℹ️ Information lookup: type={info_type}, entity={entity_name}")
        
        try:
            result = {
                "success": True,
                "info_type": info_type,
                "entity_name": entity_name
            }
            
            if info_type == "pricing":
                # Get pricing information
                if entity_type == "doctor":
                    doctors = db.search_doctors_with_fallback(name=entity_name, limit=1)
                    if doctors:
                        result["pricing"] = {
                            "registration_fee": doctors[0].get("registration_fee", "未知"),
                            "consultation_fee": "咨询费用请询问前台"
                        }
                    else:
                        result["message"] = "未找到该医生的价格信息"
                
                elif entity_type == "service":
                    services = db.search_services_with_fallback(service_name=entity_name, limit=1)
                    if services:
                        result["pricing"] = {
                            "service_fee": services[0].get("price", "未知"),
                            "description": services[0].get("description", "")
                        }
                    else:
                        result["message"] = "未找到该服务的价格信息"
                
            elif info_type == "hours":
                # Standard clinic hours
                result["hours"] = {
                    "weekdays": "周一至周五 8:00-18:00",
                    "saturday": "周六 8:00-12:00",
                    "sunday": "周日 休息",
                    "holidays": "节假日时间请电话咨询"
                }
                
            elif info_type == "contact":
                # Get contact information
                if entity_name:
                    clinics = db.search_clinics_with_fallback(clinic_name=entity_name, limit=1)
                    if clinics and clinics['clinics_found']:
                        clinic = clinics['clinics'][0]
                        result["contact"] = {
                            "phone": clinic.get("phone", "未知"),
                            "address": clinic.get("address", "未知"),
                            "email": "info@humansa.com"
                        }
                else:
                    result["contact"] = {
                        "hotline": "400-888-9999",
                        "email": "support@humansa.com",
                        "wechat": "Humansa健康"
                    }
                    
            elif info_type == "insurance":
                result["insurance"] = {
                    "accepted": ["基本医保", "商业保险"],
                    "coverage": "部分项目可使用医保，详情请咨询",
                    "reimbursement": "支持商业保险直付"
                }
                
            elif info_type == "location":
                if entity_name:
                    clinics = db.search_clinics_with_fallback(clinic_name=entity_name, limit=1)
                    if clinics and clinics['clinics_found']:
                        clinic = clinics['clinics'][0]
                        result["location"] = {
                            "address": clinic.get("address", "未知"),
                            "city": clinic.get("city", "未知"),
                            "transportation": "地铁/公交可达，提供停车位"
                        }
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Information lookup error: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def emergency_handler(
        self,
        emergency_type: str,
        symptoms: Optional[List[str]] = None,
        location: Optional[str] = None,
        contact_method: Optional[str] = "phone"
    ) -> Dict[str, Any]:
        """
        Handle emergency situations with appropriate responses
        """
        logger.info(f"🚨 Emergency handler: type={emergency_type}, symptoms={symptoms}")
        
        try:
            response = {
                "success": True,
                "emergency_type": emergency_type,
                "priority": "high"
            }
            
            if emergency_type == "medical":
                # Assess severity
                critical_symptoms = ['胸痛', '呼吸困难', '意识不清', '大出血']
                is_critical = symptoms and any(s in critical_symptoms for s in symptoms)
                
                if is_critical:
                    response["action"] = "immediate"
                    response["instructions"] = [
                        "立即拨打 120 急救电话",
                        "保持冷静，不要移动患者",
                        "记录症状开始时间"
                    ]
                    response["emergency_contacts"] = {
                        "急救": "120",
                        "Humansa急诊": "400-888-9999"
                    }
                else:
                    response["action"] = "urgent_consultation"
                    response["instructions"] = [
                        "尽快前往就近急诊",
                        "或联系Humansa紧急咨询热线"
                    ]
                    response["emergency_contacts"] = {
                        "Humansa热线": "400-888-9999",
                        "就近急诊": "请前往最近的医院急诊科"
                    }
                    
            elif emergency_type == "consultation":
                response["action"] = "connect_doctor"
                response["available_options"] = {
                    "phone": "电话咨询（5分钟内接通）",
                    "video": "视频问诊（10分钟内接通）",
                    "chat": "在线聊天（立即开始）"
                }
                response["contact_info"] = {
                    "hotline": "400-888-9999",
                    "online": "app.humansa.com/emergency"
                }
                
            elif emergency_type == "hotline":
                response["hotlines"] = {
                    "医疗急救": "120",
                    "Humansa 24小时热线": "400-888-9999",
                    "心理危机干预": "400-161-9995",
                    "中毒咨询": "010-83132345"
                }
                
            return response
            
        except Exception as e:
            logger.error(f"❌ Emergency handler error: {e}")
            return {
                "success": False,
                "error": str(e),
                "fallback_contact": "400-888-9999"
            }
    
    async def conversation_memory(
        self,
        action: str,
        user_id: str,
        memory_type: Optional[str] = "general",
        content: Optional[Dict[str, Any]] = None,
        time_range: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Manage conversation memory and context
        """
        logger.info(f"💭 Conversation memory: action={action}, user={user_id}, type={memory_type}")
        
        try:
            if not self.memory_manager:
                return {
                    "success": False,
                    "error": "Memory manager not initialized"
                }
            
            if action == "save":
                if not content:
                    return {
                        "success": False,
                        "error": "No content provided to save"
                    }
                
                # Save to memory
                memory_id = await self.memory_manager.store_memory(
                    user_id=user_id,
                    memory_type=memory_type,
                    content=content
                )
                
                return {
                    "success": True,
                    "action": "save",
                    "memory_id": memory_id,
                    "message": f"Successfully saved {memory_type} memory"
                }
                
            elif action == "retrieve":
                # Retrieve memories
                memories = await self.memory_manager.retrieve_memories(
                    user_id=user_id,
                    memory_type=memory_type,
                    time_range=time_range
                )
                
                return {
                    "success": True,
                    "action": "retrieve",
                    "memories": memories,
                    "count": len(memories),
                    "message": f"Retrieved {len(memories)} memories"
                }
                
            elif action == "update":
                if not content or 'memory_id' not in content:
                    return {
                        "success": False,
                        "error": "Memory ID and content required for update"
                    }
                
                success = await self.memory_manager.update_memory(
                    memory_id=content['memory_id'],
                    updates=content
                )
                
                return {
                    "success": success,
                    "action": "update",
                    "message": "Memory updated successfully" if success else "Failed to update memory"
                }
                
            elif action == "summarize":
                # Get conversation summary
                summary = await self.memory_manager.get_conversation_summary(
                    user_id=user_id,
                    time_range=time_range
                )
                
                return {
                    "success": True,
                    "action": "summarize",
                    "summary": summary,
                    "message": "Generated conversation summary"
                }
                
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}"
                }
                
        except Exception as e:
            logger.error(f"❌ Conversation memory error: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# ===== DYNAMIC TOOL LOADER =====

class DynamicToolLoader:
    """Dynamically load tools based on query context"""
    
    def __init__(self, tool_manager: ConsolidatedHumansaTools):
        self.tool_manager = tool_manager
        self.all_tools = tool_manager.get_llamaindex_tools()
        self.tool_map = {tool.name: tool for tool in self.all_tools}
        
    def select_tools_for_query(self, query: str, max_tools: int = 5) -> List[FunctionTool]:
        """Select relevant tools based on query content"""
        query_lower = query.lower()
        selected_tools = []
        
        # Always include unified search and conversation memory
        base_tools = ['unified_search', 'conversation_memory']
        
        # Context-based tool selection
        tool_keywords = {
            'appointment_manager': ['预约', '挂号', '改期', '取消', 'appointment', 'book'],
            'medical_advisor': ['症状', '疼', '不舒服', '生病', '咨询', 'symptom'],
            'product_recommender': ['产品', '保健品', '推荐', '购买', 'product'],
            'information_lookup': ['价格', '营业时间', '地址', '电话', '保险', 'price', 'hours'],
            'emergency_handler': ['紧急', '急诊', '120', '急救', 'emergency']
        }
        
        # Add base tools
        for tool_name in base_tools:
            if tool_name in self.tool_map:
                selected_tools.append(self.tool_map[tool_name])
        
        # Add context-specific tools
        for tool_name, keywords in tool_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                if tool_name in self.tool_map and self.tool_map[tool_name] not in selected_tools:
                    selected_tools.append(self.tool_map[tool_name])
                    if len(selected_tools) >= max_tools:
                        break
        
        # If still under limit, add remaining tools by priority
        priority_order = ['appointment_manager', 'medical_advisor', 'information_lookup']
        for tool_name in priority_order:
            if len(selected_tools) < max_tools and tool_name in self.tool_map:
                if self.tool_map[tool_name] not in selected_tools:
                    selected_tools.append(self.tool_map[tool_name])
        
        logger.info(f"🎯 Selected {len(selected_tools)} tools for query: {[t.name for t in selected_tools]}")
        return selected_tools