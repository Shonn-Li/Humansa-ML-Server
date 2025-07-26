# HIS-AI Endpoints Quick Reference

## 🔐 Authentication
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/system/sendYZMCode` | GET | Send SMS verification code | ❌ No auth system |
| `/login` | POST | Login with code, get cookie | ❌ No cookie auth |

## 🏥 Hospital/Clinic Management
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/findAllValidHopsital` | GET | List all clinics | ✅ `search_clinics_structured()` |
| `/api/ai/findHopsitalByName` | GET | Search clinic by name | ✅ `search_clinics_structured()` |
| `/api/ai/findAllHopsitalName` | GET | Get all clinic names only | ⚠️ Partial - returns full objects |

**Missing**: Hospital ID (`hospitalId`) concept - we use clinic names directly

## 👨‍⚕️ Doctor Management
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/getDoctorListByIdAndName` | GET | Search by IDs (comma-separated) + name | ⚠️ Partial - no ID list support |

**Gap**: They support `ids=id1,id2,id3` - we only search by single name

## 🏢 Department Management
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/getDeptListByIdsAndNameAndHid` | GET | Get departments by hospital | ❌ No department concept |

**Major Gap**: No department (`deptId`) structure - we only have specialties

## 📅 Appointment Management
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/getUnbookedShiftSchedulingInformation` | GET | Available slots by date/dept/doctor | ✅ `find_doctor_availability_structured()` |
| `/api/ai/getAppointmentByPhone` | GET | Get patient's future appointments | ❌ No appointment history |

**Missing**: 
- Shift-based scheduling (we use mock slots)
- Historical appointment lookup

## 👤 Patient Management
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/getPapersonByIdAndPhone` | GET | Get patient by PID + phone | ❌ No patient lookup |

**Critical Gap**: 
- No `pid` (Patient ID) system
- No `cpId` (Clinic internal code)
- We only collect name/phone at booking time

## 📦 Package/Membership System
| Endpoint | Method | Purpose | What We Have |
|----------|---------|---------|--------------|
| `/api/ai/getPkgTempletInstanceListByPid` | GET | Get purchased packages | ❌ Not implemented |
| `/api/ai/getNodeListByTempletInstanceId` | GET | Get package details/nodes | ❌ Not implemented |
| `/api/ai/getVipUserAccountsByPid` | GET | Get VIP membership info | ❌ Not implemented |

**Major Feature Gap**: Entire package/membership system missing

## 🚨 Critical Missing Components

### 1. **Patient ID (PID) System**
```
Their System: Every patient has persistent `pid`
Our System: No patient persistence - only collect at booking
```

### 2. **ID Mapping Requirements**
You need a mapping table:
```sql
CREATE TABLE patient_mappings (
    our_user_id TEXT,
    their_pid TEXT,
    phone TEXT,
    created_at TIMESTAMP
);
```

### 3. **Multi-Entity IDs**
They use IDs everywhere:
- `hospitalId` - We need to map clinic names to IDs
- `deptId` - We don't have departments
- `doctorId` - We have it
- `pid` - Patient ID we're missing
- `cpId` - Clinic internal code we're missing
- `templetInstanceId` - Package IDs we don't support

### 4. **Write Operations**
**Their API shows NO write endpoints for:**
- Creating patients
- Booking appointments  
- Updating patient info
- Purchasing packages

This suggests either:
1. Write operations use different API
2. They handle writes through web interface only
3. Collection is incomplete

## 📋 Implementation Priority

### High Priority (Core Functionality)
1. ❗ Add patient ID system with phone-based lookup
2. ❗ Add appointment history retrieval
3. ❗ Add department structure to doctors
4. ❗ Map our entities to their ID system

### Medium Priority (Enhanced Features)
5. ⚠️ Implement shift-based scheduling (replace mock slots)
6. ⚠️ Add multi-ID search for doctors
7. ⚠️ Support hospital/clinic ID concept

### Low Priority (Future Features)
8. 📦 Package/membership system
9. 📦 VIP account management
10. 📦 Multi-clinic support (`cpId`)

## 🔄 Quick Validation Checklist

- [ ] Can we create/retrieve patients by PID?
- [ ] Do we support department-based doctor organization?
- [ ] Can we query appointment history?
- [ ] Do we have hospital/clinic IDs?
- [ ] Can we handle comma-separated ID searches?
- [ ] Do we track patient packages/memberships?
- [ ] Can we map phone numbers to patient IDs?

## 💡 Next Steps

1. **Immediate**: Design PID mapping system
2. **Short-term**: Add department structure
3. **Long-term**: Implement package/membership features
4. **Integration**: Build adapter layer for ID translation