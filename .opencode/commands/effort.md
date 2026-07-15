---
description: Set AI effort level — minimal, low, medium, high, or auto. Controls how thorough and comprehensive the AI is. Auto mode detects task complexity automatically.
---

# /effort — AI Effort Control

The user wants effort level: **$ARGUMENTS**

## Effort level definitions

| Level | Model (on restart) | Behavior |
|-------|-------------------|----------|
| minimal | `gpt-4o-mini` | Ultra-concise. 1-3 sentence answers. No explanations. No code comments. Fastest possible response. |
| low | `gpt-4o` | Concise but complete. Short paragraphs. Minimal code comments. Direct answers. |
| medium | `claude-sonnet-4-6` | Balanced. Clear explanations. Standard code comments. Considers alternatives briefly. |
| high | `claude-opus-4-5` (thinking) | Maximum thoroughness. Step-by-step reasoning. Exhaustive edge case analysis. Full test coverage. Comprehensive code comments. |
| auto | dynamic | Analyze the user's message and select the appropriate level. |

## Instructions

1. If `$ARGUMENTS` is empty or invalid, show the user the available options and current effort level.
2. Read the current effort setting from `.opencode/effort.json` (create if missing with `{"level":"medium"}`).
3. If `$ARGUMENTS` is `auto`, analyze the current conversation context — consider task complexity, number of files involved, whether tests are needed, whether this is a bug fix vs feature vs question — and pick the appropriate level.
4. Write the chosen effort level to `.opencode/effort.json`:
   ```json
   {"level": "high", "auto_override": false}
   ```
5. Update `.opencode/opencode.json` to set the `model` and `small_model` fields that match the effort level's recommended model (for next restart). Preserve all existing fields.
6. Tell the user:
   - What effort level was set
   - What model will be used on next restart (if different from current)
   - That they need to **quit and restart opencode** for the model change to take effect
   - The current session will follow the new effort behavior immediately

For `auto` mode, the detection logic is:
- **minimal**: Simple questions, greetings, file reads, status checks
- **low**: Straightforward edits, single-file changes, config tweaks
- **medium**: Multi-step tasks, feature additions, bug fixes with testing
- **high**: Complex architecture decisions, security-sensitive code, cross-file refactoring, production deployments

If `$ARGUMENTS` is `status`, just read and display the current effort level without changing anything.
