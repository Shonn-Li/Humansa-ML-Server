"""
Booking Workflow Validator for Humansa Agent
Ensures proper sequence: Search → Check Availability → Book
"""

import logging
from typing import List, Dict, Tuple, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BookingWorkflowValidator:
    """Validates and enforces proper booking workflow sequence."""
    
    BOOKING_STATES = {
        "INITIAL": "initial",
        "DOCTOR_SEARCHED": "doctor_searched",
        "AVAILABILITY_CHECKED": "availability_checked",
        "BOOKING_CONFIRMED": "booking_confirmed"
    }
    
    REQUIRED_WORKFLOW = [
        "search_doctors",
        "find_doctor_availability",
        "book_appointment"
    ]
    
    def __init__(self):
        self.workflow_state = {}  # Track state per user/session
        self.tool_history = {}    # Track tool calls per user/session
        
    def reset_workflow(self, session_id: str):
        """Reset workflow state for a session."""
        self.workflow_state[session_id] = self.BOOKING_STATES["INITIAL"]
        self.tool_history[session_id] = []
        logger.info(f"🔄 Reset booking workflow for session: {session_id}")
        
    def validate_tool_call(self, session_id: str, tool_name: str, params: Dict) -> Tuple[bool, Optional[str]]:
        """
        Validate if a tool call is appropriate for current workflow state.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Initialize session if needed
        if session_id not in self.workflow_state:
            self.reset_workflow(session_id)
            
        current_state = self.workflow_state[session_id]
        history = self.tool_history[session_id]
        
        # Record the tool call
        history.append({
            "tool": tool_name,
            "params": params,
            "timestamp": datetime.now().isoformat()
        })
        
        # Validate based on tool and state
        if tool_name == "book_appointment":
            # Must have searched and checked availability first
            if current_state != self.BOOKING_STATES["AVAILABILITY_CHECKED"]:
                missing_steps = []
                if "search_doctors" not in [h["tool"] for h in history]:
                    missing_steps.append("search for doctors")
                if "find_doctor_availability" not in [h["tool"] for h in history]:
                    missing_steps.append("check doctor availability")
                    
                error_msg = f"Cannot book appointment. Must first: {', '.join(missing_steps)}"
                logger.warning(f"❌ Booking validation failed: {error_msg}")
                return False, error_msg
                
        elif tool_name == "find_doctor_availability":
            # Should have searched for doctors first (but not strictly required)
            if current_state == self.BOOKING_STATES["INITIAL"]:
                logger.info("⚠️ Checking availability without searching doctors first")
                
        # Update state based on tool
        if tool_name == "search_doctors":
            self.workflow_state[session_id] = self.BOOKING_STATES["DOCTOR_SEARCHED"]
        elif tool_name == "find_doctor_availability":
            self.workflow_state[session_id] = self.BOOKING_STATES["AVAILABILITY_CHECKED"]
        elif tool_name == "book_appointment":
            self.workflow_state[session_id] = self.BOOKING_STATES["BOOKING_CONFIRMED"]
            
        logger.info(f"✅ Tool '{tool_name}' validated. State: {self.workflow_state[session_id]}")
        return True, None
        
    def get_next_required_tool(self, session_id: str) -> Optional[str]:
        """Get the next required tool in the booking workflow."""
        if session_id not in self.tool_history:
            return "search_doctors"
            
        history = [h["tool"] for h in self.tool_history[session_id]]
        
        for required_tool in self.REQUIRED_WORKFLOW:
            if required_tool not in history:
                return required_tool
                
        return None
        
    def get_workflow_progress(self, session_id: str) -> Dict:
        """Get current workflow progress."""
        if session_id not in self.workflow_state:
            self.reset_workflow(session_id)
            
        history = self.tool_history.get(session_id, [])
        completed_steps = [h["tool"] for h in history]
        
        progress = {
            "current_state": self.workflow_state[session_id],
            "completed_steps": completed_steps,
            "required_steps": self.REQUIRED_WORKFLOW,
            "next_step": self.get_next_required_tool(session_id),
            "is_complete": all(step in completed_steps for step in self.REQUIRED_WORKFLOW)
        }
        
        return progress
        
    def enforce_workflow_in_prompt(self, query: str, session_id: str) -> str:
        """Add workflow enforcement to the query prompt."""
        progress = self.get_workflow_progress(session_id)
        
        if "book" in query.lower() or "appointment" in query.lower():
            if not progress["is_complete"]:
                next_step = progress["next_step"]
                enforcement = f"\n\nWORKFLOW ENFORCEMENT: "
                
                if next_step == "search_doctors":
                    enforcement += "You must first search for doctors before booking."
                elif next_step == "find_doctor_availability":
                    enforcement += "You must check doctor availability before booking."
                    
                return query + enforcement
                
        return query