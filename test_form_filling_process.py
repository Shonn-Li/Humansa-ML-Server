#!/usr/bin/env python3
"""
Test the complete form filling process with FormFillingAgent
"""

import asyncio
from src.humansa.v2.forms.form_filling_agent import FormFillingAgent
from src.humansa.v2.forms.form_tools import create_appointment_form, handle_form_confirmation
from src.humansa.v2.forms.models import FormStatus
import json

async def test_complete_form_flow():
    """Test the complete form creation and filling flow"""
    
    print("=" * 60)
    print("FORM FILLING PROCESS TEST")
    print("=" * 60)
    
    # Test cases showing progression from incomplete to complete
    test_scenarios = [
        {
            "name": "Incomplete Query - Missing Multiple Fields",
            "query": "我想看医生",
            "user_id": "test_user_001"
        },
        {
            "name": "Partial Query - Has Symptoms",
            "query": "我头疼想看医生",
            "user_id": "test_user_002"
        },
        {
            "name": "Better Query - Has Doctor",
            "query": "我想找李明医生看病",
            "user_id": "test_user_003"
        },
        {
            "name": "Complete Query - All Info",
            "query": "我想预约李明医生看内科，明天上午9点，最近头疼发烧",
            "user_id": "test_user_004"
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\n{'='*60}")
        print(f"Scenario: {scenario['name']}")
        print(f"Query: {scenario['query']}")
        print(f"{'='*60}")
        
        # Step 1: Show what FormFillingAgent extracts
        agent = FormFillingAgent()
        extracted = agent.fill_form_from_query(scenario['query'])
        
        print("\n📊 FormFillingAgent Extraction Results:")
        print(f"   Confidence: {extracted.get('extraction_confidence', 0):.0%}")
        print(f"   Extracted Fields:")
        for key, value in extracted.items():
            if key not in ['extraction_confidence', 'missing_fields', 'suggestions']:
                print(f"     - {key}: {value}")
        
        if extracted.get('missing_fields'):
            print(f"   Missing Fields: {', '.join(extracted['missing_fields'])}")
        
        # Step 2: Create form using form tools
        print("\n📋 Creating Form...")
        result = await create_appointment_form(
            user_id=scenario['user_id'],
            query=scenario['query']
        )
        
        if result['success']:
            print(f"   ✅ Form created with ID: {result['form_id']}")
            print(f"   Status: {result['status']}")
            print(f"   Action Required: {result.get('action_required', 'none')}")
            print(f"\n   Preview:")
            print("   " + "-" * 40)
            for line in result['preview'].split('\n'):
                if line.strip():
                    print(f"   {line}")
            print("   " + "-" * 40)
            
            # If form is complete, simulate confirmation
            if result.get('action_required') == 'confirmation':
                print("\n🤝 Simulating User Confirmation...")
                confirm_result = await handle_form_confirmation(
                    user_input="确认",
                    form_id=result['form_id'],
                    user_id=scenario['user_id']
                )
                
                if confirm_result['success']:
                    print("   ✅ Appointment Confirmed!")
                    if 'confirmation_code' in confirm_result:
                        print(f"   Confirmation Code: {confirm_result['confirmation_code']}")
                else:
                    print(f"   ❌ Confirmation failed: {confirm_result.get('message')}")
        else:
            print(f"   ❌ Form creation failed: {result.get('message')}")
    
    # Test modification flow
    print(f"\n{'='*60}")
    print("MODIFICATION FLOW TEST")
    print(f"{'='*60}")
    
    print("\nStep 1: Create initial form")
    initial_result = await create_appointment_form(
        user_id="test_modify_001",
        query="预约张医生看皮肤科，下周一"
    )
    
    if initial_result['success']:
        form_id = initial_result['form_id']
        print(f"✅ Form created: {form_id}")
        print(f"Preview: {initial_result['preview'][:100]}...")
        
        # Simulate providing missing time
        print("\nStep 2: User provides missing time")
        from src.humansa.v2.forms.form_tools import update_appointment_form
        
        update_result = await update_appointment_form(
            form_id=form_id,
            user_input="下午3点吧",
            user_id="test_modify_001"
        )
        
        if update_result['success']:
            print(f"✅ Form updated")
            print(f"Updated fields: {update_result.get('updated_fields')}")
            print(f"New preview: {update_result['preview'][:200]}...")

async def test_form_filling_agent_standalone():
    """Test FormFillingAgent independently"""
    print(f"\n{'='*60}")
    print("FORM FILLING AGENT DETAILED TEST")
    print(f"{'='*60}")
    
    agent = FormFillingAgent()
    
    # Complex test case
    complex_query = "紧急！我家孩子发烧39度，想尽快看儿科专家，最好今天下午"
    
    print(f"\nComplex Query: {complex_query}")
    result = agent.fill_form_from_query(complex_query)
    
    print("\nDetailed Extraction:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    print("\nForm Filling Process Test")
    print("This demonstrates how the FormFillingAgent extracts information")
    print("and how forms are created with varying levels of completeness.\n")
    
    asyncio.run(test_complete_form_flow())
    asyncio.run(test_form_filling_agent_standalone())