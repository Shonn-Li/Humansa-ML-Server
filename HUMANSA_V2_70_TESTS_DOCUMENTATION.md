# HUMANSA V2 - 70 Test Cases with Follow-up Conversations

## Overview

This extended test suite (`run_HUMANSA_v2_test_70_cases_with_followup.sh`) includes:
- 40 original single-turn tests
- 30 new multi-turn conversation tests
- Proper follow-up testing to evaluate conversation flow handling

## New Features

### 1. Multi-turn Conversation Support

The new `test_api_followup()` function:
- Maintains conversation history between turns
- Sends full message arrays to simulate real conversations
- Captures assistant responses and adds them to history
- Shows complete conversation flow in results

### 2. Test Categories

#### Original Categories (Tests 1-40):
1. Identity and Introduction (1-5)
2. Doctor Search (6-10)
3. Appointment Booking (11-15)
4. Clinic Information (16-20)
5. Medical Queries (21-25)
6. Memory Tests (26-30)
7. Product Inquiries (31-40)

#### New Follow-up Categories (Tests 41-70):

##### Category 8: Complete Appointment Booking Flows (41-50)
- Test 41: Complete booking from search to confirmation
- Test 42: Booking for family member
- Test 43: Booking with doctor recommendation
- Test 44: Complete cancellation flow
- Test 45: Complete rescheduling flow
- Test 46: Location-based booking with availability check
- Test 47: Symptom-based booking
- Test 48: Availability check before booking
- Test 49: Price-conscious booking
- Test 50: Health checkup booking

##### Category 9: Product Purchase Flows (51-55)
- Test 51: Complete vitamin purchase
- Test 52: Medical device purchase
- Test 53: Pregnancy supplement purchase
- Test 54: Sleep aid purchase with concerns
- Test 55: Elderly supplement package

##### Category 10: Medical Consultation Flows (56-60)
- Test 56: Symptom to appointment
- Test 57: Urgent care consultation
- Test 58: Test results consultation
- Test 59: Pregnancy consultation
- Test 60: Sleep disorder consultation

##### Category 11: Memory and Context Tests (61-65)
- Test 61: Location and condition aware booking
- Test 62: Child health history
- Test 63: Follow-up appointment
- Test 64: Family member health management
- Test 65: Allergy management

##### Category 12: Error Recovery and Edge Cases (66-70)
- Test 66: Doctor not found recovery
- Test 67: Incorrect information correction
- Test 68: Price adjustment flow
- Test 69: Multiple corrections
- Test 70: Product selection corrections

## Usage

```bash
# Make sure virtual environment is activated
source youwo-ml-venv/bin/activate

# Ensure test database is running
cd test_environment && docker-compose up -d

# Run the extended test suite
./run_HUMANSA_v2_test_70_cases_with_followup.sh
```

## Expected Improvements

These tests will reveal:

1. **Conversation State Management**: Whether the system maintains context between turns
2. **Information Collection**: How well the system collects missing information
3. **Error Recovery**: How the system handles corrections and changes
4. **Tool Integration**: Whether tools work properly in multi-turn scenarios
5. **Memory Persistence**: If user information is retained across conversations

## Example Multi-turn Test

```bash
test_api_followup 41 "booking_user_1" \
    "Turn 1|我想预约骨科医生|Turn 2|北京的张伟医生可以|Turn 3|下周二上午10点|Turn 4|我叫李明，电话13800138000|Turn 5|确认预约" \
    "Appointment Booking Flow" \
    "Complete booking from search to confirmation"
```

This test simulates:
1. Initial request for appointment
2. Doctor selection
3. Time selection
4. Providing patient information
5. Final confirmation

## Output Files

- Results: `test_results_v2_40cases_enhanced/results_[timestamp].md`
- Process Log: `test_results_v2_40cases_enhanced/process_log_[timestamp].md`

The results will show:
- Each turn of the conversation
- Bot responses at each step
- Whether context is maintained
- Tool calls and their results
- Complete conversation summaries

## Success Criteria

A successful implementation should:
1. Remember previous turns in the conversation
2. Collect all required information progressively
3. Handle corrections gracefully
4. Complete bookings/purchases successfully
5. Maintain user context throughout the flow