---
description: Update current session with progress notes
allowed-tools: ["Write", "Edit", "Bash", "Read"]
---

# Session Update Command

Add timestamped progress updates to the current active session.

## Usage
```
/session-update [notes]
```

## Implementation

**Step 1: Check for active session**
```bash
# Check if there's an active session
if [ ! -f "sessions/.current-session" ]; then
    echo "No active session found. Use /session-start to begin a session."
    exit 1
fi

# Read current session file
CURRENT_SESSION=$(cat sessions/.current-session)
if [ ! -f "$CURRENT_SESSION" ]; then
    echo "Current session file not found. Use /session-start to begin a session."
    exit 1
fi
```

**Step 2: Generate update timestamp**
```bash
UPDATE_TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
```

**Step 3: Capture context**
Automatically gather:
- Git status and recent changes
- Current branch and commit
- Any todo list updates
- File modifications since last update

**Step 4: Create progress entry**
Add new progress entry to the session file:

```markdown
### [UPDATE_TIMESTAMP] - Progress Update
**Git Status**: [auto-detected]
**Current Branch**: [auto-detected]
**Recent Changes**: [auto-detected]

**Notes**: [USER_NOTES or auto-generated summary]

**Files Modified**:
- [List of recently modified files]

**Issues/Solutions**:
- [Any problems encountered and how they were resolved]

**Next Steps**:
- [Immediate next actions]

---
```

**Step 5: Auto-summary generation**
If no custom notes provided, generate automatic summary based on:
- Recent git commits
- File modifications
- Time since last update
- Current directory context

**Step 6: Update session metadata**
Update the session file's last modified timestamp and increment update count.

## Context Capture Rules
- **Git Changes**: Show `git status` and `git diff --name-only`
- **Recent Commits**: Show last 3 commits with `git log --oneline -3`
- **File Changes**: Detect recently modified files in project
- **Time Tracking**: Calculate time since last update
- **Todo Progress**: Check for todo list changes

## Auto-Summary Examples
When no notes provided, generate summaries like:
- "Working on authentication module - modified 3 files in YouWoAI-Server-v1/src/v1/auth/"
- "Debugging payment integration - fixed Stripe webhook handling"
- "Implementing session management - added custom Claude Code commands"

## Error Handling
- No active session: Prompt to start session
- Invalid session file: Suggest session recovery
- Git not available: Continue with file-based tracking
- Permission issues: Guide user to fix permissions