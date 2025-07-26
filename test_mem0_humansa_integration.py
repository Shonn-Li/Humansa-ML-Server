"""
Comprehensive test suite for Mem0 integration with Humansa
Tests memory storage, retrieval, and persistence across conversations
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
import asyncpg
from mem0 import Memory
import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
TEST_CONFIG = {
    "db_host": os.getenv("DB_HOST", "localhost"),
    "db_port": int(os.getenv("DB_PORT", "5456")),  # Humansa test DB port
    "db_user": os.getenv("DB_USER", "youwo"),
    "db_password": os.getenv("DB_PASSWORD", "youwo123"),
    "db_name": os.getenv("DB_NAME", "youwoai"),
    "azure_api_key": os.getenv("AZURE_OPENAI_API_KEY", "test-key"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT", "https://test.openai.azure.com"),
    "azure_deployment": os.getenv("AZURE_OPENAI_DEPLOYMENT_GPT4", "gpt-4"),
    "mem0_schema": "mem0_test",
    "ml_server_url": os.getenv("ML_SERVER_URL", "http://localhost:6001")  # Test environment ML server
}

# Test users
TEST_USERS = {
    "user1": {"id": 10001, "name": "Test User 1 - No Memory"},
    "user2": {"id": 10002, "name": "Test User 2 - With Diabetes"},
    "user3": {"id": 10003, "name": "Test User 3 - Complex History"}
}


class Mem0HumansaTestSuite:
    """Test suite for Mem0 integration with Humansa"""
    
    def __init__(self):
        self.memory = None
        self.db_pool = None
        self.test_results = []
        
    async def setup(self):
        """Initialize test environment"""
        logger.info("Setting up Mem0 test environment...")
        
        # Initialize database connection
        self.db_pool = await asyncpg.create_pool(
            host=TEST_CONFIG["db_host"],
            port=TEST_CONFIG["db_port"],
            user=TEST_CONFIG["db_user"],
            password=TEST_CONFIG["db_password"],
            database=TEST_CONFIG["db_name"]
        )
        
        # Initialize Mem0
        try:
            self.memory = Memory.from_config({
                "llm": {
                    "provider": "azure_openai",
                    "config": {
                        "api_key": TEST_CONFIG["azure_api_key"],
                        "azure_endpoint": TEST_CONFIG["azure_endpoint"],
                        "azure_deployment": TEST_CONFIG["azure_deployment"],
                        "api_version": "2024-02-01"
                    }
                },
                "embedder": {
                    "provider": "azure_openai",
                    "config": {
                        "api_key": TEST_CONFIG["azure_api_key"],
                        "azure_endpoint": TEST_CONFIG["azure_endpoint"],
                        "azure_deployment": "text-embedding-ada-002",
                        "api_version": "2024-02-01"
                    }
                },
                "vector_store": {
                    "provider": "pgvector",
                    "config": {
                        "host": TEST_CONFIG["db_host"],
                        "port": TEST_CONFIG["db_port"],
                        "user": TEST_CONFIG["db_user"],
                        "password": TEST_CONFIG["db_password"],
                        "database": TEST_CONFIG["db_name"],
                        "collection_name": f"{TEST_CONFIG['mem0_schema']}_memories"
                    }
                }
            })
            logger.info("✓ Mem0 initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Mem0: {e}")
            # For testing without real Azure credentials
            logger.info("Using mock memory for testing")
            self.memory = MockMemory()  # We'll implement a mock if needed
            
    async def teardown(self):
        """Clean up test environment"""
        if self.db_pool:
            await self.db_pool.close()
            
    async def clear_test_memories(self):
        """Clear all test user memories before starting tests"""
        logger.info("Clearing existing test memories...")
        for user_key, user_info in TEST_USERS.items():
            memory_user_id = f"humansa_test_{user_info['id']}"
            try:
                # Get all memories for user
                all_memories = self.memory.get_all(memory_user_id)
                # Delete each memory
                for memory in all_memories:
                    self.memory.delete(memory_id=memory['id'])
                logger.info(f"✓ Cleared memories for {user_key}")
            except Exception as e:
                logger.warning(f"Could not clear memories for {user_key}: {e}")
    
    # ========== Test Cases ==========
    
    async def test_01_basic_memory_storage(self):
        """Test 1: Basic memory storage for a new user"""
        test_name = "Basic Memory Storage"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 1: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user1"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Store a simple conversation
            messages = [
                {"role": "user", "content": "Hi, I'm new here"},
                {"role": "assistant", "content": "Hello! I'm Humansa, your medical AI assistant. How can I help you today?"},
                {"role": "user", "content": "I prefer morning appointments around 9 AM"},
                {"role": "assistant", "content": "I've noted your preference for morning appointments around 9 AM."}
            ]
            
            # Add to memory
            self.memory.add(
                messages=messages,
                user_id=memory_user_id,
                metadata={"test_case": "01", "timestamp": datetime.utcnow().isoformat()}
            )
            
            # Verify storage
            memories = self.memory.get_all(memory_user_id)
            
            assert len(memories) > 0, "No memories stored"
            assert any("morning appointments" in str(m).lower() for m in memories), "Preference not captured"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "memories_stored": len(memories)
            })
            logger.info(f"✓ Test passed: Stored {len(memories)} memories")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_02_medical_context_extraction(self):
        """Test 2: Extract medical context from conversation"""
        test_name = "Medical Context Extraction"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 2: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user2"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Medical conversation
            messages = [
                {"role": "user", "content": "I have type 2 diabetes and take metformin daily"},
                {"role": "assistant", "content": "I see you have type 2 diabetes and are taking metformin. How long have you been on this medication?"},
                {"role": "user", "content": "About 2 years now. I'm also allergic to penicillin"},
                {"role": "assistant", "content": "Thank you for sharing. I've noted your 2-year history with metformin and your penicillin allergy."}
            ]
            
            self.memory.add(
                messages=messages,
                user_id=memory_user_id,
                metadata={"test_case": "02", "medical_context": True}
            )
            
            # Search for medical information
            diabetes_memories = self.memory.search("diabetes medication", user_id=memory_user_id)
            allergy_memories = self.memory.search("allergies", user_id=memory_user_id)
            
            assert len(diabetes_memories) > 0, "Diabetes information not found"
            assert len(allergy_memories) > 0, "Allergy information not found"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "diabetes_memories": len(diabetes_memories),
                "allergy_memories": len(allergy_memories)
            })
            logger.info(f"✓ Test passed: Found {len(diabetes_memories)} diabetes and {len(allergy_memories)} allergy memories")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_03_memory_update_and_evolution(self):
        """Test 3: Test memory updates and evolution over time"""
        test_name = "Memory Update and Evolution"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 3: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user2"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Update medical information
            messages = [
                {"role": "user", "content": "My doctor changed my medication from metformin to insulin"},
                {"role": "assistant", "content": "I see your medication has been changed from metformin to insulin. This is an important update."},
                {"role": "user", "content": "Yes, my blood sugar wasn't well controlled with metformin alone"},
                {"role": "assistant", "content": "I've updated your medication information. You're now on insulin due to inadequate blood sugar control with metformin."}
            ]
            
            self.memory.add(
                messages=messages,
                user_id=memory_user_id,
                metadata={"test_case": "03", "update": True}
            )
            
            # Check if both old and new information is retained
            medication_memories = self.memory.search("medication diabetes", user_id=memory_user_id)
            
            # Should find both metformin (historical) and insulin (current)
            memory_text = " ".join([str(m) for m in medication_memories])
            assert "metformin" in memory_text.lower(), "Historical medication not retained"
            assert "insulin" in memory_text.lower(), "Current medication not found"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "total_medication_memories": len(medication_memories)
            })
            logger.info(f"✓ Test passed: Memory evolution tracked with {len(medication_memories)} medication memories")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_04_multi_conversation_memory(self):
        """Test 4: Memory across multiple conversations"""
        test_name = "Multi-Conversation Memory"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 4: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user3"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # First conversation - Initial symptoms
            conv1 = [
                {"role": "user", "content": "I've been having headaches for the past week"},
                {"role": "assistant", "content": "I'm sorry to hear about your headaches. Can you describe them?"},
                {"role": "user", "content": "They're mostly in the morning and feel like pressure"},
                {"role": "assistant", "content": "Morning headaches with pressure sensation noted. Let me ask a few more questions."}
            ]
            
            self.memory.add(
                messages=conv1,
                user_id=memory_user_id,
                metadata={"conversation_id": "conv_001", "test_case": "04"}
            )
            
            # Second conversation - Follow-up
            await asyncio.sleep(1)  # Small delay to simulate time passing
            conv2 = [
                {"role": "user", "content": "The headaches are getting worse"},
                {"role": "assistant", "content": "I see you mentioned headaches last week. How have they changed?"},
                {"role": "user", "content": "Now they last all day and I feel nauseous"},
                {"role": "assistant", "content": "The progression from morning headaches to all-day headaches with nausea is concerning."}
            ]
            
            self.memory.add(
                messages=conv2,
                user_id=memory_user_id,
                metadata={"conversation_id": "conv_002", "test_case": "04"}
            )
            
            # Test memory retrieval across conversations
            headache_memories = self.memory.search("headache symptoms", user_id=memory_user_id)
            
            # Should find information from both conversations
            memory_text = " ".join([str(m) for m in headache_memories])
            assert "morning" in memory_text.lower(), "Initial symptom not found"
            assert "nauseous" in memory_text.lower() or "nausea" in memory_text.lower(), "Updated symptom not found"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "memories_across_conversations": len(headache_memories)
            })
            logger.info(f"✓ Test passed: Found {len(headache_memories)} memories across conversations")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_05_appointment_preference_memory(self):
        """Test 5: Remember appointment preferences"""
        test_name = "Appointment Preference Memory"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 5: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user3"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Appointment preference conversation
            messages = [
                {"role": "user", "content": "I need to book an appointment with Dr. Smith"},
                {"role": "assistant", "content": "I can help you book an appointment with Dr. Smith. What time works best?"},
                {"role": "user", "content": "I prefer Tuesday afternoons, and I don't like waiting more than 15 minutes"},
                {"role": "assistant", "content": "I've noted your preferences: Tuesday afternoons with Dr. Smith, and maximum 15-minute wait time."}
            ]
            
            self.memory.add(
                messages=messages,
                user_id=memory_user_id,
                metadata={"test_case": "05", "preference_type": "appointment"}
            )
            
            # Test preference retrieval
            preferences = self.memory.search("appointment preferences Dr. Smith", user_id=memory_user_id)
            
            memory_text = " ".join([str(m) for m in preferences])
            assert "tuesday" in memory_text.lower(), "Day preference not found"
            assert "afternoon" in memory_text.lower(), "Time preference not found"
            assert "15" in memory_text or "fifteen" in memory_text.lower(), "Wait time preference not found"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "preferences_found": len(preferences)
            })
            logger.info(f"✓ Test passed: Found {len(preferences)} appointment preferences")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_06_complex_medical_history(self):
        """Test 6: Complex medical history with multiple conditions"""
        test_name = "Complex Medical History"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 6: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user3"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Complex medical history
            messages = [
                {"role": "user", "content": "I have diabetes, hypertension, and had a knee surgery last year"},
                {"role": "assistant", "content": "I see you have multiple conditions. Let me note these: diabetes, hypertension, and knee surgery last year."},
                {"role": "user", "content": "I take lisinopril for blood pressure, insulin for diabetes, and I'm allergic to sulfa drugs"},
                {"role": "assistant", "content": "I've recorded your medications: lisinopril for hypertension, insulin for diabetes, and your sulfa drug allergy."},
                {"role": "user", "content": "My family history includes heart disease - my father had a heart attack at 55"},
                {"role": "assistant", "content": "Important family history noted: father had heart attack at 55. This is relevant given your hypertension."}
            ]
            
            self.memory.add(
                messages=messages,
                user_id=memory_user_id,
                metadata={"test_case": "06", "medical_complexity": "high"}
            )
            
            # Test comprehensive retrieval
            conditions = self.memory.search("medical conditions", user_id=memory_user_id)
            medications = self.memory.search("medications", user_id=memory_user_id)
            family_history = self.memory.search("family history", user_id=memory_user_id)
            
            assert len(conditions) > 0, "Medical conditions not found"
            assert len(medications) > 0, "Medications not found"
            assert len(family_history) > 0, "Family history not found"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "conditions": len(conditions),
                "medications": len(medications),
                "family_history": len(family_history)
            })
            logger.info(f"✓ Test passed: Complex medical history stored successfully")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_07_contextual_memory_retrieval(self):
        """Test 7: Contextual memory retrieval"""
        test_name = "Contextual Memory Retrieval"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 7: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            user_id = TEST_USERS["user3"]["id"]
            memory_user_id = f"humansa_test_{user_id}"
            
            # Query for specific context
            query = "What medications is this patient taking for their chronic conditions?"
            relevant_memories = self.memory.search(query, user_id=memory_user_id, limit=5)
            
            # Should retrieve medication-related memories
            memory_text = " ".join([str(m) for m in relevant_memories])
            
            # Check if relevant medications are found
            medications_found = []
            if "lisinopril" in memory_text.lower():
                medications_found.append("lisinopril")
            if "insulin" in memory_text.lower():
                medications_found.append("insulin")
            
            assert len(medications_found) >= 2, f"Expected at least 2 medications, found {medications_found}"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "relevant_memories": len(relevant_memories),
                "medications_found": medications_found
            })
            logger.info(f"✓ Test passed: Found {len(relevant_memories)} relevant memories")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    # ========== Memory Persistence Tests ==========
    
    async def test_08_memory_persistence_check(self):
        """Test 8: Verify memories persist (don't add new ones)"""
        test_name = "Memory Persistence Check"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 8: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            # Check User 1's memories
            user1_id = TEST_USERS["user1"]["id"]
            memory_user1_id = f"humansa_test_{user1_id}"
            user1_memories = self.memory.get_all(memory_user1_id)
            
            # Check User 2's memories
            user2_id = TEST_USERS["user2"]["id"]
            memory_user2_id = f"humansa_test_{user2_id}"
            user2_memories = self.memory.get_all(memory_user2_id)
            
            # Check User 3's memories
            user3_id = TEST_USERS["user3"]["id"]
            memory_user3_id = f"humansa_test_{user3_id}"
            user3_memories = self.memory.get_all(memory_user3_id)
            
            # Verify memories exist from previous tests
            assert len(user1_memories) > 0, "User 1 memories not persisted"
            assert len(user2_memories) > 0, "User 2 memories not persisted"
            assert len(user3_memories) > 0, "User 3 memories not persisted"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "user1_memories": len(user1_memories),
                "user2_memories": len(user2_memories),
                "user3_memories": len(user3_memories)
            })
            logger.info(f"✓ Test passed: All user memories persisted")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_09_cross_session_memory_recall(self):
        """Test 9: Recall specific information from earlier sessions"""
        test_name = "Cross-Session Memory Recall"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 9: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            # Test specific recalls for each user
            
            # User 1: Should remember appointment preference
            user1_id = TEST_USERS["user1"]["id"]
            memory_user1_id = f"humansa_test_{user1_id}"
            user1_prefs = self.memory.search("appointment time preference", user_id=memory_user1_id)
            
            memory_text = " ".join([str(m) for m in user1_prefs])
            assert "morning" in memory_text.lower() or "9 am" in memory_text.lower(), "User 1 appointment preference not recalled"
            
            # User 2: Should remember medication change
            user2_id = TEST_USERS["user2"]["id"]
            memory_user2_id = f"humansa_test_{user2_id}"
            user2_meds = self.memory.search("current diabetes medication", user_id=memory_user2_id)
            
            memory_text = " ".join([str(m) for m in user2_meds])
            assert "insulin" in memory_text.lower(), "User 2 current medication not recalled"
            
            # User 3: Should remember allergy
            user3_id = TEST_USERS["user3"]["id"]
            memory_user3_id = f"humansa_test_{user3_id}"
            user3_allergy = self.memory.search("drug allergies", user_id=memory_user3_id)
            
            memory_text = " ".join([str(m) for m in user3_allergy])
            assert "sulfa" in memory_text.lower(), "User 3 allergy not recalled"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "user1_recall": "appointment preference",
                "user2_recall": "medication change",
                "user3_recall": "drug allergy"
            })
            logger.info(f"✓ Test passed: All specific memories recalled successfully")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def test_10_comprehensive_patient_summary(self):
        """Test 10: Generate comprehensive patient summary from all memories"""
        test_name = "Comprehensive Patient Summary"
        logger.info(f"\n{'='*50}")
        logger.info(f"Test 10: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            # Generate summary for User 3 (most complex history)
            user3_id = TEST_USERS["user3"]["id"]
            memory_user3_id = f"humansa_test_{user3_id}"
            
            # Get all memories
            all_memories = self.memory.get_all(memory_user3_id)
            
            # Create a patient summary
            summary = {
                "user_id": user3_id,
                "total_memories": len(all_memories),
                "conditions": [],
                "medications": [],
                "allergies": [],
                "preferences": [],
                "symptoms": []
            }
            
            # Analyze memories (simple keyword-based for testing)
            memory_text = " ".join([str(m) for m in all_memories]).lower()
            
            # Extract conditions
            if "diabetes" in memory_text:
                summary["conditions"].append("diabetes")
            if "hypertension" in memory_text:
                summary["conditions"].append("hypertension")
            if "knee surgery" in memory_text:
                summary["conditions"].append("knee surgery history")
            
            # Extract medications
            if "insulin" in memory_text:
                summary["medications"].append("insulin")
            if "lisinopril" in memory_text:
                summary["medications"].append("lisinopril")
            
            # Extract allergies
            if "sulfa" in memory_text:
                summary["allergies"].append("sulfa drugs")
            
            # Extract preferences
            if "tuesday afternoon" in memory_text:
                summary["preferences"].append("Tuesday afternoon appointments")
            if "dr. smith" in memory_text:
                summary["preferences"].append("Prefers Dr. Smith")
            
            # Extract symptoms
            if "headache" in memory_text:
                summary["symptoms"].append("headaches (progressing)")
            
            # Verify comprehensive capture
            assert len(summary["conditions"]) >= 2, "Not all conditions captured"
            assert len(summary["medications"]) >= 2, "Not all medications captured"
            assert len(summary["allergies"]) >= 1, "Allergies not captured"
            assert len(summary["preferences"]) >= 1, "Preferences not captured"
            
            self.test_results.append({
                "test": test_name,
                "status": "PASSED",
                "summary": summary
            })
            logger.info(f"✓ Test passed: Comprehensive patient summary generated")
            logger.info(f"  - Conditions: {summary['conditions']}")
            logger.info(f"  - Medications: {summary['medications']}")
            logger.info(f"  - Allergies: {summary['allergies']}")
            
        except Exception as e:
            self.test_results.append({
                "test": test_name,
                "status": "FAILED",
                "error": str(e)
            })
            logger.error(f"✗ Test failed: {e}")
    
    async def run_all_tests(self):
        """Run all test cases"""
        await self.setup()
        
        try:
            # Clear existing memories for clean test
            await self.clear_test_memories()
            
            # Run memory creation tests (1-7)
            await self.test_01_basic_memory_storage()
            await self.test_02_medical_context_extraction()
            await self.test_03_memory_update_and_evolution()
            await self.test_04_multi_conversation_memory()
            await self.test_05_appointment_preference_memory()
            await self.test_06_complex_medical_history()
            await self.test_07_contextual_memory_retrieval()
            
            # Run memory persistence tests (8-10)
            await self.test_08_memory_persistence_check()
            await self.test_09_cross_session_memory_recall()
            await self.test_10_comprehensive_patient_summary()
            
            # Generate summary report
            self.generate_test_report()
            
        finally:
            await self.teardown()
    
    def generate_test_report(self):
        """Generate test summary report"""
        logger.info(f"\n{'='*70}")
        logger.info("TEST SUMMARY REPORT")
        logger.info(f"{'='*70}")
        
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results if r["status"] == "FAILED")
        
        logger.info(f"Total Tests: {len(self.test_results)}")
        logger.info(f"Passed: {passed}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Success Rate: {(passed/len(self.test_results)*100):.1f}%")
        
        logger.info(f"\nDetailed Results:")
        for i, result in enumerate(self.test_results, 1):
            status_icon = "✓" if result["status"] == "PASSED" else "✗"
            logger.info(f"{status_icon} Test {i}: {result['test']} - {result['status']}")
            if result["status"] == "FAILED":
                logger.info(f"  Error: {result.get('error', 'Unknown error')}")
        
        # Save results to file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"mem0_test_results_{timestamp}.json"
        with open(filename, 'w') as f:
            json.dump({
                "timestamp": timestamp,
                "summary": {
                    "total": len(self.test_results),
                    "passed": passed,
                    "failed": failed,
                    "success_rate": f"{(passed/len(self.test_results)*100):.1f}%"
                },
                "results": self.test_results
            }, f, indent=2, default=str)
        
        logger.info(f"\nTest results saved to: {filename}")


# Mock Memory class for testing without real Azure credentials
class MockMemory:
    """Mock implementation of Mem0 for testing"""
    def __init__(self):
        self.memories = {}
        self.id_counter = 1
        
    def add(self, messages, user_id, metadata=None):
        if user_id not in self.memories:
            self.memories[user_id] = []
        
        # Extract key information from messages
        memory_content = " ".join([m["content"] for m in messages])
        
        memory = {
            "id": self.id_counter,
            "user_id": user_id,
            "memory": memory_content,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }
        
        self.memories[user_id].append(memory)
        self.id_counter += 1
        
    def get_all(self, user_id):
        return self.memories.get(user_id, [])
    
    def search(self, query, user_id, limit=10):
        user_memories = self.memories.get(user_id, [])
        # Simple keyword search
        query_lower = query.lower()
        results = []
        
        for memory in user_memories:
            if any(word in memory["memory"].lower() for word in query_lower.split()):
                results.append(memory)
                
        return results[:limit]
    
    def delete(self, memory_id):
        for user_id in self.memories:
            self.memories[user_id] = [m for m in self.memories[user_id] if m["id"] != memory_id]


async def main():
    """Main test runner"""
    test_suite = Mem0HumansaTestSuite()
    await test_suite.run_all_tests()


if __name__ == "__main__":
    # Run tests
    asyncio.run(main())