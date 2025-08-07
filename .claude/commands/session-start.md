---
description: Start a new development session with optional name
allowed-tools: ["Write", "Bash", "Read"]
---

# Session Start Command

Start a new development session with optional descriptive name.

## Usage
```
/session-start [name]
```

## Implementation

**Step 1: Create session filename**
```bash
# Generate timestamp
TIMESTAMP=$(date +"%Y-%m-%d-%H%M")
SESSION_NAME="$ARGUMENTS"

# Create filename
if [ -n "$SESSION_NAME" ]; then
    FILENAME="sessions/${TIMESTAMP}-${SESSION_NAME}.md"
else
    FILENAME="sessions/${TIMESTAMP}.md"
fi

# Update current session tracker
echo "$FILENAME" > sessions/.current-session
```

**Step 2: Initialize session file**
Create a new session file with the following structure:

```markdown
# Development Session - [TIMESTAMP] - [NAME]

## Session Info
- **Started**: [TIMESTAMP]
- **Name**: [NAME or "General Development"]
- **Status**: Active

## Goals
- [ ] [To be defined based on context]

## Progress Log

### [TIMESTAMP] - Session Started
- Initiated new development session
- Session goals to be defined

## Notes
- Session tracking active
- Use `/session-update` to log progress
- Use `/session-end` to conclude session

## Context
- Project: YouWoAI Multi-Platform System
- Current branch: [auto-detect from git]
- Recent commits: [auto-detect from git log]
```

**Step 3: Display confirmation**
Show the user:
- Session filename created
- Session goals prompt
- Available commands reminder

**Step 4: Git context capture**
Automatically capture current git status and recent commits for context.

## Session Goals Prompt
If no clear goals are evident from the context, prompt the user to define session objectives.

## Available Commands
Remind user of available session commands:
- `/session-update` - Add progress updates
- `/session-current` - View current session
- `/session-end` - End and summarize session
- `/session-list` - List all sessions