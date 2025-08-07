"""
Form Filling Agent - Intelligent form completion from natural language
"""
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FormFillingAgent:
    """
    Agent responsible for intelligently filling forms from natural language input
    This is the "brain" that understands user intent and maps it to form fields
    """
    
    def __init__(self):
        # Mock doctor database (in production, this would query real database)
        self.doctors = {
            "李明": {"id": "doc_001", "name": "李明医生", "department": "内科", "title": "主任医师"},
            "张伟": {"id": "doc_002", "name": "张伟医生", "department": "外科", "title": "副主任医师"},
            "王芳": {"id": "doc_003", "name": "王芳医生", "department": "儿科", "title": "主治医师"},
            "刘洋": {"id": "doc_004", "name": "刘洋医生", "department": "皮肤科", "title": "主任医师"},
            "陈静": {"id": "doc_005", "name": "陈静医生", "department": "妇科", "title": "副主任医师"},
        }
        
        # Department mapping
        self.department_keywords = {
            "内科": ["内科", "感冒", "发烧", "咳嗽", "头痛", "胃痛", "心脏"],
            "外科": ["外科", "外伤", "骨折", "手术"],
            "儿科": ["儿科", "小孩", "儿童", "宝宝", "孩子"],
            "皮肤科": ["皮肤", "过敏", "湿疹", "痘痘", "皮疹"],
            "妇科": ["妇科", "妇产", "月经", "孕"],
            "眼科": ["眼科", "眼睛", "视力", "近视"],
            "耳鼻喉科": ["耳鼻喉", "耳朵", "鼻子", "喉咙", "听力"],
        }
        
    def fill_form_from_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main method to fill form from natural language query
        Returns a dictionary of extracted form fields
        """
        logger.info(f"🤖 Form Filling Agent processing: {query}")
        
        # Initialize form data
        form_data = {
            "extraction_confidence": 0.0,
            "missing_fields": [],
            "suggestions": []
        }
        
        # Step 1: Extract doctor information
        doctor_info = self._extract_doctor(query)
        if doctor_info:
            form_data.update(doctor_info)
            form_data["extraction_confidence"] += 0.25
        else:
            form_data["missing_fields"].append("doctor")
            
        # Step 2: Extract date and time
        date_info = self._extract_date(query)
        if date_info:
            form_data.update(date_info)
            form_data["extraction_confidence"] += 0.25
        else:
            form_data["missing_fields"].append("appointment_date")
            
        time_info = self._extract_time(query)
        if time_info:
            form_data.update(time_info)
            form_data["extraction_confidence"] += 0.25
        else:
            form_data["missing_fields"].append("appointment_time")
            
        # Step 3: Extract symptoms
        symptoms = self._extract_symptoms(query)
        if symptoms:
            form_data["symptoms"] = symptoms
            form_data["extraction_confidence"] += 0.15
        else:
            form_data["missing_fields"].append("symptoms")
            
        # Step 4: Extract department (if no doctor specified)
        if "doctor_name" not in form_data:
            department = self._extract_department(query)
            if department:
                form_data["department"] = department
                form_data["extraction_confidence"] += 0.1
                # Suggest doctors from this department
                form_data["suggestions"].append({
                    "type": "doctor_recommendation",
                    "doctors": self._get_doctors_by_department(department)
                })
        
        # Step 5: Extract urgency
        is_urgent = self._extract_urgency(query)
        form_data["is_urgent"] = is_urgent
        
        # Step 6: Extract patient information
        patient_info = self._extract_patient_info(query)
        if patient_info:
            form_data.update(patient_info)
            if "patient_name" in patient_info:
                form_data["extraction_confidence"] += 0.1
            if "patient_phone" in patient_info:
                form_data["extraction_confidence"] += 0.1
        else:
            if "patient_name" not in form_data:
                form_data["missing_fields"].append("patient_name")
            if "patient_phone" not in form_data:
                form_data["missing_fields"].append("patient_phone")
        
        # Step 7: Apply context if provided
        if context:
            form_data = self._apply_context(form_data, context)
        
        # Step 7: Generate intelligent suggestions
        form_data["suggestions"].extend(self._generate_suggestions(form_data, query))
        
        logger.info(f"✅ Form filled with confidence: {form_data['extraction_confidence']:.0%}")
        logger.info(f"   Extracted fields: {[k for k in form_data.keys() if k not in ['extraction_confidence', 'missing_fields', 'suggestions']]}")
        logger.info(f"   Missing fields: {form_data['missing_fields']}")
        
        return form_data
    
    def _extract_doctor(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract doctor information from query"""
        # Pattern 1: Direct doctor name mention
        patterns = [
            r'(?:找|看|预约|挂)(.{1,3})(?:医生|大夫|医师)',
            r'(.{1,3})(?:医生|大夫|医师)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, query)
            if match:
                doctor_name = match.group(1)
                # Look up in database
                if doctor_name in self.doctors:
                    doctor = self.doctors[doctor_name]
                    return {
                        "doctor_id": doctor["id"],
                        "doctor_name": doctor["name"],
                        "department": doctor["department"],
                        "doctor_title": doctor["title"]
                    }
                else:
                    # Unknown doctor, but we captured the name
                    return {
                        "doctor_name": f"{doctor_name}医生",
                        "doctor_search_needed": True
                    }
        
        return None
    
    def _extract_date(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract appointment date from query"""
        today = datetime.now().date()
        
        # Relative dates
        if "今天" in query:
            return {"appointment_date": today.isoformat()}
        elif "明天" in query:
            return {"appointment_date": (today + timedelta(days=1)).isoformat()}
        elif "后天" in query:
            return {"appointment_date": (today + timedelta(days=2)).isoformat()}
        elif "大后天" in query:
            return {"appointment_date": (today + timedelta(days=3)).isoformat()}
        
        # Next week patterns
        weekday_map = {
            '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6
        }
        
        next_week_match = re.search(r'下周([一二三四五六日天])', query)
        if next_week_match:
            target_weekday = weekday_map[next_week_match.group(1)]
            days_ahead = target_weekday - today.weekday() + 7
            return {"appointment_date": (today + timedelta(days=days_ahead)).isoformat()}
        
        # This week patterns
        this_week_match = re.search(r'(?:这)?周([一二三四五六日天])', query)
        if this_week_match:
            target_weekday = weekday_map[this_week_match.group(1)]
            days_ahead = target_weekday - today.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            return {"appointment_date": (today + timedelta(days=days_ahead)).isoformat()}
        
        # Specific date patterns
        date_match = re.search(r'(\d{1,2})月(\d{1,2})[日号]', query)
        if date_match:
            month = int(date_match.group(1))
            day = int(date_match.group(2))
            year = today.year
            try:
                target_date = datetime(year, month, day).date()
                if target_date < today:
                    target_date = datetime(year + 1, month, day).date()
                return {"appointment_date": target_date.isoformat()}
            except:
                pass
        
        return None
    
    def _extract_time(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract appointment time from query"""
        # Morning/afternoon with hour
        morning_match = re.search(r'上午(\d{1,2})点', query)
        if morning_match:
            hour = int(morning_match.group(1))
            return {"appointment_time": f"{hour:02d}:00"}
        
        afternoon_match = re.search(r'下午(\d{1,2})点', query)
        if afternoon_match:
            hour = int(afternoon_match.group(1))
            if hour < 12:
                hour += 12
            return {"appointment_time": f"{hour:02d}:00"}
        
        # Specific time format
        time_match = re.search(r'(\d{1,2}):(\d{2})', query)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2))
            return {"appointment_time": f"{hour:02d}:{minute:02d}"}
        
        # Hour only
        hour_match = re.search(r'(\d{1,2})点', query)
        if hour_match:
            hour = int(hour_match.group(1))
            return {"appointment_time": f"{hour:02d}:00"}
        
        # General time preferences
        if "上午" in query:
            return {"appointment_time": "09:00", "time_preference": "morning"}
        elif "下午" in query:
            return {"appointment_time": "14:00", "time_preference": "afternoon"}
        elif "晚上" in query:
            return {"appointment_time": "18:00", "time_preference": "evening"}
        
        return None
    
    def _extract_symptoms(self, query: str) -> Optional[str]:
        """Extract symptoms from query"""
        # Direct symptom patterns
        symptom_patterns = [
            r'症状[是为：:](.+?)(?:[，。,.]|$)',
            r'[我有](.+?)[的]?症状',
            r'感[觉到](.+?)(?:[，。,.]|$)',
            r'最近(.+?)(?:[，。,.]|想|要)',
        ]
        
        for pattern in symptom_patterns:
            match = re.search(pattern, query)
            if match:
                return match.group(1).strip()
        
        # Common symptoms keywords
        symptom_keywords = [
            "头痛", "头疼", "发烧", "发热", "咳嗽", "流鼻涕", "鼻塞",
            "喉咙痛", "胃痛", "腹痛", "拉肚子", "腹泻", "恶心", "呕吐",
            "胸闷", "心慌", "失眠", "疲劳", "乏力", "头晕", "耳鸣",
            "皮疹", "过敏", "瘙痒", "疼痛", "酸痛", "肿胀"
        ]
        
        found_symptoms = []
        for symptom in symptom_keywords:
            if symptom in query:
                found_symptoms.append(symptom)
        
        if found_symptoms:
            return "、".join(found_symptoms)
        
        return None
    
    def _extract_department(self, query: str) -> Optional[str]:
        """Extract department from query based on keywords"""
        for dept, keywords in self.department_keywords.items():
            for keyword in keywords:
                if keyword in query:
                    return dept
        return None
    
    def _extract_urgency(self, query: str) -> bool:
        """Determine if appointment is urgent"""
        urgent_keywords = ["紧急", "急", "马上", "立即", "赶紧", "尽快", "很严重", "严重"]
        return any(keyword in query for keyword in urgent_keywords)
    
    def _extract_patient_info(self, query: str) -> Optional[Dict[str, Any]]:
        """Extract patient name and phone from query"""
        info = {}
        
        # Extract name patterns
        # Pattern 1: 我叫XXX
        name_match1 = re.search(r'我叫([^，。,\s]+)', query)
        # Pattern 2: 我是XXX
        name_match2 = re.search(r'我是([^，。,\s]+)', query)
        # Pattern 3: 姓名：XXX or 姓名:XXX
        name_match3 = re.search(r'姓名[:：]([^，。,\s]+)', query)
        
        if name_match1:
            info["patient_name"] = name_match1.group(1)
        elif name_match2:
            info["patient_name"] = name_match2.group(1)
        elif name_match3:
            info["patient_name"] = name_match3.group(1)
        
        # Extract phone patterns
        # Pattern 1: 11-digit mobile number
        phone_match = re.search(r'1[3-9]\d{9}', query)
        # Pattern 2: 电话：XXX
        phone_match2 = re.search(r'电话[:：]?\s*(\d{11})', query)
        
        if phone_match:
            info["patient_phone"] = phone_match.group(0)
        elif phone_match2:
            info["patient_phone"] = phone_match2.group(1)
        
        return info if info else None
    
    def _get_doctors_by_department(self, department: str) -> List[Dict[str, Any]]:
        """Get doctors in a specific department"""
        doctors = []
        for name, info in self.doctors.items():
            if info["department"] == department:
                doctors.append({
                    "id": info["id"],
                    "name": info["name"],
                    "title": info["title"]
                })
        return doctors
    
    def _apply_context(self, form_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Apply context information to form data"""
        # Apply user preferences
        if "preferred_doctor" in context and "doctor_name" not in form_data:
            form_data["doctor_name"] = context["preferred_doctor"]
            form_data["extraction_confidence"] += 0.1
            
        # Apply medical history
        if "allergies" in context:
            form_data["known_allergies"] = context["allergies"]
            
        return form_data
    
    def _generate_suggestions(self, form_data: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
        """Generate intelligent suggestions based on extracted data"""
        suggestions = []
        
        # Suggest time slots if date but no time
        if "appointment_date" in form_data and "appointment_time" not in form_data:
            suggestions.append({
                "type": "time_slots",
                "message": "请选择就诊时间",
                "options": ["09:00", "10:00", "14:00", "15:00", "16:00"]
            })
        
        # Suggest symptom description if missing
        if "symptoms" not in form_data:
            suggestions.append({
                "type": "symptom_prompt",
                "message": "请描述您的症状，以便医生更好地准备"
            })
        
        # Suggest nearby dates if requested date might be full
        if form_data.get("appointment_date") == datetime.now().date().isoformat():
            suggestions.append({
                "type": "alternative_dates",
                "message": "今天号源可能紧张，也可查看其他日期",
                "options": [
                    (datetime.now() + timedelta(days=1)).date().isoformat(),
                    (datetime.now() + timedelta(days=2)).date().isoformat()
                ]
            })
        
        return suggestions


# Example usage
if __name__ == "__main__":
    agent = FormFillingAgent()
    
    # Test cases
    test_queries = [
        "我想预约李明医生看内科，明天上午9点",
        "头疼想看医生",
        "给孩子挂个儿科号，最近咳嗽",
        "下周二下午找刘洋医生看皮肤过敏",
        "紧急！胸闷心慌，需要马上看医生"
    ]
    
    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        result = agent.fill_form_from_query(query)
        
        print(f"Confidence: {result['extraction_confidence']:.0%}")
        print(f"Extracted:")
        for key, value in result.items():
            if key not in ['extraction_confidence', 'missing_fields', 'suggestions']:
                print(f"  {key}: {value}")
        
        if result['missing_fields']:
            print(f"Missing: {', '.join(result['missing_fields'])}")
            
        if result['suggestions']:
            print("Suggestions:")
            for suggestion in result['suggestions']:
                print(f"  - {suggestion['type']}: {suggestion.get('message', '')}")