#!/usr/bin/env python
"""Test appointment booking flow with user approval system"""

import asyncio
import aiohttp
import json
from datetime import datetime, timedelta

class AppointmentFlowTester:
    def __init__(self, base_url="http://localhost:6001"):
        self.base_url = base_url
        self.session = None
        self.user_id = "test_appointment_flow"
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def send_message(self, message: str, stream: bool = False) -> dict:
        """Send a message to the appointment agent"""
        url = f"{self.base_url}/v2/humansa/chat"
        
        data = {
            "user_id": self.user_id,
            "messages": [{"role": "user", "content": message}],
            "stream": stream
        }
        
        async with self.session.post(url, json=data) as response:
            if response.status == 200:
                result = await response.json()
                
                # Extract content from response
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    
                    # Handle response agent format
                    if isinstance(content, dict) and "output" in content:
                        actual_content = content["output"][0].get("content", "")
                    else:
                        actual_content = str(content)
                    
                    return {
                        "success": True,
                        "content": actual_content,
                        "raw_response": result
                    }
                else:
                    return {
                        "success": False,
                        "error": "Invalid response format",
                        "raw_response": result
                    }
            else:
                error_text = await response.text()
                return {
                    "success": False,
                    "error": f"HTTP {response.status}: {error_text}"
                }
    
    async def test_appointment_search(self):
        """Test appointment search functionality"""
        print("\n" + "="*60)
        print("🔍 Testing Appointment Search")
        print("="*60)
        
        test_queries = [
            "我想预约心内科医生",
            "明天有儿科医生吗？",
            "孙浩医生什么时候有空？",
            "这周上午有骨科专家吗？"
        ]
        
        results = []
        for query in test_queries:
            print(f"\n📝 Query: {query}")
            response = await self.send_message(query)
            
            if response["success"]:
                print("✅ Response received")
                print(f"📄 Content preview: {response['content'][:200]}...")
                
                # Check if search was performed (look for specific appointment info)
                has_specific_slots = any(keyword in response['content'] for keyword in 
                                       ["医生", "时间", "日期", "预约", "门诊"])
                results.append({
                    "query": query,
                    "success": True,
                    "has_specific_info": has_specific_slots
                })
            else:
                print(f"❌ Error: {response['error']}")
                results.append({
                    "query": query,
                    "success": False,
                    "has_specific_info": False
                })
            
            await asyncio.sleep(1)
        
        successful = sum(1 for r in results if r["success"])
        with_info = sum(1 for r in results if r["has_specific_info"])
        
        print(f"\n📊 Search Results: {successful}/{len(results)} successful, {with_info}/{len(results)} with appointment info")
        return results
    
    async def test_appointment_booking_flow(self):
        """Test complete appointment booking flow with approval"""
        print("\n" + "="*60)
        print("🎯 Testing Complete Booking Flow")
        print("="*60)
        
        # Step 1: Search for appointments
        print("\n1️⃣ Searching for heart specialist appointments...")
        search_response = await self.send_message("我想预约心内科医生，明天上午有时间吗？")
        
        if not search_response["success"]:
            print(f"❌ Search failed: {search_response['error']}")
            return {"success": False, "step": "search"}
        
        print("✅ Search completed")
        print(f"📄 Options: {search_response['content'][:300]}...")
        
        # Step 2: Simulate user selection (if options presented)
        if "医生" in search_response["content"] and "时间" in search_response["content"]:
            print("\n2️⃣ User selecting first option...")
            selection_response = await self.send_message("我选择第1个时间")
            
            if not selection_response["success"]:
                print(f"❌ Selection failed: {selection_response['error']}")
                return {"success": False, "step": "selection"}
            
            print("✅ Selection processed")
            print(f"📄 Response: {selection_response['content'][:300]}...")
            
            # Step 3: Check if approval is requested
            if "确认" in selection_response["content"] or "预约" in selection_response["content"]:
                print("\n3️⃣ Processing approval request...")
                approval_response = await self.send_message("确认预约")
                
                if not approval_response["success"]:
                    print(f"❌ Approval failed: {approval_response['error']}")
                    return {"success": False, "step": "approval"}
                
                print("✅ Approval processed")
                print(f"📄 Final result: {approval_response['content'][:300]}...")
                
                # Check if booking was confirmed
                booking_confirmed = "预约成功" in approval_response["content"] or "确认" in approval_response["content"]
                
                return {
                    "success": True,
                    "booking_confirmed": booking_confirmed,
                    "final_response": approval_response["content"]
                }
            else:
                print("⚠️ No approval request detected")
                return {"success": True, "step": "no_approval_needed"}
        else:
            print("⚠️ No specific appointment options found in response")
            return {"success": True, "step": "no_specific_options"}
    
    async def test_approval_scenarios(self):
        """Test different approval/rejection scenarios"""
        print("\n" + "="*60)
        print("👤 Testing Approval Scenarios")
        print("="*60)
        
        scenarios = [
            ("确认预约", "approval"),
            ("取消预约", "rejection"),
            ("不知道", "unclear"),
            ("好的", "approval"),
            ("不要了", "rejection")
        ]
        
        results = []
        
        for response_text, expected_type in scenarios:
            print(f"\n📝 Testing response: '{response_text}' (expected: {expected_type})")
            
            # First get an appointment option
            search_response = await self.send_message("我想预约皮肤科医生")
            await asyncio.sleep(1)
            
            if search_response["success"]:
                # Then test approval response
                approval_response = await self.send_message(response_text)
                
                if approval_response["success"]:
                    content = approval_response["content"]
                    
                    # Analyze response type
                    if "确认" in content or "成功" in content or "安排" in content:
                        detected_type = "approval"
                    elif "取消" in content or "已取消" in content:
                        detected_type = "rejection"
                    elif "明确" in content or "请" in content:
                        detected_type = "unclear"
                    else:
                        detected_type = "unknown"
                    
                    correct = detected_type == expected_type
                    print(f"{'✅' if correct else '❌'} Expected {expected_type}, got {detected_type}")
                    
                    results.append({
                        "input": response_text,
                        "expected": expected_type,
                        "detected": detected_type,
                        "correct": correct
                    })
                else:
                    print(f"❌ Request failed: {approval_response['error']}")
                    results.append({
                        "input": response_text,
                        "expected": expected_type,
                        "detected": "error",
                        "correct": False
                    })
            
            await asyncio.sleep(1)
        
        correct_count = sum(1 for r in results if r["correct"])
        print(f"\n📊 Approval Tests: {correct_count}/{len(results)} handled correctly")
        return results
    
    async def test_error_handling(self):
        """Test error handling scenarios"""
        print("\n" + "="*60)
        print("🚨 Testing Error Handling")
        print("="*60)
        
        error_scenarios = [
            "预约一个不存在的科室",
            "预约昨天的时间",
            "预约一个不存在的医生"
        ]
        
        results = []
        for scenario in error_scenarios:
            print(f"\n📝 Testing: {scenario}")
            response = await self.send_message(scenario)
            
            if response["success"]:
                # Check if error was handled gracefully
                content = response["content"]
                has_error_handling = any(keyword in content for keyword in 
                                       ["抱歉", "没有", "不可用", "错误", "重新"])
                
                print(f"{'✅' if has_error_handling else '❌'} Error handling: {has_error_handling}")
                results.append({
                    "scenario": scenario,
                    "handled_gracefully": has_error_handling
                })
            else:
                print(f"❌ Request failed: {response['error']}")
                results.append({
                    "scenario": scenario,
                    "handled_gracefully": False
                })
            
            await asyncio.sleep(1)
        
        handled_count = sum(1 for r in results if r["handled_gracefully"])
        print(f"\n📊 Error Handling: {handled_count}/{len(results)} scenarios handled gracefully")
        return results


async def main():
    """Run comprehensive appointment flow tests"""
    print("🏥 HUMANSA V2 Appointment Flow Testing with Approval System")
    print(f"⏰ Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    
    async with AppointmentFlowTester() as tester:
        # Test 1: Basic appointment search
        search_results = await tester.test_appointment_search()
        
        # Test 2: Complete booking flow
        booking_result = await tester.test_appointment_booking_flow()
        
        # Test 3: Approval scenarios
        approval_results = await tester.test_approval_scenarios()
        
        # Test 4: Error handling
        error_results = await tester.test_error_handling()
        
        # Summary
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        # Search results
        successful_searches = sum(1 for r in search_results if r["success"])
        searches_with_info = sum(1 for r in search_results if r["has_specific_info"])
        print(f"🔍 Search Tests: {successful_searches}/{len(search_results)} successful, {searches_with_info}/{len(search_results)} with appointment details")
        
        # Booking flow
        print(f"🎯 Booking Flow: {'✅ Success' if booking_result.get('success', False) else '❌ Failed'}")
        if booking_result.get("booking_confirmed"):
            print(f"✅ Booking confirmed successfully")
        
        # Approval scenarios
        correct_approvals = sum(1 for r in approval_results if r["correct"])
        print(f"👤 Approval Handling: {correct_approvals}/{len(approval_results)} scenarios handled correctly")
        
        # Error handling
        handled_errors = sum(1 for r in error_results if r["handled_gracefully"])
        print(f"🚨 Error Handling: {handled_errors}/{len(error_results)} scenarios handled gracefully")
        
        # Overall assessment
        overall_score = (searches_with_info + (1 if booking_result.get('success') else 0) + 
                        correct_approvals + handled_errors)
        max_score = len(search_results) + 1 + len(approval_results) + len(error_results)
        
        print(f"\n🎉 Overall Score: {overall_score}/{max_score} ({overall_score/max_score*100:.1f}%)")
        
        if overall_score >= max_score * 0.8:
            print("✅ Appointment system is working well!")
        elif overall_score >= max_score * 0.6:
            print("⚠️ Appointment system needs some improvements")
        else:
            print("❌ Appointment system requires significant fixes")


if __name__ == "__main__":
    asyncio.run(main())