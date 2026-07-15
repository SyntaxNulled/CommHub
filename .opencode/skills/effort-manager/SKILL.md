---
name: effort-manager
description: Controls AI effort level (minimal/low/medium/high/auto) by reading .opencode/effort.json and adjusting thoroughness, verbosity, and depth accordingly. Use when the user mentions effort, thoroughness, or wants to control AI behavior intensity.
---

# Effort Manager

At the start of each task or user request, read `.opencode/effort.json` to determine the current effort level. If the file doesn't exist, default to `medium`.

## Effort Level Behaviors

### minimal
- Responses are 1-3 sentences maximum
- No code comments, no explanations
- Direct answers only — no preamble or postamble
- Skip edge case analysis, skip alternatives
- Use the simplest possible solution
- **Do NOT** run tests, lint, or typecheck unless explicitly asked

### low
- Short paragraphs, get to the point quickly
- Minimal code comments, one line per function at most
- Brief explanation of approach
- Skip edge cases unless critical
- Run tests only if explicitly asked

### medium
- Clear explanation of approach and trade-offs
- Standard code comments
- Consider main alternatives briefly
- Test basic edge cases
- Run tests to verify after changes
- Default level when no effort is specified

### high
- Step-by-step reasoning before writing any code
- Exhaustive edge case analysis
- Full test coverage (unit + edge cases)
- Comprehensive code comments explaining *why* not just *what*
- Consider all alternatives with pros/cons
- Always run tests, lint, typecheck after changes
- Check for security implications
- Verify against all existing patterns in the codebase
- Be extremely thorough — do not cut corners

### auto
- Read the user's message and surrounding conversation context
- Detect task complexity using these signals:
  - **minimal**: Greetings, simple questions, status checks, single value lookups
  - **low**: Simple edits to one file, straightforward config changes, basic questions
  - **medium**: Feature additions, bug fixes with tests, multi-step tasks, 2-5 file changes
  - **high**: Architecture decisions, security code, cross-file refactoring (5+ files), production deployments, complex algorithms, novel features
- Apply the detected level for this specific response, then re-evaluate on the next turn
- When uncertain, prefer one level higher

## The `/effort` Command

Users can change the effort level at any time using the `/effort` command:
- `/effort minimal` — fastest, most concise
- `/effort low` — concise but complete
- `/effort medium` — balanced default
- `/effort high` — maximum thoroughness
- `/effort auto` — automatic detection per task
- `/effort status` — show current setting
