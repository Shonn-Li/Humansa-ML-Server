"""
Database connection utilities for Humansa AI-Agent system.
Connects to the same PostgreSQL database as the YouWoAI-Server.
Uses the same connection pattern as the main chat system.
"""
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, date
from dotenv import load_dotenv
from contextlib import contextmanager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration - same pattern as main chat system
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "user": os.getenv("DB_USER", "youwo"),
    "password": os.getenv("DB_PASSWORD", "youwo123"),
    "dbname": os.getenv("DB_NAME", "youwoai"),
}


class HumansaDatabase:
    """Database connection and query utility for Humansa tables."""

    def __init__(self):
        self.db_config = DB_CONFIG
        logger.info("HumansaDatabase initialized")

    @contextmanager
    def get_connection(self):
        """Database connection context manager - same pattern as PostgresManager"""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def find_doctor_by_name(self, doctor_name: str) -> Optional[Dict[str, Any]]:
        """Find doctor information by name with fuzzy matching support."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # First try exact match
                    exact_query = """
                        SELECT d.doctor_code, d.clinic_code, d.name, d.title, 
                               d.expertise, d.bio, d.registration_fee,
                               c.name as clinic_name, c.address, c.phone
                        FROM humansa_doctor d
                        LEFT JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
                        WHERE d.name = %s
                    """
                    cursor.execute(exact_query, (doctor_name,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(
                            f"✅ Found doctor by exact match: {row['name']}")
                        return dict(row)

                    # If no exact match, try fuzzy matching with ILIKE
                    fuzzy_query = """
                        SELECT d.doctor_code, d.clinic_code, d.name, d.title, 
                               d.expertise, d.bio, d.registration_fee,
                               c.name as clinic_name, c.address, c.phone
                        FROM humansa_doctor d
                        LEFT JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
                        WHERE d.name ILIKE %s
                        ORDER BY d.name
                        LIMIT 1
                    """
                    # Use fuzzy matching with wildcards
                    fuzzy_pattern = f"%{doctor_name}%"
                    cursor.execute(fuzzy_query, (fuzzy_pattern,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(
                            f"✅ Found doctor by fuzzy match: {row['name']} (searched for: {doctor_name})")
                        return dict(row)

                    logger.info(f"❌ No doctor found for name: {doctor_name}")
                    return None
        except Exception as e:
            logger.error(f"Error finding doctor {doctor_name}: {e}")
            return None

    def find_doctor_availability(self, doctor_name: str, date_str: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find available appointment slots for a doctor."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if date_str:
                        # Parse date string to ensure proper format
                        try:
                            # Handle various date formats
                            if '月' in date_str:  # Chinese format like "7月15日"
                                # Simple parsing for common Chinese date formats
                                import re
                                match = re.search(r'(\d+)月(\d+)日', date_str)
                                if match:
                                    month = int(match.group(1))
                                    day = int(match.group(2))
                                    current_year = datetime.now().year
                                    search_date = f"{current_year}-{month:02d}-{day:02d}"
                                else:
                                    search_date = date_str
                            else:
                                search_date = date_str
                        except:
                            search_date = date_str

                        query = """
                            SELECT s.doctor_code, s.shift_date, s.start_time, s.end_time, 
                                   s.remaining_slots, s.clinic_code,
                                   d.name as doctor_name, c.name as clinic_name
                            FROM humansa_schedule s
                            LEFT JOIN humansa_doctor d ON s.doctor_code = d.doctor_code
                            LEFT JOIN humansa_clinics c ON s.clinic_code = c.clinic_code
                            WHERE d.name = %s AND s.shift_date = %s AND s.remaining_slots > 0
                            ORDER BY s.start_time
                        """
                        cursor.execute(query, (doctor_name, search_date))
                    else:
                        # Get all future availability for the doctor
                        query = """
                            SELECT s.doctor_code, s.shift_date, s.start_time, s.end_time, 
                                   s.remaining_slots, s.clinic_code,
                                   d.name as doctor_name, c.name as clinic_name
                            FROM humansa_schedule s
                            LEFT JOIN humansa_doctor d ON s.doctor_code = d.doctor_code
                            LEFT JOIN humansa_clinics c ON s.clinic_code = c.clinic_code
                            WHERE d.name = %s AND s.shift_date >= CURRENT_DATE AND s.remaining_slots > 0
                            ORDER BY s.shift_date, s.start_time
                        """
                        cursor.execute(query, (doctor_name,))

                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error finding availability for {doctor_name}: {e}")
            return []

    def get_clinic_services(self, clinic_name: str) -> List[Dict[str, Any]]:
        """Get medical services available at a clinic."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT ms.clinic_code, ms.service_name, 
                               ms.price, ms.description, c.name as clinic_name
                        FROM humansa_medical_service ms
                        LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                        WHERE c.name = %s
                        ORDER BY ms.service_name
                    """
                    cursor.execute(query, (clinic_name,))
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting services for {clinic_name}: {e}")
            return []

    def get_pricing_info(self, service_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pricing information for medical services."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    if service_name:
                        query = """
                            SELECT ms.clinic_code, ms.service_name, 
                                   ms.price, ms.description, c.name as clinic_name
                            FROM humansa_medical_service ms
                            LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                            WHERE ms.service_name ILIKE %s
                            ORDER BY c.name, ms.service_name
                        """
                        cursor.execute(query, (f"%{service_name}%",))
                    else:
                        query = """
                            SELECT ms.clinic_code, ms.service_name, 
                                   ms.price, ms.description, c.name as clinic_name
                            FROM humansa_medical_service ms
                            LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                            ORDER BY c.name, ms.service_name
                        """
                        cursor.execute(query)

                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting pricing info: {e}")
            return []

    def get_all_clinics(self) -> List[Dict[str, Any]]:
        """Get all available clinics."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT clinic_code, name, address, phone
                        FROM humansa_clinics
                        ORDER BY name
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Error getting clinics: {e}")
            return []

    def health_check(self) -> bool:
        """Simple database health check"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    def find_clinic_by_name(self, clinic_name: str) -> Optional[Dict[str, Any]]:
        """Find clinic information by name with fuzzy matching support."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # First try exact match
                    exact_query = """
                        SELECT clinic_code, name, address, phone
                        FROM humansa_clinics
                        WHERE name = %s
                    """
                    cursor.execute(exact_query, (clinic_name,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(
                            f"✅ Found clinic by exact match: {row['name']}")
                        return dict(row)

                    # If no exact match, try fuzzy matching with ILIKE
                    fuzzy_query = """
                        SELECT clinic_code, name, address, phone
                        FROM humansa_clinics
                        WHERE name ILIKE %s
                        ORDER BY name
                        LIMIT 1
                    """
                    fuzzy_pattern = f"%{clinic_name}%"
                    cursor.execute(fuzzy_query, (fuzzy_pattern,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(
                            f"✅ Found clinic by fuzzy match: {row['name']} (searched for: {clinic_name})")
                        return dict(row)

                    logger.info(f"❌ No clinic found for name: {clinic_name}")
                    return None
        except Exception as e:
            logger.error(f"Error finding clinic {clinic_name}: {e}")
            return None

    def search_doctors_with_fallback(self, name: Optional[str] = None, specialty: Optional[str] = None,
                                     city: Optional[str] = None, limit: int = 5) -> List[Dict[str, Any]]:
        """Search doctors with fuzzy matching and fallback to general results."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    results = []

                    # Try specific search first
                    conditions = []
                    params = []

                    if name:
                        conditions.append("d.name ILIKE %s")
                        params.append(f"%{name}%")

                    if specialty:
                        conditions.append("d.expertise ILIKE %s")
                        params.append(f"%{specialty}%")

                    if city:
                        conditions.append("c.address ILIKE %s")
                        params.append(f"%{city}%")

                    if conditions:
                        specific_query = f"""
                            SELECT d.doctor_code, d.clinic_code, d.name, d.title, 
                                   d.expertise, d.bio, d.registration_fee,
                                   c.name as clinic_name, c.address, c.phone
                            FROM humansa_doctor d
                            LEFT JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
                            WHERE {' AND '.join(conditions)}
                            ORDER BY d.name
                            LIMIT %s
                        """
                        params.append(limit)
                        cursor.execute(specific_query, params)
                        results = [dict(row) for row in cursor.fetchall()]

                    # If no specific results, get general fallback
                    if not results:
                        fallback_query = """
                            SELECT d.doctor_code, d.clinic_code, d.name, d.title, 
                                   d.expertise, d.bio, d.registration_fee,
                                   c.name as clinic_name, c.address, c.phone
                            FROM humansa_doctor d
                            LEFT JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
                            ORDER BY d.name
                            LIMIT %s
                        """
                        cursor.execute(fallback_query, (limit,))
                        results = [dict(row) for row in cursor.fetchall()]
                        logger.info(
                            f"📋 Using fallback: returned {len(results)} general doctors")
                    else:
                        logger.info(
                            f"🎯 Found {len(results)} doctors matching search criteria")

                    return results
        except Exception as e:
            logger.error(f"Error searching doctors: {e}")
            return []

    def find_doctor_availability_with_fallback(self, doctor_name: str, date_str: Optional[str] = None) -> Dict[str, Any]:
        """Find doctor availability with improved fallback strategies."""
        try:
            # First try exact doctor name
            availability = self.find_doctor_availability(doctor_name, date_str)
            if availability:
                return {
                    "doctor_found": True,
                    "exact_match": True,
                    "availability": availability,
                    "search_method": "exact_name"
                }

            # Try fuzzy search for doctor
            doctor_info = self.find_doctor_by_name(doctor_name)
            if doctor_info:
                # Found doctor with fuzzy match, try availability again
                actual_name = doctor_info['name']
                availability = self.find_doctor_availability(
                    actual_name, date_str)
                return {
                    "doctor_found": True,
                    "exact_match": False,
                    "found_doctor_name": actual_name,
                    "availability": availability,
                    "search_method": "fuzzy_name"
                }

            # If no doctor found, suggest similar doctors
            similar_doctors = self.search_doctors_with_fallback(
                name=doctor_name, limit=3)
            return {
                "doctor_found": False,
                "exact_match": False,
                "suggested_doctors": similar_doctors,
                "availability": [],
                "search_method": "suggestion",
                "message": f"Doctor '{doctor_name}' not found. Here are similar doctors available."
            }

        except Exception as e:
            logger.error(f"Error in availability search with fallback: {e}")
            return {
                "doctor_found": False,
                "exact_match": False,
                "availability": [],
                "error": str(e),
                "search_method": "error"
            }

    def find_doctor_availability_range_with_fallback(self, doctor_name: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Find doctor availability across a date range with fuzzy search and intelligent fallback."""
        try:
            # First try to find the doctor with fuzzy matching
            doctor_info = self.find_doctor_by_name(doctor_name)

            if doctor_info:
                # Doctor found, get availability for date range
                with self.get_connection() as conn:
                    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                        query = """
                            SELECT shift_date, start_time, end_time, remaining_slots
                            FROM humansa_schedule 
                            WHERE doctor_code = %s 
                            AND shift_date BETWEEN %s AND %s
                            AND remaining_slots > 0
                            ORDER BY shift_date, start_time
                        """
                        cursor.execute(
                            query, (doctor_info['doctor_code'], start_date, end_date))
                        slots = cursor.fetchall()

                        # Group by date
                        available_dates = []
                        availability = []
                        current_date = None

                        for slot in slots:
                            slot_dict = dict(slot)
                            availability.append(slot_dict)

                            slot_date = slot_dict['shift_date'].strftime(
                                '%Y-%m-%d')
                            if slot_date != current_date:
                                available_dates.append(slot_date)
                                current_date = slot_date

                        logger.info(
                            f"✅ Found {len(availability)} slots across {len(available_dates)} days for {doctor_info['name']} ({start_date} to {end_date})")

                        return {
                            "doctor_found": True,
                            "found_doctor_name": doctor_info['name'],
                            "exact_match": doctor_info['name'].lower() == doctor_name.lower(),
                            "availability": availability,
                            "available_dates": available_dates,
                            "search_method": "exact" if doctor_info['name'].lower() == doctor_name.lower() else "fuzzy"
                        }

            # Doctor not found, suggest similar doctors with availability in the date range
            similar_doctors = self.get_doctors_with_availability_in_range(
                start_date, end_date, limit=5)

            return {
                "doctor_found": False,
                "exact_match": False,
                "suggested_doctors": similar_doctors,
                "availability": [],
                "available_dates": [],
                "search_method": "suggestion",
                "message": f"Doctor '{doctor_name}' not found. Here are similar doctors with availability in the requested date range."
            }

        except Exception as e:
            logger.error(
                f"Error in availability range search with fallback: {e}")
            return {
                "doctor_found": False,
                "exact_match": False,
                "availability": [],
                "available_dates": [],
                "error": str(e),
                "search_method": "error"
            }

    def get_doctors_with_availability_in_range(self, start_date: str, end_date: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get doctors who have availability in the specified date range."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    query = """
                        SELECT DISTINCT d.doctor_code, d.name, d.title, d.expertise, 
                               c.name as clinic_name, COUNT(s.shift_date) as available_slots
                        FROM humansa_doctor d
                        LEFT JOIN humansa_clinics c ON d.clinic_code = c.clinic_code
                        LEFT JOIN humansa_schedule s ON d.doctor_code = s.doctor_code
                        WHERE s.shift_date BETWEEN %s AND %s
                        AND s.remaining_slots > 0
                        GROUP BY d.doctor_code, d.name, d.title, d.expertise, c.name
                        ORDER BY available_slots DESC
                        LIMIT %s
                    """
                    cursor.execute(query, (start_date, end_date, limit))
                    doctors = cursor.fetchall()
                    return [dict(doc) for doc in doctors]
        except Exception as e:
            logger.error(
                f"Error getting doctors with availability in range: {e}")
            return []

    def search_clinics_with_fallback(self, clinic_name: Optional[str] = None, city: Optional[str] = None,
                                     specialty: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Search clinics with fuzzy matching and intelligent fallback."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build dynamic query based on available filters
                    conditions = []
                    params = []

                    if clinic_name:
                        conditions.append("c.name ILIKE %s")
                        params.append(f"%{clinic_name}%")

                    if city:
                        conditions.append("c.address ILIKE %s")
                        params.append(f"%{city}%")

                    if specialty:
                        conditions.append("d.expertise ILIKE %s")
                        params.append(f"%{specialty}%")

                    where_clause = " AND ".join(
                        conditions) if conditions else "1=1"

                    query = f"""
                        SELECT DISTINCT c.clinic_code, c.name, c.address, c.phone,
                               COUNT(DISTINCT d.doctor_code) as doctor_count,
                               STRING_AGG(DISTINCT d.expertise, ', ') as specialties
                        FROM humansa_clinics c
                        LEFT JOIN humansa_doctor d ON c.clinic_code = d.clinic_code
                        WHERE {where_clause}
                        GROUP BY c.clinic_code, c.name, c.address, c.phone
                        ORDER BY doctor_count DESC
                        LIMIT %s
                    """
                    params.append(limit)

                    cursor.execute(query, params)
                    clinics = cursor.fetchall()

                    if clinics:
                        search_method = "filtered" if conditions else "all"
                        return {
                            "clinics_found": True,
                            "clinics": [dict(clinic) for clinic in clinics],
                            "total_found": len(clinics),
                            "search_method": search_method,
                            "filters_applied": {
                                "clinic_name": clinic_name,
                                "city": city,
                                "specialty": specialty
                            }
                        }
                    else:
                        # No matches, return all clinics
                        fallback_query = """
                            SELECT clinic_code, name, address, phone
                            FROM humansa_clinics
                            ORDER BY name
                            LIMIT %s
                        """
                        cursor.execute(fallback_query, (limit,))
                        all_clinics = cursor.fetchall()

                        return {
                            "clinics_found": True,
                            "clinics": [dict(clinic) for clinic in all_clinics],
                            "total_found": len(all_clinics),
                            "search_method": "fallback",
                            "message": "No clinics matched your criteria. Here are our available clinics."
                        }

        except Exception as e:
            logger.error(f"Error searching clinics: {e}")
            return {
                "clinics_found": False,
                "clinics": [],
                "error": str(e),
                "search_method": "error"
            }

    def search_services_with_fallback(self, service_name: Optional[str] = None, specialty: Optional[str] = None,
                                      clinic_name: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Search medical services with fuzzy matching and intelligent fallback."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build dynamic query based on available filters
                    conditions = []
                    params = []

                    if service_name:
                        conditions.append("ms.service_name ILIKE %s")
                        params.append(f"%{service_name}%")

                    if specialty:
                        conditions.append("ms.description ILIKE %s")
                        params.append(f"%{specialty}%")

                    if clinic_name:
                        conditions.append("c.name ILIKE %s")
                        params.append(f"%{clinic_name}%")

                    where_clause = " AND ".join(
                        conditions) if conditions else "1=1"

                    query = f"""
                        SELECT ms.clinic_code, ms.service_name, ms.price, 
                               ms.description, c.name as clinic_name
                        FROM humansa_medical_service ms
                        LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                        WHERE {where_clause}
                        ORDER BY ms.service_name
                        LIMIT %s
                    """
                    params.append(limit)

                    cursor.execute(query, params)
                    services = cursor.fetchall()

                    if services:
                        search_method = "filtered" if conditions else "all"
                        return {
                            "services_found": True,
                            "services": [dict(service) for service in services],
                            "total_found": len(services),
                            "search_method": search_method,
                            "filters_applied": {
                                "service_name": service_name,
                                "specialty": specialty,
                                "clinic_name": clinic_name
                            }
                        }
                    else:
                        # No matches, return popular services
                        fallback_query = """
                            SELECT ms.clinic_code, ms.service_name, ms.price, 
                                   ms.description, c.name as clinic_name
                            FROM humansa_medical_service ms
                            LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                            ORDER BY ms.service_name
                            LIMIT %s
                        """
                        cursor.execute(fallback_query, (limit,))
                        all_services = cursor.fetchall()

                        return {
                            "services_found": True,
                            "services": [dict(service) for service in all_services],
                            "total_found": len(all_services),
                            "search_method": "fallback",
                            "message": "No services matched your criteria. Here are our available services."
                        }

        except Exception as e:
            logger.error(f"Error searching services: {e}")
            return {
                "services_found": False,
                "services": [],
                "error": str(e),
                "search_method": "error"
            }

    def get_pricing_with_fallback(self, service_type: str, clinic_name: Optional[str] = None,
                                  specialty: Optional[str] = None, limit: int = 5) -> Dict[str, Any]:
        """Get pricing information with fuzzy search and intelligent fallback."""
        try:
            with self.get_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    # Build dynamic query based on available filters
                    conditions = ["ms.service_name ILIKE %s"]
                    params = [f"%{service_type}%"]

                    if clinic_name:
                        conditions.append("c.name ILIKE %s")
                        params.append(f"%{clinic_name}%")

                    if specialty:
                        conditions.append("ms.description ILIKE %s")
                        params.append(f"%{specialty}%")

                    where_clause = " AND ".join(conditions)

                    query = f"""
                        SELECT ms.clinic_code, ms.service_name, ms.price, 
                               ms.description, c.name as clinic_name, c.address
                        FROM humansa_medical_service ms
                        LEFT JOIN humansa_clinics c ON ms.clinic_code = c.clinic_code
                        WHERE {where_clause}
                        ORDER BY ms.price
                        LIMIT %s
                    """
                    params.append(limit)

                    cursor.execute(query, params)
                    services = cursor.fetchall()

                    if services:
                        return {
                            "pricing_found": True,
                            "services": [dict(service) for service in services],
                            "total_found": len(services),
                            "search_method": "matched",
                            "filters_applied": {
                                "service_type": service_type,
                                "clinic_name": clinic_name,
                                "specialty": specialty
                            }
                        }
                    else:
                        # No matches, return general pricing
                        fallback_query = """
                            SELECT service_code, service_name, category, description, 
                                   base_price, currency
                            FROM humansa_service
                            ORDER BY service_name
                            LIMIT %s
                        """
                        cursor.execute(fallback_query, (limit,))
                        all_services = cursor.fetchall()

                        return {
                            "pricing_found": True,
                            "services": [dict(service) for service in all_services],
                            "total_found": len(all_services),
                            "search_method": "fallback",
                            "message": f"No exact matches for '{service_type}'. Here are our available services and pricing."
                        }

        except Exception as e:
            logger.error(f"Error getting pricing: {e}")
            return {
                "pricing_found": False,
                "services": [],
                "error": str(e),
                "search_method": "error"
            }


# Global database instance
db = HumansaDatabase()
