# HIS API to Humansa Tools Mapping

This document maps the HIS-AI API endpoints to our Humansa tool implementations and identifies gaps/differences.

## 1. Doctor Management

### HIS API: `GET /api/ai/getDoctorListByIdAndName`
**Parameters:**
- `ids` (string, optional): Comma-separated doctor IDs
- `userName` (string, optional): Doctor name

### Humansa Tool: `find_doctor_info`
**Parameters:**
- `name` (string, optional): Doctor name
- `specialty` (string, optional): Medical specialty
- `city` (string, optional): City location
- `language` (string): Response language

**Differences:**
- ✅ Both support doctor name search
- ❌ HIS uses doctor IDs, we use internal doctor_code
- ✅ We add specialty and city filters (enhancement)
- ❌ We don't support batch ID queries

## 2. Doctor Availability

### HIS API: `GET /api/ai/getUnbookedShiftSchedulingInformation`
**Parameters:**
- `deptId` (string, optional): Department ID
- `doctorId` (string, optional): Doctor ID
- `hospitalId` (string, required): Hospital ID
- `schDate` (string, required): Date (YYYY-MM-DD)

### Humansa Tool: `find_doctor_availability`
**Parameters:**
- `doctor_name` (string): Doctor name
- `start_date` (string, optional): Start date
- `end_date` (string, optional): End date  
- `specialty` (string, optional): Specialty
- `days_ahead` (int, optional): Days to look ahead

**Differences:**
- ❌ HIS uses IDs (deptId, doctorId, hospitalId), we use names
- ✅ We support date ranges, HIS requires specific date
- ✅ We have fuzzy matching for doctor names
- ❌ We don't have department-level filtering

## 3. Clinic/Hospital Search

### HIS API: `GET /api/ai/findAllValidHopsital`
**Parameters:** None (returns all)

### HIS API: `GET /api/ai/findHopsitalByName`
**Parameters:**
- `name` (string, required): Hospital name

### Humansa Tool: `search_clinics`
**Parameters:**
- `clinic_name` (string, optional): Clinic name
- `city` (string, optional): City
- `specialty` (string, optional): Specialty services

**Differences:**
- ✅ Both support name-based search
- ✅ We add city and specialty filters
- ✅ We have fuzzy matching
- ❌ HIS has separate endpoints for all vs specific

## 4. Appointment Booking

### HIS API: Not available in the collection (only GET endpoints)

### Humansa Tools:
- `book_appointment`
- `prepare_booking_confirmation`

**Gap Analysis:**
- ❌ HIS API collection doesn't include booking endpoints
- ❓ Need actual booking API specification

## 5. Patient Management

### HIS API: `GET /api/ai/getPapersonByIdAndPhone`
**Parameters:**
- `pid` (string, optional): Patient ID
- `phone` (string, required): Phone number
- `cpId` (string, required): Clinic internal code

### HIS API: `GET /api/ai/getAppointmentByPhone`
**Parameters:**
- `pid` (string, optional): Patient ID
- `phone` (string, required): Phone number
- `hospitalId` (string, required): Hospital ID

### Humansa: No direct patient query tools
**Gap:**
- ❌ We don't have patient lookup tools
- ❌ We don't query appointments by phone
- ✅ We store patient info in memory/context

## Key Integration Requirements

### 1. ID Mapping System
We need to maintain mappings between:
- Our `doctor_code` ↔ HIS `doctorId`
- Our `clinic_code` ↔ HIS `hospitalId`
- Our internal patient IDs ↔ HIS `pid`

### 2. Authentication
HIS requires:
- `X-CurTime` header with timestamp
- `X-Token` header for authentication
- Session cookies with 2-hour timeout

Our tools need to:
- Add authentication headers
- Handle token refresh
- Manage session lifecycle

### 3. Data Format Differences
HIS API:
- Uses Chinese field names in responses
- Returns data in specific HIS format
- Requires specific parameter names

Our tools:
- Use English field names internally
- Return standardized format
- Accept flexible parameters

## Recommended Implementation

### 1. Create HIS API Adapter Layer
```python
class HISAPIAdapter:
    def __init__(self, base_url, auth_config):
        self.base_url = base_url
        self.auth = HISAuthManager(auth_config)
        self.id_mapper = HISIDMapper()
    
    async def find_doctor(self, name=None, doctor_code=None):
        # Map our doctor_code to HIS doctorId
        his_doctor_id = self.id_mapper.get_his_doctor_id(doctor_code)
        
        # Call HIS API with proper auth
        headers = self.auth.get_headers()
        response = await self.call_his_api(
            "/api/ai/getDoctorListByIdAndName",
            params={"ids": his_doctor_id, "userName": name},
            headers=headers
        )
        
        # Transform HIS response to our format
        return self.transform_doctor_response(response)
```

### 2. Maintain Local Cache
- Cache doctor/clinic mappings
- Store frequently accessed data
- Sync periodically with HIS

### 3. Hybrid Approach
- Use local DB for quick searches
- Validate availability with HIS API
- Book appointments through HIS API

## Action Items

1. **Get Complete HIS API Documentation**
   - Booking endpoints
   - Response formats
   - Error codes

2. **Implement ID Mapping Service**
   - Create mapping tables
   - Sync logic with HIS

3. **Build Authentication Manager**
   - Token management
   - Session refresh
   - Error handling

4. **Create Response Transformers**
   - HIS format → Our format
   - Handle Chinese/English
   - Normalize data

5. **Test Integration**
   - End-to-end booking flow
   - Error scenarios
   - Performance testing