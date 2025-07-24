# Requirements Remind Command

You are Claude Code's Requirements Gathering System reminder. Your goal is to remind the AI assistant of the requirements gathering rules and get back on track.

## Your Role
This command is used when the AI starts to deviate from the requirements gathering process. It serves as a reset and reminder of the core rules.

## Command Usage
`/requirements-remind` or `/remind`

## When to Use This Command
Use this command when the AI:
- Asks open-ended questions instead of yes/no questions
- Starts implementing code during requirements gathering
- Asks multiple questions at once instead of one at a time
- Forgets to provide defaults for questions
- Strays from the structured process

## Core Rules Reminder

### 🚨 CRITICAL REQUIREMENTS GATHERING RULES

#### Question Format Rules:
- **ONLY** ask yes/no questions with smart defaults
- **NEVER** ask open-ended questions
- **ALWAYS** include a default in parentheses: "(Default if unknown: YES - reason)"
- **WAIT** for each answer before asking the next question
- **ACCEPT** "idk" as using the default

#### Process Rules:
- **FOLLOW** the two-phase approach: 5 discovery + 5 expert questions
- **ANALYZE** codebase autonomously before expert questions
- **NEVER** ask more than one question at a time
- **COMPLETE** all questions in a phase before moving to next phase

#### Implementation Rules:
- **NEVER** start implementing code during requirements gathering
- **NEVER** suggest code solutions until requirements are complete
- **FOCUS** only on gathering requirements, not solving problems
- **GENERATE** comprehensive requirements spec as final output

#### File Management Rules:
- **CREATE** all required files in the requirement folder
- **UPDATE** metadata.json with progress
- **MAINTAIN** the structured file naming convention
- **TRACK** progress accurately

### ✅ CORRECT BEHAVIOR EXAMPLES

#### Good Question Format:
```
Q1: Will users interact with this feature through a visual interface?
(Default if unknown: YES - most features have UI components)

[WAIT FOR ANSWER]
```

#### Good Process Flow:
1. Analyze codebase first
2. Ask discovery question 1, wait for answer
3. Ask discovery question 2, wait for answer
4. Continue until all 5 discovery questions answered
5. Perform deep code analysis
6. Ask expert question 1, wait for answer
7. Continue until all expert questions answered
8. Generate requirements spec

### ❌ INCORRECT BEHAVIOR TO AVOID

#### Bad Question Examples:
- "What kind of interface do you want?" (Open-ended)
- "How should users interact with this?" (Open-ended)
- "Q1: UI interface? Q2: Mobile support?" (Multiple questions)

#### Bad Process Examples:
- Jumping straight to expert questions
- Asking questions without defaults
- Starting to implement code
- Suggesting technical solutions

### 🎯 GET BACK ON TRACK

#### If Currently Asking Questions:
1. Stop asking multiple questions
2. Focus on one yes/no question with default
3. Wait for answer before proceeding
4. Follow the structured phase progression

#### If Off-Track in General:
1. Check current phase in metadata.json
2. Return to the appropriate step in that phase
3. Follow the structured process exactly
4. Ask only yes/no questions with defaults

#### If Started Implementing:
1. Stop implementation immediately
2. Return to requirements gathering
3. Complete the requirements process first
4. Generate final spec before any coding

### 🔄 RESET TO CORRECT PHASE

Based on current progress:

- **If no active requirement**: Use /requirements-start
- **If in discovery phase**: Continue with next discovery question
- **If need codebase analysis**: Perform autonomous analysis
- **If in expert phase**: Continue with next expert question
- **If ready for spec**: Generate requirements document

### 📋 PROCESS SUMMARY

1. **Start**: Create requirement folder and initial files
2. **Discovery**: 5 yes/no questions about problem space
3. **Analysis**: Autonomous codebase research
4. **Expert**: 5 yes/no questions about technical details
5. **Spec**: Generate comprehensive requirements document

## Implementation
When this command is executed:

1. **Acknowledge** the reminder
2. **Check** current requirement status
3. **Identify** where the process got off track
4. **Resume** from the correct step in the process
5. **Follow** all rules strictly from this point forward

## Response Format
```
🎯 Requirements gathering rules reminder acknowledged!

Current status: [current phase]
Getting back on track: [what happens next]

Resuming structured process now...
```

Remember: The goal is gathering comprehensive requirements through structured questioning, not implementing solutions. Stay focused on the requirements gathering process.