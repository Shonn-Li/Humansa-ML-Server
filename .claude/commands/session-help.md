---
description: Display help information for session management commands
---

# Session Management Help

Comprehensive guide to Claude Code session management commands for YouWoAI project.

## Overview
Session management helps track development progress, maintain context across coding sessions, and document implementation decisions for future reference.

## Available Commands

### `/session-start [name]`
**Purpose**: Start a new development session
**Usage**: 
- `/session-start authentication-refactor`
- `/session-start` (creates timestamp-only session)

**What it does**:
- Creates new session file with timestamp
- Sets up session structure with goals
- Tracks current git context
- Marks session as active

### `/session-update [notes]`
**Purpose**: Add progress updates to current session
**Usage**:
- `/session-update Fixed OAuth integration bug`
- `/session-update` (auto-generates update from recent activity)

**What it does**:
- Captures git status and changes
- Documents progress with timestamp
- Tracks file modifications
- Records issues and solutions

### `/session-current`
**Purpose**: View current session status
**Usage**: `/session-current`

**What it does**:
- Shows session duration and progress
- Displays recent updates
- Shows git context
- Provides quick action suggestions

### `/session-end`
**Purpose**: End session with comprehensive summary
**Usage**: `/session-end`

**What it does**:
- Generates complete session summary
- Analyzes git changes and statistics
- Documents accomplishments and issues
- Provides next session preparation notes

### `/session-list`
**Purpose**: List all sessions with summaries
**Usage**: `/session-list`

**What it does**:
- Shows all sessions chronologically
- Displays session statistics
- Highlights active session
- Provides session overview metrics

## File Structure
```
.claude/
├── commands/           # Custom slash commands
│   ├── session-start.md
│   ├── session-update.md
│   ├── session-current.md
│   ├── session-end.md
│   ├── session-list.md
│   └── session-help.md
└── sessions/           # Session storage
    ├── .current-session    # Active session tracker
    └── *.md               # Individual session files
```

## Session File Format
```markdown
# Development Session - YYYY-MM-DD-HHMM - [name]

## Session Info
- **Started**: [timestamp]
- **Status**: Active/Completed

## Goals
- [ ] Goal 1
- [x] Goal 2 (completed)

## Progress Log
### [timestamp] - Progress Update
[Detailed progress notes]

## Session Summary
[Generated at session end]
```

## Best Practices

### Starting Sessions
- Use descriptive names for complex features
- Define clear, achievable goals
- Start sessions for significant work chunks

### During Development
- Update regularly when completing tasks
- Document unexpected issues and solutions
- Note important implementation decisions

### Ending Sessions
- Always end sessions properly for complete summaries
- Review generated summary for accuracy
- Use insights for future session planning

## Integration with YouWoAI Project

### Project Context
Sessions automatically capture:
- Current git branch and commits
- Modified files in Mobile/Server/ML components
- Database migration status
- Environment configuration changes

### YouWoAI-Specific Features
- Multi-platform development tracking
- API endpoint implementation progress
- Database schema change documentation
- Deployment and testing notes

## Workflow Examples

### Feature Development
```bash
/session-start payment-integration
# Work on Stripe integration
/session-update Added Stripe webhook handling
# Fix issues
/session-update Resolved webhook verification bug
/session-end
```

### Bug Fixing
```bash
/session-start fix-ios-background-audio
# Investigate and fix
/session-update Found issue in audio session management
/session-update Implemented proper background handling
/session-end
```

### Code Review Session
```bash
/session-start code-review-auth-module
# Review authentication code
/session-update Reviewed OAuth implementation
/session-update Identified security improvements needed
/session-end
```

## Tips for Effective Sessions
1. **Be Specific**: Use descriptive session names
2. **Update Frequently**: Don't wait too long between updates
3. **Document Issues**: Always note problems and solutions
4. **Set Clear Goals**: Define what you want to accomplish
5. **End Properly**: Complete sessions for full documentation

## Troubleshooting

### No Active Session
```bash
# Error: No active session found
# Solution: Start a new session
/session-start
```

### Corrupted Session
```bash
# If session tracking is broken
rm sessions/.current-session
/session-start recovery-session
```

### Missing Commands
```bash
# Ensure commands are in the right location
ls .claude/commands/session-*.md
```

## Advanced Usage

### Session Analysis
Sessions provide valuable insights:
- Development velocity tracking
- Problem pattern identification
- Code quality improvement areas
- Time estimation for similar tasks

### Team Collaboration
- Share session summaries in standups
- Use session notes for code review context
- Reference sessions in commit messages
- Create session templates for common tasks

## Command Reference Quick Guide
```
/session-start [name]    # Begin new session
/session-update [notes]  # Add progress update  
/session-current         # View current status
/session-end            # Complete session
/session-list           # View all sessions
/session-help           # Show this help
```