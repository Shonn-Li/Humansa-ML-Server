---
description: View current session status and information
allowed-tools: ["Read", "Bash"]
---

# Session Current Command

Display the status and information of the current active session.

## Usage
```
/session-current
```

## Implementation

**Step 1: Check for active session**
```bash
# Check if there's an active session
if [ ! -f "sessions/.current-session" ]; then
    echo "No active session found."
    echo "Use /session-start to begin a new session."
    exit 0
fi

# Read current session file
CURRENT_SESSION=$(cat sessions/.current-session)
if [ ! -f "$CURRENT_SESSION" ]; then
    echo "Current session file not found: $CURRENT_SESSION"
    echo "Session tracker may be corrupted. Use /session-start to begin a new session."
    exit 1
fi
```

**Step 2: Parse session information**
Extract key information from the session file:
- Session name and timestamp
- Start time and duration
- Current goals and progress
- Number of updates
- Recent activity

**Step 3: Display session overview**
```markdown
# Current Session Status

## Session Info
- **File**: [SESSION_FILENAME]
- **Started**: [SESSION_START_TIME]
- **Duration**: [CALCULATED_DURATION]
- **Last Update**: [LAST_UPDATE_TIME]
- **Total Updates**: [UPDATE_COUNT]

## Session Goals
[Display current goals from session file]

## Recent Activity
[Show last 3 progress updates]

## Git Context
- **Current Branch**: [CURRENT_BRANCH]
- **Recent Commits**: [LAST_3_COMMITS]
- **Uncommitted Changes**: [GIT_STATUS_SUMMARY]

## Quick Actions
- `/session-update [notes]` - Add progress update
- `/session-end` - End current session
- `/session-list` - View all sessions

## Session Statistics
- **Files Modified**: [COUNT]
- **Progress Updates**: [COUNT]
- **Time Active**: [DURATION]
- **Goals Completed**: [COMPLETED_COUNT]/[TOTAL_COUNT]
```

**Step 4: Show recent context**
Display:
- Recent file modifications
- Current working directory
- Active git branch
- Uncommitted changes summary

**Step 5: Provide helpful suggestions**
Based on session state, suggest:
- Next logical steps
- Files that might need attention
- Goals that are ready to be completed
- Areas that need updates

## Information Extraction
- **Session Metadata**: Parse session file header
- **Progress Tracking**: Count updates and calculate statistics
- **Git Integration**: Show current git status
- **Time Calculations**: Calculate session duration and activity
- **Goal Analysis**: Parse and display goal completion status

## Display Format
Use clear, organized format with:
- Color coding for different information types
- Progress indicators for goals
- Time-based information formatting
- Quick action reminders
- Contextual suggestions

## Error Handling
- **No Active Session**: Clear message with instructions
- **Corrupted Session**: Recovery suggestions
- **Git Not Available**: Graceful degradation
- **File Permission Issues**: Helpful error messages

## Smart Suggestions
Based on session analysis:
- "You've been working for 2 hours - consider taking a break"
- "3 goals completed - great progress!"
- "Last update was 45 minutes ago - time for an update?"
- "Uncommitted changes detected - consider committing progress"