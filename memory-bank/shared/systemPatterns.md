# System Patterns

**Purpose**: Architecture patterns and design decisions

## Ralph Principles (LLM Smart Zone Optimization)

**Core Insight**: LLMs perform best in short, fresh bursts, not long conversations.

### The Two-Zone Problem
- **Smart Zone**: First 30-40% of context (focused, precise, good decisions)
- **Dumb Zone**: Beyond 40% of context (confused, error-prone, degraded quality)

### How This Project Implements Ralph
1. **Frequent Git Commits**: Externalize state to git, not conversation memory
2. **Wave-Based Execution**: Each wave = one iteration (discrete work unit)
3. **Memory Bank as PRD**: Requirements persist outside context window
4. **Session Snapshots**: Resume points without context bloat
5. **GitHub Issues as Tasks**: External tracking enables crash recovery

### Agent Guidelines (CRITICAL)
✅ **DO**:
- Commit to git after EVERY logical change (not just wave completion)
- Read git history + Memory Bank instead of scrolling conversation
- If context feels bloated (>80K tokens), finalize and recall
- Complete one wave, then checkpoint
- Trust the codebase as memory, not conversation history

❌ **DON'T**:
- Try to remember everything in conversation
- Do multiple waves in one session
- Continue when context approaches 100K tokens
- Skip commits to "batch" changes

### Context Budget Targets
- **Optimal**: <60K tokens (30% of 200K window)
- **Warning**: 60-80K tokens (30-40%)
- **Critical**: >80K tokens (>40% - finalize immediately)

## Architecture Patterns
- [Pattern 1]: [When to use]

## Design Decisions
- [Decision 1]: [Rationale]

## Known Gotchas
- [Gotcha 1]: [How to avoid]
