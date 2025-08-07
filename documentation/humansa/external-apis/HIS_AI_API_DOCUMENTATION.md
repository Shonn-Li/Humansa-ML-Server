# HIS-AI API Documentation

This document describes the external HIS (Hospital Information System) AI API endpoints that Humansa needs to integrate with for appointment booking, doctor search, and patient management.

## Overview

**Base URL**: `{{baseUrl}}` (to be configured per environment)  
**Authentication**: Token-based with session cookies  
**API Source**: HIS-AI接口文档.postman.json

## Authentication

### Headers Required for All API Calls

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `X-CurTime` | string | Request timestamp | `1753152288945` |
| `X-Token` | string | Authentication token for request validation | `f70f1746144e49eb3e83b897e227968990b377b8b07f8499` |

### Authentication Flow

#### 1. Get Login Verification Code
```
GET /api/system/sendYZMCode
```

**Query Parameters:**
- `userCode` (string, required): HIS system user code (e.g., `HIS_AI`)

**Response:**
```json
{
  "code": -1,
  "returnMsg": "接收者电话号码为空",
  "data": null
}
```

#### 2. Login to Get Cookie
```
POST /login
```

**Description**: Login to HIS system to obtain session cookie. Cookie has 2-hour idle timeout.

**Body**: URL-encoded form data (specific fields not documented in collection)

## Core API Endpoints

### 1. Hospital/Clinic Management

#### Get All Valid Hospitals
```
GET /api/ai/findAllValidHopsital
```

**Description**: Query all valid Nuoya (诺亚) clinic basic information

**Headers**: Standard authentication headers required

**Response**: List of all active hospitals/clinics

#### Find Hospital by Name
```
GET /api/ai/findHopsitalByName
```

**Query Parameters:**
- `name` (string, required): Hospital/clinic name to search (e.g., `友邦峻宇养生庭`)

**Response**: Hospital details matching the name

#### Get All Hospital Names
```
GET /api/ai/findAllHopsitalName
```

**Description**: Retrieve list of all hospital/clinic names only

**Response**: Array of hospital names

### 2. Doctor Management

#### Search Doctors by ID and Name
```
GET /api/ai/getDoctorListByIdAndName
```

**Query Parameters:**
- `ids` (string, optional): Comma-separated list of doctor IDs (e.g., `6e690c4a49664f4993a21690a83d4726,0d46427c23654a078b09d76cd9b45aa1`)
- `userName` (string, optional): Doctor name (e.g., `邹威`)

**Response**: List of doctor information including:
- Doctor ID
- Name
- Specialty
- Clinic assignment
- Other professional details

### 3. Department Management

#### Get Department Information
```
GET /api/ai/getDeptListByIdsAndNameAndHid
```

**Query Parameters:**
- `ids` (string, optional): Comma-separated department IDs
- `deptName` (string, optional): Department name filter (e.g., `骨`)
- `hospitalId` (string, required): Hospital ID (e.g., `6`)

**Response**: Department details including:
- Department ID
- Department name
- Associated doctors
- Services offered

### 4. Appointment Management

#### Get Available Appointment Slots
```
GET /api/ai/getUnbookedShiftSchedulingInformation
```

**Query Parameters:**
- `deptId` (string, optional): Department ID
- `doctorId` (string, optional): Doctor ID
- `hospitalId` (string, required): Hospital ID (e.g., `6`)
- `schDate` (string, required): Appointment date in YYYY-MM-DD format (e.g., `2025-07-22`)

**Response**: Available time slots with:
- Slot details
- Remaining capacity
- Shift information

#### Get Patient Appointments by Phone
```
GET /api/ai/getAppointmentByPhone
```

**Query Parameters:**
- `pid` (string, optional): Patient ID (e.g., `52ac24b073fe430889778f56902415bd`)
- `phone` (string, required): Patient phone number (e.g., `15700722874`)
- `hospitalId` (string, required): Hospital ID (e.g., `6`)

**Description**: Retrieve future appointments for a patient

**Response**: List of upcoming appointments with details

### 5. Patient Management

#### Get Patient Information
```
GET /api/ai/getPapersonByIdAndPhone
```

**Query Parameters:**
- `pid` (string, optional): Patient ID (e.g., `fd69c99434314e53a035d6c81b534a82`)
- `phone` (string, required): Patient phone number (e.g., `15700722874`)
- `cpId` (string, required): Clinic internal code (e.g., `1`)

**Response**: Patient profile including:
- Basic demographics
- Contact information
- Medical record number
- Registration details

### 6. Package/Membership System

#### Get Patient's Purchased Packages
```
GET /api/ai/getPkgTempletInstanceListByPid
```

**Query Parameters:**
- `pid` (string, required): Patient ID

**Description**: Retrieve purchased but incomplete medical packages

**Response**: List of active medical packages

#### Get Package Details
```
GET /api/ai/getNodeListByTempletInstanceId
```

**Query Parameters:**
- `templetInstanceId` (string, required): Package instance ID (e.g., `87bf3053e2014dae95f36f704544c878`)

**Description**: Query patient package nodes and node items

**Response**: Detailed package structure with:
- Service nodes
- Completion status
- Remaining items

#### Get VIP Account Information
```
GET /api/ai/getVipUserAccountsByPid
```

**Query Parameters:**
- `pid` (string, required): Patient ID

**Response**: VIP membership details including:
- Account status
- Benefits
- Expiration date

## Important Notes

1. **No Write Operations**: This API collection only contains GET requests. Actual appointment booking endpoints are not included.

2. **Patient ID Required**: Most endpoints require a patient ID (`pid`), suggesting need for patient registration flow.

3. **Hospital ID Required**: Many endpoints require `hospitalId`, indicating multi-location support.

4. **Chinese Language**: API uses Chinese field names and values extensively.

5. **Session Management**: Cookie-based authentication with 2-hour timeout requires session refresh strategy.

## Integration Considerations

1. **Missing Endpoints**: 
   - Patient registration/creation
   - Appointment booking/confirmation
   - Appointment cancellation/modification
   - Payment processing

2. **Data Mapping Required**:
   - Hospital ID mapping
   - Department ID mapping
   - Doctor ID synchronization
   - Patient ID linking

3. **Error Handling**:
   - Token expiration
   - Session timeout
   - Network failures
   - Invalid IDs

## Implementation Recommendations

1. **Create Wrapper Service**: Build an abstraction layer to handle:
   - Authentication and token management
   - Request/response transformation
   - Error handling and retries
   - ID mapping and caching

2. **Local Data Storage**: Maintain local copies of:
   - Patient profiles with ID mappings
   - Doctor and clinic information
   - Appointment history
   - Session tokens

3. **Synchronization Strategy**:
   - Regular sync for doctor/clinic data
   - Real-time checks for availability
   - Patient data validation on demand
   - Appointment status polling

4. **Security Measures**:
   - Secure token storage
   - API key encryption
   - Request logging for audit
   - PII data protection