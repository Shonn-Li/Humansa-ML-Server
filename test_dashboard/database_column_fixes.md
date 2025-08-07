# Database Column Fixes for Humansa ML Server

## Summary
The following database column reference fixes need to be applied to ensure compatibility with the standardized test database schema.

## Files to Update

### 1. `/src/humansa/v2/tools/db_medical_tools.py`

#### Table Name Changes:
- `humansa_doctors` → `humansa_doctor` (singular)

#### Column Name Changes:
- `clinic_id` → `clinic_code`
- `doctor_id` → `doctor_code`

#### Specific Changes:

1. **Line ~34**: Change table name
   ```python
   # OLD:
   FROM humansa_doctors d
   # NEW:
   FROM humansa_doctor d
   ```

2. **Line ~35**: Change join condition
   ```python
   # OLD:
   JOIN humansa_clinics c ON d.clinic_id = c.clinic_id
   # NEW:
   JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
   ```

3. **Line ~98**: Change doctor_id reference
   ```python
   # OLD:
   "doctor_id": row['doctor_id'],
   # NEW:
   "doctor_id": row['doctor_code'],
   ```

4. **Line ~137-138**: Update doctor query
   ```python
   # OLD:
   FROM humansa_doctors d
   JOIN humansa_clinics c ON d.clinic_id = c.clinic_id
   WHERE d.doctor_id = $1
   # NEW:
   FROM humansa_doctor d
   JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
   WHERE d.doctor_code = $1
   ```

5. **Line ~147**: Update appointment slots query
   ```python
   # OLD:
   WHERE doctor_id = $1
   # NEW:
   WHERE doctor_code = $1
   ```

6. **Line ~217-219**: Update appointment booking query
   ```python
   # OLD:
   JOIN humansa_doctors d ON s.doctor_id = d.doctor_id
   JOIN humansa_clinics c ON d.clinic_id = c.clinic_id
   # NEW:
   JOIN humansa_doctor d ON s.doctor_code = d.doctor_code
   JOIN humansa_clinics c ON s.clinic_code = c.clinic_code
   ```

7. **Line ~238**: Update appointment insert columns
   ```python
   # OLD:
   appointment_id, slot_id, user_id, doctor_id, clinic_id,
   # NEW:
   appointment_id, slot_id, user_id, doctor_code, clinic_code,
   ```

8. **Line ~246-247**: Update appointment insert values
   ```python
   # OLD:
   slot['doctor_id'],
   slot['clinic_id'],
   # NEW:
   slot['doctor_code'],
   slot['clinic_code'],
   ```

9. **Line ~287-288**: Update user appointments query
   ```python
   # OLD:
   JOIN humansa_doctors d ON a.doctor_id = d.doctor_id
   JOIN humansa_clinics c ON a.clinic_id = c.clinic_id
   # NEW:
   JOIN humansa_doctor d ON a.doctor_code = d.doctor_code
   JOIN humansa_clinics c ON a.clinic_code = c.clinic_code
   ```

10. **Line ~372**: Fix service name column
    ```python
    # OLD:
    ms.service_name as name,
    # NEW:
    ms.name,
    ```

11. **Line ~393**: Fix service name condition
    ```python
    # OLD:
    conditions.append(f"LOWER(ms.service_name) LIKE LOWER(${param_count})")
    # NEW:
    conditions.append(f"LOWER(ms.name) LIKE LOWER(${param_count})")
    ```

12. **Line ~409**: Fix order by clause
    ```python
    # OLD:
    query += " ORDER BY ms.service_name"
    # NEW:
    query += " ORDER BY ms.name"
    ```

13. **Line ~492-494**: Update clinic info query
    ```python
    # OLD:
    SELECT c.*, COUNT(d.doctor_id) as doctor_count
    FROM humansa_clinics c
    LEFT JOIN humansa_doctors d ON c.clinic_id = d.clinic_id
    # NEW:
    SELECT c.*, COUNT(d.doctor_code) as doctor_count
    FROM humansa_clinics c
    LEFT JOIN humansa_doctor d ON c.clinic_code = d.clinic_code
    ```

14. **Line ~515**: Update group by clause
    ```python
    # OLD:
    query += " GROUP BY c.clinic_id ORDER BY c.name"
    # NEW:
    query += " GROUP BY c.clinic_code ORDER BY c.name"
    ```

15. **Line ~523**: Update clinic_id in results
    ```python
    # OLD:
    "clinic_id": row['clinic_id'],
    # NEW:
    "clinic_id": row['clinic_code'],
    ```

### 2. `/src/humansa/postgres/database.py`

Check this file for any references to:
- `doctor_id` → should be `doctor_code`
- `clinic_id` → should be `clinic_code`
- `humansa_doctors` → should be `humansa_doctor`

## Database Schema Reference

### Correct Table Names:
- `humansa_clinics` (uses `clinic_code` as primary key)
- `humansa_doctor` (singular, uses `doctor_code` as primary key)
- `humansa_medical_service` (uses `service_code` as primary key)

### Correct Column Names:
- Doctor references: `doctor_code` (NOT `doctor_id`)
- Clinic references: `clinic_code` (NOT `clinic_id`)
- Service name: `name` (NOT `service_name` in humansa_medical_service table)

## Testing
After applying these fixes:
1. Restart all ML server instances
2. Run the 22 test case suite
3. Check that there are no "column does not exist" errors
4. Verify that all database queries work correctly