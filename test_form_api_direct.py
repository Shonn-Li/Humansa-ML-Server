#!/usr/bin/env python3
"""
Test form creation and retrieval directly
"""

import asyncio
import json
from src.humansa.v2.forms.form_service import FormService
from src.humansa.v2.forms.models import FormStatus

async def test_form_direct():
    """Test form service directly"""
    print("=== Testing Form Service Directly ===\n")
    
    # Create form service
    service = FormService()
    
    # Create a form
    form_data = {
        "doctor_name": "李明医生",
        "date": "2025-08-03",
        "time_slot": "09:00",
        "symptoms": "头痛",
        "patient_name": "张三",
        "patient_phone": "13800138000"
    }
    
    print("1. Creating form...")
    form = await service.create_form("test_user", form_data)
    print(f"Created form: {form.form_id}")
    print(f"Form data: {json.dumps(form.to_dict(), ensure_ascii=False, indent=2)}")
    
    # Try to get it back
    print("\n2. Retrieving form...")
    retrieved = await service.get_form(form.form_id)
    if retrieved:
        print(f"✓ Retrieved form: {retrieved.form_id}")
        print(f"Is complete: {retrieved.is_complete()}")
        print(f"Preview: {retrieved.get_preview_message()}")
    else:
        print("✗ Failed to retrieve form")
    
    # Check global storage
    print("\n3. Checking global storage...")
    from src.humansa.v2.forms.form_service import _FORM_STORAGE
    print(f"Forms in global storage: {list(_FORM_STORAGE.keys())}")
    
    # Test form completion
    if retrieved and retrieved.is_complete():
        print("\n4. Testing form submission...")
        success = await service.update_form_status(form.form_id, FormStatus.SUBMITTED)
        print(f"Update status: {'✓ Success' if success else '✗ Failed'}")


if __name__ == "__main__":
    asyncio.run(test_form_direct())