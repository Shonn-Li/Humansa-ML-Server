"""
StreamingValidator - Validates OpenAI Response API streaming format compliance
"""

import asyncio
import json
import logging
from typing import Dict, List, Set, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class EventValidation:
    """Tracks validation state for an event"""
    event_id: str
    event_type: str
    timestamp: datetime
    has_completion: bool = False
    completion_type: Optional[str] = None
    completion_timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class StreamingValidator:
    """Validates OpenAI Response API streaming format compliance"""
    
    # OpenAI event pairs that require completion
    EVENT_PAIRS = {
        'response.output_item.added': 'response.output_item.done',
        'response.content_part.added': 'response.content_part.done',
        'response.function_tool_call.in_progress': 'response.function_tool_call.completed',
        'response.web_search_call.in_progress': 'response.web_search_call.completed',
        'response.file_search_call.in_progress': 'response.file_search_call.completed',
        'response.reasoning_part.added': 'response.reasoning_part.done',
    }
    
    # Required event lifecycle
    REQUIRED_LIFECYCLE = [
        'response.created',
        'response.in_progress',
        ('response.completed', 'response.failed')  # One of these must occur
    ]
    
    def __init__(self):
        self.events: List[Dict[str, Any]] = []
        self.event_validations: Dict[str, EventValidation] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.lifecycle_events: Set[str] = set()
        
    def track_event(self, event: Dict[str, Any]) -> None:
        """Track a streaming event for validation"""
        self.events.append(event)
        event_type = event.get('type', '')
        event_id = event.get('id') or event.get('item_id') or event.get('output_id')
        
        # Track lifecycle events
        if event_type in ['response.created', 'response.in_progress', 
                         'response.completed', 'response.failed']:
            self.lifecycle_events.add(event_type)
        
        # Track paired events
        if event_type in self.EVENT_PAIRS:
            if event_id:
                validation = EventValidation(
                    event_id=event_id,
                    event_type=event_type,
                    timestamp=datetime.now(),
                    metadata=event
                )
                self.event_validations[f"{event_type}:{event_id}"] = validation
                
        # Check for completion events
        for start_event, end_event in self.EVENT_PAIRS.items():
            if event_type == end_event and event_id:
                key = f"{start_event}:{event_id}"
                if key in self.event_validations:
                    self.event_validations[key].has_completion = True
                    self.event_validations[key].completion_type = end_event
                    self.event_validations[key].completion_timestamp = datetime.now()
                else:
                    self.warnings.append(
                        f"Completion event {end_event} for id {event_id} without matching start event"
                    )
    
    def validate_event_structure(self, event: Dict[str, Any]) -> List[str]:
        """Validate individual event structure"""
        errors = []
        
        # Required fields
        if 'type' not in event:
            errors.append("Event missing required 'type' field")
            
        # Event-specific validation
        event_type = event.get('type', '')
        
        if event_type == 'response.output_item.added':
            if 'item' not in event:
                errors.append(f"{event_type} missing required 'item' field")
                
        elif event_type == 'response.output_text.delta':
            if 'delta' not in event:
                errors.append(f"{event_type} missing required 'delta' field")
                
        elif event_type == 'response.citations':
            if 'citations' not in event:
                errors.append(f"{event_type} missing required 'citations' field")
                
        return errors
    
    def validate_lifecycle(self) -> List[str]:
        """Validate event lifecycle compliance"""
        errors = []
        
        # Check required lifecycle events
        if 'response.created' not in self.lifecycle_events:
            errors.append("Missing required 'response.created' event")
            
        if 'response.in_progress' not in self.lifecycle_events:
            errors.append("Missing required 'response.in_progress' event")
            
        # Must have either completed or failed
        if not ('response.completed' in self.lifecycle_events or 
                'response.failed' in self.lifecycle_events):
            errors.append("Missing required completion event (response.completed or response.failed)")
            
        # Can't have both completed and failed
        if ('response.completed' in self.lifecycle_events and 
            'response.failed' in self.lifecycle_events):
            errors.append("Both response.completed and response.failed present - only one allowed")
            
        return errors
    
    def validate_event_pairs(self) -> List[str]:
        """Validate all paired events have completions"""
        errors = []
        
        for key, validation in self.event_validations.items():
            if not validation.has_completion:
                errors.append(
                    f"Event {validation.event_type} with id {validation.event_id} "
                    f"missing completion event {self.EVENT_PAIRS.get(validation.event_type)}"
                )
                
        return errors
    
    def validate_event_ordering(self) -> List[str]:
        """Validate events are in correct order"""
        errors = []
        
        # Track order of key events
        created_index = -1
        in_progress_index = -1
        completed_index = -1
        
        for i, event in enumerate(self.events):
            event_type = event.get('type', '')
            
            if event_type == 'response.created':
                created_index = i
            elif event_type == 'response.in_progress':
                in_progress_index = i
            elif event_type in ['response.completed', 'response.failed']:
                completed_index = i
                
        # Validate ordering
        if created_index >= 0 and in_progress_index >= 0:
            if created_index > in_progress_index:
                errors.append("response.created must come before response.in_progress")
                
        if in_progress_index >= 0 and completed_index >= 0:
            if in_progress_index > completed_index:
                errors.append("response.in_progress must come before completion event")
                
        return errors
    
    def validate_streaming_format(self) -> Tuple[bool, Dict[str, Any]]:
        """Perform complete validation of streaming format"""
        all_errors = []
        
        # Validate each event structure
        for event in self.events:
            event_errors = self.validate_event_structure(event)
            all_errors.extend(event_errors)
            
        # Validate lifecycle
        lifecycle_errors = self.validate_lifecycle()
        all_errors.extend(lifecycle_errors)
        
        # Validate event pairs
        pair_errors = self.validate_event_pairs()
        all_errors.extend(pair_errors)
        
        # Validate ordering
        ordering_errors = self.validate_event_ordering()
        all_errors.extend(ordering_errors)
        
        # Compile results
        is_valid = len(all_errors) == 0
        
        report = {
            'valid': is_valid,
            'total_events': len(self.events),
            'errors': all_errors,
            'warnings': self.warnings,
            'lifecycle_complete': len(self.lifecycle_events) >= 3,
            'unpaired_events': [
                {
                    'type': v.event_type,
                    'id': v.event_id,
                    'timestamp': v.timestamp.isoformat()
                }
                for v in self.event_validations.values() 
                if not v.has_completion
            ],
            'event_summary': self._get_event_summary()
        }
        
        return is_valid, report
    
    def _get_event_summary(self) -> Dict[str, int]:
        """Get summary of event types"""
        summary = defaultdict(int)
        for event in self.events:
            summary[event.get('type', 'unknown')] += 1
        return dict(summary)
    
    async def validate_streaming_response(self, response_generator) -> Tuple[bool, Dict[str, Any]]:
        """Validate a complete streaming response"""
        try:
            async for event in response_generator:
                if isinstance(event, str):
                    # Handle SSE format
                    if event.startswith('data: '):
                        data_str = event[6:]
                        if data_str == '[DONE]':
                            break
                        try:
                            event_data = json.loads(data_str)
                            self.track_event(event_data)
                        except json.JSONDecodeError:
                            self.errors.append(f"Invalid JSON in streaming event: {data_str[:100]}")
                else:
                    # Direct event object
                    self.track_event(event)
                    
        except Exception as e:
            self.errors.append(f"Error processing streaming response: {str(e)}")
            
        return self.validate_streaming_format()


class OpenAIFormatValidator:
    """Validates compliance with OpenAI's exact response format"""
    
    @staticmethod
    def validate_chat_completion_chunk(chunk: Dict[str, Any]) -> List[str]:
        """Validate a single chat completion chunk"""
        errors = []
        
        # Required fields for OpenAI format
        required_fields = ['id', 'object', 'created', 'model', 'choices']
        for field in required_fields:
            if field not in chunk:
                errors.append(f"Missing required field '{field}' in chunk")
                
        # Validate object type
        if chunk.get('object') != 'chat.completion.chunk':
            errors.append(f"Invalid object type: {chunk.get('object')}, expected 'chat.completion.chunk'")
            
        # Validate choices structure
        if 'choices' in chunk:
            if not isinstance(chunk['choices'], list):
                errors.append("'choices' must be a list")
            else:
                for i, choice in enumerate(chunk['choices']):
                    if 'index' not in choice:
                        errors.append(f"Choice {i} missing 'index' field")
                    if 'delta' not in choice:
                        errors.append(f"Choice {i} missing 'delta' field")
                        
        return errors
    
    @staticmethod
    def validate_final_response(response: Dict[str, Any]) -> List[str]:
        """Validate final response format"""
        errors = []
        
        required_fields = ['id', 'object', 'created', 'model', 'choices', 'usage']
        for field in required_fields:
            if field not in response:
                errors.append(f"Missing required field '{field}' in final response")
                
        # Validate usage
        if 'usage' in response:
            usage_fields = ['prompt_tokens', 'completion_tokens', 'total_tokens']
            for field in usage_fields:
                if field not in response['usage']:
                    errors.append(f"Missing usage field '{field}'")
                    
        return errors