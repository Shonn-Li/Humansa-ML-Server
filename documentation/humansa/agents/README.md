# Humansa Agent Documentation

This directory contains detailed implementation documentation for each Humansa agent.

## Available Agents

### 1. [Appointment Agent](appointment_agent.md)
- **Purpose**: Handle medical appointment bookings with intelligent form management
- **Key Features**:
  - Progressive information collection
  - Form-based approval system
  - Multi-turn conversation support
  - Appointment history tracking
  - Smart validation and suggestions

### 2. General Medical Agent
- **Purpose**: Answer general medical questions and provide health information
- **Key Features**:
  - Medical knowledge base
  - Symptom analysis
  - Health tips and recommendations

### 3. Product Agent
- **Purpose**: Provide information about medical products and medications
- **Key Features**:
  - Product search and information
  - Medication details
  - Usage instructions

### 4. Diagnosis Agent
- **Purpose**: Assist with preliminary symptom assessment
- **Key Features**:
  - Symptom collection
  - Basic triage
  - Recommendation for appropriate care

### 5. Medication Agent
- **Purpose**: Manage medication information and reminders
- **Key Features**:
  - Medication database
  - Drug interactions
  - Dosage information

## Architecture Overview

All agents follow a consistent pattern:

1. **Agent Interface**: Each agent implements a standard interface for the orchestrator
2. **Tool Integration**: Agents can use tools but handle their own validation
3. **Response Format**: Structured responses that orchestrators understand
4. **State Management**: Agents are stateless; context is passed by orchestrator

## Best Practices

1. **Validation**: Agents validate their own requirements, not orchestrators
2. **Clear Status**: Return clear status codes (need_info, success, error)
3. **Progressive Collection**: Collect information naturally over multiple turns
4. **Error Handling**: Graceful degradation with helpful error messages
5. **Testing**: Comprehensive test suites with multi-turn scenarios