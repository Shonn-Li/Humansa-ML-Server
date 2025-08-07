---
description: List all development sessions with summaries
allowed-tools: ["Read", "Bash", "Glob"]
---

# Session List Command

Display a list of all development sessions with summaries and metadata.

## Usage
```
/session-list
```

## Implementation

**Step 1: Scan sessions directory**
```bash
# Find all session files
SESSION_FILES=$(find sessions/ -name "*.md" -not -name ".*" | sort -r)

if [ -z "$SESSION_FILES" ]; then
    echo "No sessions found."
    echo "Use /session-start to create your first session."
    exit 0
fi
```

**Step 2: Identify active session**
```bash
# Check for active session
ACTIVE_SESSION=""
if [ -f "sessions/.current-session" ]; then
    ACTIVE_SESSION=$(cat sessions/.current-session)
fi
```

**Step 3: Generate session list**
```markdown
# Development Sessions Overview

## Active Session
[Display currently active session with special highlighting]

## Recent Sessions
[List sessions in reverse chronological order]

## Session History
```

**Step 4: Parse each session file**
For each session, extract and display:
```markdown
### [SESSION_DATE] - [SESSION_NAME] [ACTIVE_INDICATOR]
- **Duration**: [CALCULATED_DURATION]
- **Status**: [Active/Completed]
- **Goals**: [COMPLETED]/[TOTAL] completed
- **Updates**: [UPDATE_COUNT] progress updates
- **Summary**: [BRIEF_DESCRIPTION]
- **Key Accomplishments**: [TOP_2_ACCOMPLISHMENTS]

---
```

**Step 5: Provide session statistics**
```markdown
## Session Statistics
- **Total Sessions**: [COUNT]
- **Active Sessions**: [ACTIVE_COUNT]
- **Completed Sessions**: [COMPLETED_COUNT]
- **Total Development Time**: [AGGREGATE_TIME]
- **Average Session Duration**: [AVERAGE_DURATION]
- **Most Productive Period**: [TIME_ANALYSIS]

## Quick Actions
- `/session-start [name]` - Start new session
- `/session-current` - View active session
- View specific session: `Read sessions/[filename]`
```

## Session Analysis Features
- **Goal Completion Rate**: Calculate percentage of goals achieved per session
- **Update Frequency**: Analyze how often sessions were updated
- **Duration Patterns**: Identify typical session lengths
- **Activity Trends**: Show development patterns over time
- **Topic Analysis**: Categorize sessions by type of work

## Display Formatting
- **Active Session**: Highlighted with special indicator (🟢 ACTIVE)
- **Recent Sessions**: Last 5-10 sessions prominently displayed
- **Older Sessions**: Grouped by date ranges (This Week, Last Week, etc.)
- **Status Indicators**: Visual indicators for session status
- **Duration Format**: Human-readable time formats (2h 30m, 45m, etc.)

## Sorting and Filtering Options
- **Default**: Reverse chronological order (newest first)
- **By Duration**: Longest sessions first
- **By Completion**: Most completed goals first
- **By Activity**: Most updates first

## Session File Parsing
Extract information from session files:
- **Header Metadata**: Session name, start time, status
- **Goal Tracking**: Parse goal completion checkboxes
- **Update Count**: Count progress update entries
- **Duration Calculation**: Calculate from start to end time
- **Summary Generation**: Extract key accomplishments

## Error Handling
- **Corrupted Session Files**: Skip and note issues
- **Permission Problems**: Graceful error messages
- **Empty Sessions Directory**: Helpful guidance
- **Parsing Errors**: Continue with available information

## Smart Features
- **Session Recommendations**: Suggest sessions to review based on current work
- **Pattern Recognition**: Identify common session types
- **Productivity Insights**: Show most productive sessions
- **Goal Tracking**: Highlight recurring goals across sessions

## Integration
- **Git Integration**: Show commits per session
- **File Tracking**: Show files modified per session
- **Time Analysis**: Aggregate development time statistics
- **Progress Tracking**: Overall project progress across sessions