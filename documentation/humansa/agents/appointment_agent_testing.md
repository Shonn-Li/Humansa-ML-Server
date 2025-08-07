# Appointment Agent Testing Guide

## Overview

The appointment agent has been implemented with a comprehensive form-based system. This guide covers testing procedures and expected behaviors.

## Test Environment Setup

### 1. Enable Pattern 2 Orchestrator
```bash
export HUMANSA_USE_PATTERN2=true
export HUMANSA_ENHANCED_LOGGING=true
```

### 2. Start the Server
```bash
# For test environment (port 6001)
./run_humansa_test_environment_v2.sh

# For development (port 5001)
python -m src.main
```

### 3. Verify Endpoints
- **V1 Endpoint**: `/v1-humansa/chat/completions`
- **V2 Responses**: `/v2/humansa/responses/create`

## Test Scenarios

### Test 1: Complete Appointment in One Turn
**Input**: "我想预约李明医生明天上午9点看头痛"

**Expected Output**:
- Form created with all information
- Preview showing appointment details
- Request for confirmation
- Form ID in response

### Test 2: Multi-Turn Progressive Collection
**Turn 1**: "我想看医生"
- Should ask for doctor preference and symptoms

**Turn 2**: "头痛，想看李明医生"
- Should ask for date/time preference

**Turn 3**: "明天上午"
- Should create form and show preview

### Test 3: Form Modification
**Turn 1**: Create appointment
**Turn 2**: "改成下午3点"
- Should update form and show new preview

### Test 4: Form Confirmation
**After form creation**: "确认"
- Should submit form and return confirmation code (APT-XXXXXX)

### Test 5: Form Cancellation
**After form creation**: "取消"
- Should cancel the appointment

## Implementation Status

### ✅ Completed Components

1. **Appointment Agent V2** (`appointment_agent_v2.py`)
   - Full validation logic
   - Progressive information collection
   - Form lifecycle management
   - Multi-turn context handling

2. **Form System**
   - Form models with validation
   - Form service for CRUD operations
   - Form tools for orchestrator integration
   - Mock booking service

3. **Form Registry**
   - Appointment history tracking
   - User analytics
   - Export functionality

4. **Documentation**
   - Complete architecture documentation
   - API endpoint documentation
   - Testing procedures

### ⚠️ Integration Requirements

For the form system to work properly:

1. **Pattern 2 Orchestrator Must Be Enabled**
   ```python
   # In orchestrator_pattern2_fixed.py
   # The appointment tool must use AppointmentAgentV2
   ```

2. **Response API Must Include Form Metadata**
   ```python
   # Form ID should be in response metadata
   response["metadata"]["form_id"] = form_id
   ```

3. **Context Must Be Maintained**
   ```python
   # Orchestrator must accumulate appointment context
   context = {
       'doctor': accumulated_doctor_info,
       'symptoms': accumulated_symptoms,
       'date': accumulated_date,
       'time': accumulated_time,
       'active_form_id': current_form_id
   }
   ```

## Test Suite

A comprehensive test suite with 22 test cases has been created:
- `test_appointment_form_system.py` - Full test suite
- `test_appointment_quick.py` - Quick validation test
- `test_appointment_v1.sh` - Shell script for v1 API testing

### Running Tests

```bash
# Python test suite (requires requests library)
python3 test_appointment_form_system.py

# Shell script test
./test_appointment_v1.sh

# Quick test
python3 test_appointment_quick.py
```

## Known Issues

1. **Server Configuration**: Ensure Pattern 2 is enabled before testing
2. **API Key**: Some endpoints may require authentication
3. **Port Configuration**: Tests default to port 5001, adjust if using test environment (6001)

## Next Steps

1. **Enable Pattern 2 in Production**
2. **Run Full Test Suite**
3. **Monitor Form Creation Success Rate**
4. **Collect User Feedback**
5. **Optimize Natural Language Understanding**