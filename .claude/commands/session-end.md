---
description: End current session with comprehensive summary
allowed-tools: ["Write", "Edit", "Bash", "Read"]
---

# Session End Command

End the current development session with a comprehensive summary.

## Usage
```
/session-end
```

## Implementation

**Step 1: Verify active session**
```bash
# Check if there's an active session
if [ ! -f "sessions/.current-session" ]; then
    echo "No active session found. Nothing to end."
    exit 1
fi

# Read current session file
CURRENT_SESSION=$(cat sessions/.current-session)
if [ ! -f "$CURRENT_SESSION" ]; then
    echo "Current session file not found."
    exit 1
fi
```

**Step 2: Generate comprehensive summary**
Create a detailed session summary with:

```markdown
## Session Summary - [END_TIMESTAMP]

### Duration & Timing
- **Session Duration**: [Calculate from start to end]
- **Active Development Time**: [Estimate based on updates]
- **Started**: [SESSION_START_TIME]
- **Ended**: [END_TIMESTAMP]

### Accomplishments
- [List of completed goals and tasks]
- [Major features implemented]
- [Bugs fixed]
- [Code improvements made]

### Git Changes Summary
- **Total Commits**: [Count of commits during session]
- **Files Modified**: [List of modified files]
- **Lines Added/Removed**: [Git diff stats]
- **Branches Worked On**: [List of branches]

### Key Implementation Details
- [Important code changes with explanations]
- [Architecture decisions made]
- [Dependencies added or updated]
- [Configuration changes]

### Problems Encountered & Solutions
- [Issues faced during development]
- [Solutions implemented]
- [Workarounds used]
- [Resources that helped]

### Todo Items
- **Completed**: [List of completed todos]
- **Remaining**: [List of pending todos]
- **New Items Discovered**: [New todos identified]

### Knowledge Gained
- [New techniques learned]
- [Framework/library insights]
- [Best practices discovered]
- [Performance considerations]

### Next Session Preparation
- [Immediate next steps]
- [Files to review]
- [Issues to investigate]
- [Resources to check]

### Technical Notes
- [Important technical details for future reference]
- [API endpoints modified]
- [Database schema changes]
- [Environment configuration updates]

### Team Handoff Notes
- [Information for other developers]
- [Context for code reviews]
- [Testing recommendations]
- [Deployment considerations]

---
**Session Status**: Completed
**Total Updates**: [COUNT]
**Final Commit**: [LATEST_COMMIT_HASH]
```

**Step 3: Update session metadata**
Mark session as completed and update final statistics.

**Step 4: Clear active session**
```bash
# Clear the current session tracker
rm sessions/.current-session
```

**Step 5: Generate session insights**
Provide insights like:
- Most productive time periods
- Types of work done
- Areas of focus
- Efficiency metrics

## Auto-Analysis Features
- **Code Quality**: Analyze code changes for improvements
- **Performance Impact**: Identify performance-related changes
- **Security Considerations**: Flag any security-related modifications
- **Documentation**: Note areas that need documentation
- **Testing**: Identify testing requirements

## Session Archival
- Mark session as completed
- Add session to searchable index
- Update session statistics
- Generate session tags for categorization

## Integration Points
- **Git Integration**: Complete git analysis and statistics
- **Project Tracking**: Update project progress metrics
- **Time Tracking**: Calculate accurate development time
- **Knowledge Base**: Add learnings to project knowledge base

## Error Handling
- Handle incomplete session data gracefully
- Provide partial summaries if full analysis fails
- Suggest session recovery options
- Maintain session integrity