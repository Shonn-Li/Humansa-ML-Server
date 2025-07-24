#!/usr/bin/env python3
"""
Comprehensive test suite for Humansa v2 - 20 test cases covering all scenarios.
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
import sys
import random

BASE_URL = "http://localhost:5001"

# Test user profiles
TEST_USERS = {
    "new_patient": {
        "user_id": "test_user_new_001",
        "profile": {
            "name": "John Tan",
            "age": 35,
            "gender": "Male",
            "email": "john.tan@test.com"
        }
    },
    "chronic_patient": {
        "user_id": "test_user_chronic_001",
        "profile": {
            "name": "Mary Lim",
            "age": 58,
            "gender": "Female",
            "email": "mary.lim@test.com"
        },
        "medical_history": [
            {"condition": "Type 2 Diabetes", "diagnosed": "2018-03-15"},
            {"condition": "Hypertension", "diagnosed": "2019-07-22"}
        ],
        "current_medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "twice daily"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "once daily"}
        ]
    },
    "elderly_patient": {
        "user_id": "test_user_elderly_001",
        "profile": {
            "name": "Robert Lee",
            "age": 72,
            "gender": "Male",
            "email": "robert.lee@test.com"
        },
        "medical_history": [
            {"condition": "Coronary Artery Disease", "diagnosed": "2015-11-20"},
            {"condition": "Osteoarthritis", "diagnosed": "2017-04-10"}
        ]
    }
}


class TestCase:
    def __init__(self, name, description, test_func):
        self.name = name
        self.description = description
        self.test_func = test_func
        self.result = None
        self.details = ""


async def make_request(method, endpoint, data=None, params=None):
    """Helper function to make HTTP requests."""
    async with aiohttp.ClientSession() as session:
        kwargs = {
            "headers": {"Content-Type": "application/json"}
        }
        if data:
            kwargs["json"] = data
        if params:
            kwargs["params"] = params
            
        async with session.request(method, f"{BASE_URL}{endpoint}", **kwargs) as response:
            response_data = None
            try:
                if response.content_type == 'application/json':
                    response_data = await response.json()
                else:
                    response_data = await response.text()
            except:
                response_data = None
            
            return {
                "status": response.status,
                "data": response_data,
                "headers": dict(response.headers)
            }


# Test Case 1: Basic health inquiry
async def test_basic_health_inquiry():
    """Test basic health question handling."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "What are the symptoms of high blood pressure?"}
        ],
        "stream": False
    })
    
    return response["status"] == 200 and "blood pressure" in str(response["data"]).lower()


# Test Case 2: Emergency symptom detection
async def test_emergency_detection():
    """Test emergency triage for severe symptoms."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": "test_emergency_001",
        "messages": [
            {"role": "user", "content": "I'm having severe chest pain and difficulty breathing"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = response["data"]
    
    # Should trigger emergency response
    is_emergency = any(word in str(data).lower() for word in ["emergency", "911", "immediate", "urgent"])
    return success and is_emergency


# Test Case 3: Doctor search by specialty
async def test_doctor_search_specialty():
    """Test searching for doctors by specialty."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "I need to find a cardiologist in the central region"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should return cardiologist information
    has_cardio = "cardio" in data
    has_doctor = "dr." in data or "doctor" in data
    return success and has_cardio and has_doctor


# Test Case 4: Doctor search by language preference
async def test_doctor_search_language():
    """Test searching for doctors by language."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "Find me a doctor who speaks Mandarin"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should return doctors who speak Mandarin
    has_mandarin = "mandarin" in data
    return success and has_mandarin


# Test Case 5: Appointment availability check
async def test_appointment_availability():
    """Test checking doctor availability."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "What appointments are available with Dr. Sarah Chen this week?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should show availability information
    has_availability = any(word in data for word in ["available", "appointment", "slot", "time"])
    return success and has_availability


# Test Case 6: Direct appointment booking
async def test_appointment_booking():
    """Test booking an appointment."""
    # First search for available slots
    search_response = await make_request("POST", "/v2/humansa/appointment/search", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "search_criteria": {
            "specialty": "General Practice",
            "date_preference": {
                "from": datetime.now().strftime("%Y-%m-%d"),
                "to": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            }
        }
    })
    
    return search_response["status"] == 200


# Test Case 7: Medication interaction check
async def test_medication_interaction():
    """Test medication interaction checking."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["chronic_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "Can I take aspirin with my current medications? I'm on Metformin and Lisinopril."}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should mention medications and interactions
    has_meds = all(med in data for med in ["metformin", "lisinopril"])
    has_interaction_info = any(word in data for word in ["interaction", "safe", "consult", "doctor"])
    return success and has_meds and has_interaction_info


# Test Case 8: Symptom analysis with history
async def test_symptom_analysis():
    """Test symptom analysis considering medical history."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["chronic_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "I've been feeling very thirsty and urinating frequently. My vision is also blurry."}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should recognize diabetes-related symptoms
    has_diabetes_mention = any(word in data for word in ["diabetes", "blood sugar", "glucose"])
    return success and has_diabetes_mention


# Test Case 9: Health screening package inquiry
async def test_health_screening_packages():
    """Test health screening package recommendations."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["elderly_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "What health screening packages do you recommend for someone my age?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should recommend screening packages
    has_screening = "screening" in data or "package" in data
    return success and has_screening


# Test Case 10: Clinic location search
async def test_clinic_location_search():
    """Test searching for clinics by location."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "Find me the nearest Humansa clinic in Tampines"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should return Tampines clinic information
    has_tampines = "tampines" in data
    has_address = "address" in data or "located" in data
    return success and has_tampines and has_address


# Test Case 11: Patient profile creation and update
async def test_patient_profile_management():
    """Test creating and updating patient profile."""
    user_id = "test_profile_mgmt_001"
    
    # Create profile
    create_response = await make_request("PUT", "/v2/humansa/patient/profile", {
        "user_id": user_id,
        "profile_data": {
            "name": "Test Patient",
            "age": 45,
            "gender": "Female",
            "phone": "+65 9123 4567"
        },
        "preferences": {
            "preferred_language": "English",
            "preferred_contact": "SMS"
        }
    })
    
    # Retrieve profile
    get_response = await make_request("GET", f"/v2/humansa/patient/profile?user_id={user_id}")
    
    return create_response["status"] == 200 and get_response["status"] == 200


# Test Case 12: Conversation history retrieval
async def test_conversation_history():
    """Test retrieving conversation history."""
    user_id = TEST_USERS["chronic_patient"]["user_id"]
    
    # Make a chat request first
    await make_request("POST", "/v2/humansa/chat", {
        "user_id": user_id,
        "messages": [
            {"role": "user", "content": "Test message for history"}
        ],
        "stream": False
    })
    
    # Retrieve history
    response = await make_request("GET", f"/v2/humansa/conversation/history?user_id={user_id}&limit=5")
    
    return response["status"] == 200


# Test Case 13: Multi-turn conversation
async def test_multi_turn_conversation():
    """Test multi-turn conversation with context."""
    user_id = "test_multi_turn_001"
    
    # First turn
    response1 = await make_request("POST", "/v2/humansa/chat", {
        "user_id": user_id,
        "messages": [
            {"role": "user", "content": "I have a headache"}
        ],
        "stream": False
    })
    
    # Second turn with context
    response2 = await make_request("POST", "/v2/humansa/chat", {
        "user_id": user_id,
        "messages": [
            {"role": "user", "content": "I have a headache"},
            {"role": "assistant", "content": response1["data"].get("response", "")},
            {"role": "user", "content": "It's been going on for 3 days now"}
        ],
        "stream": False
    })
    
    success = response1["status"] == 200 and response2["status"] == 200
    # Second response should show awareness of the 3-day duration
    has_context = "3 days" in str(response2["data"]).lower() or "three days" in str(response2["data"]).lower()
    
    return success and has_context


# Test Case 14: Telemedicine appointment preference
async def test_telemedicine_preference():
    """Test booking telemedicine appointments."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "I want to book a telemedicine consultation with a general practitioner"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should mention telemedicine options
    has_telemedicine = "telemedicine" in data or "video" in data or "online" in data
    return success and has_telemedicine


# Test Case 15: Service pricing inquiry
async def test_service_pricing():
    """Test service pricing inquiries."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "How much does a cardiology consultation cost?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should provide pricing information
    has_price = any(char in str(response["data"]) for char in ["$", "sgd", "price", "cost", "fee"])
    return success and has_price


# Test Case 16: Specialist referral request
async def test_specialist_referral():
    """Test specialist referral recommendations."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["chronic_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "My GP suggested I see an endocrinologist. Can you help me find one?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should provide endocrinologist information
    has_specialist = "endocrin" in data or "specialist" in data
    return success and has_specialist


# Test Case 17: Pediatric consultation
async def test_pediatric_consultation():
    """Test pediatric-specific queries."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": "test_parent_001",
        "messages": [
            {"role": "user", "content": "My 5-year-old has had a fever for 2 days. Should I be worried?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should provide pediatric advice
    has_child_info = any(word in data for word in ["child", "pediatric", "fever"])
    return success and has_child_info


# Test Case 18: Follow-up appointment booking
async def test_followup_appointment():
    """Test booking follow-up appointments."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["chronic_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "I need to book a follow-up appointment with Dr. Rajesh Kumar for my heart condition"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should recognize follow-up context
    has_followup = "follow" in data or "appointment" in data
    has_doctor = "rajesh" in data or "kumar" in data
    return success and (has_followup or has_doctor)


# Test Case 19: Insurance coverage inquiry
async def test_insurance_coverage():
    """Test insurance coverage questions."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["new_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "Does Humansa accept AIA insurance for specialist consultations?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should mention insurance
    has_insurance = "insurance" in data or "aia" in data or "coverage" in data
    return success and has_insurance


# Test Case 20: Complex multi-agent scenario
async def test_complex_multi_agent():
    """Test complex scenario requiring multiple agents."""
    response = await make_request("POST", "/v2/humansa/chat", {
        "user_id": TEST_USERS["elderly_patient"]["user_id"],
        "messages": [
            {"role": "user", "content": "I have chest pain when I walk up stairs. I'm on heart medication. Should I see my cardiologist Dr. Rajesh Kumar soon? Also, can I take aspirin for the pain?"}
        ],
        "stream": False
    })
    
    success = response["status"] == 200
    data = str(response["data"]).lower()
    
    # Should involve multiple agents (emergency, medication, appointment)
    has_urgency = any(word in data for word in ["soon", "immediate", "urgent"])
    has_medication = "aspirin" in data or "medication" in data
    has_cardio = "cardio" in data or "heart" in data
    
    return success and has_urgency and has_medication and has_cardio


async def run_all_tests():
    """Run all test cases."""
    test_cases = [
        TestCase("Basic Health Inquiry", "Test basic health question handling", test_basic_health_inquiry),
        TestCase("Emergency Detection", "Test emergency triage for severe symptoms", test_emergency_detection),
        TestCase("Doctor Search - Specialty", "Test searching doctors by specialty", test_doctor_search_specialty),
        TestCase("Doctor Search - Language", "Test searching doctors by language", test_doctor_search_language),
        TestCase("Appointment Availability", "Test checking doctor availability", test_appointment_availability),
        TestCase("Appointment Booking", "Test direct appointment booking", test_appointment_booking),
        TestCase("Medication Interaction", "Test medication interaction checking", test_medication_interaction),
        TestCase("Symptom Analysis", "Test symptom analysis with history", test_symptom_analysis),
        TestCase("Health Screening", "Test health screening recommendations", test_health_screening_packages),
        TestCase("Clinic Location", "Test clinic location search", test_clinic_location_search),
        TestCase("Profile Management", "Test patient profile CRUD operations", test_patient_profile_management),
        TestCase("Conversation History", "Test conversation history retrieval", test_conversation_history),
        TestCase("Multi-turn Chat", "Test multi-turn conversation context", test_multi_turn_conversation),
        TestCase("Telemedicine", "Test telemedicine appointment preference", test_telemedicine_preference),
        TestCase("Service Pricing", "Test service pricing inquiries", test_service_pricing),
        TestCase("Specialist Referral", "Test specialist referral flow", test_specialist_referral),
        TestCase("Pediatric Query", "Test pediatric consultation handling", test_pediatric_consultation),
        TestCase("Follow-up Booking", "Test follow-up appointment booking", test_followup_appointment),
        TestCase("Insurance Coverage", "Test insurance coverage questions", test_insurance_coverage),
        TestCase("Complex Multi-Agent", "Test complex multi-agent scenario", test_complex_multi_agent)
    ]
    
    print("🚀 Starting Humansa v2 Comprehensive Test Suite")
    print(f"📋 Running {len(test_cases)} test cases")
    print("=" * 70)
    
    # Check server connection
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{BASE_URL}/health") as response:
                if response.status != 200:
                    print("❌ Server is not running at", BASE_URL)
                    return
    except:
        print("❌ Cannot connect to server at", BASE_URL)
        return
    
    # Run tests
    passed = 0
    failed = 0
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📌 Test {i}/{len(test_cases)}: {test_case.name}")
        print(f"   Description: {test_case.description}")
        
        try:
            result = await test_case.test_func()
            test_case.result = "PASS" if result else "FAIL"
            
            if result:
                print(f"   ✅ Result: PASSED")
                passed += 1
            else:
                print(f"   ❌ Result: FAILED")
                failed += 1
                
        except Exception as e:
            test_case.result = "ERROR"
            test_case.details = str(e)
            print(f"   ❌ Result: ERROR - {e}")
            failed += 1
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 TEST SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(test_cases)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(test_cases)*100):.1f}%")
    
    # Detailed results
    print("\n📋 DETAILED RESULTS:")
    for i, test_case in enumerate(test_cases, 1):
        emoji = "✅" if test_case.result == "PASS" else "❌"
        print(f"{emoji} {i}. {test_case.name}: {test_case.result}")
        if test_case.details:
            print(f"      Details: {test_case.details}")


if __name__ == "__main__":
    asyncio.run(run_all_tests())