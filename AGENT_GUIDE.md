# Dev-Kid — Agent Usage Guide

**Audience:** AI coding agents (Claude Code, Cursor, similar) deciding when and how to invoke dev-kid in a user's project.

This guide answers: *"I'm working on a user's task — should I reach for dev-kid? Which mode? What's the command sequence?"*

For implementation deep-dives see `CLAUDE.md`; for human quickstart see `QUICKSTART.md`.

---

## 1. When to invoke dev-kid (the triggers)

Reach for dev-kid when **any** of the following are true:

| Trigger | Why dev-kid helps |
|---|---|
| User describes work as **≥3 tasks** that touch multiple files | Wave orchestration parallelizes safely (file-lock detection); checkpoints between waves prevent silent regressions |
| User wants **agent-driven test+fix loops** after each task | Sentinel runs Tier 1 (Ollama, free) → Tier 2 (Claude Sonnet, capped budget) → Tier 3 (Claude Code handoff) automatically |
| User says **"set up X with Y, then Z"** — multi-step infra/setup | Tasks become checkpointed, recoverable across context compression |
| The work will likely **span multiple sessions** or hit `/compact` | Memory Bank + `.claude/session_snapshots/` survive compression; `dev-kid recall` resumes cleanly |
| User wants **cost tracking** on AI-generated work | Cumulative sentinel budget tracker (`dev-kid budget-status`) caps spend |

**Do NOT** reach for dev-kid for:
- Single-shot edits ("fix this typo")
- Read-only investigations ("explain how X works")
- Quick bug fixes (<3 steps, no test loop needed)
- Tasks where the user explicitly wants you to just-do-it without ceremony

---

## 2. Pick the mode — SpecKit vs Lightweight

Dev-kid has **two orchestration modes**. The choice depends on whether the user is on a SpecKit-style numbered feature workflow.

```
                    ┌────────────────────────────────────────┐
                    │ Does the project use SpecKit?           │
                    │ (i.e., `.specify/specs/00X-name/`       │
                    │  + numbered branch like 005-feature)    │
                    └─────────┬──────────────────────┬───────┘
                              │                      │
                            Yes                      No
                              │                      │
                              ▼                      ▼
                    ┌──────────────────┐   ┌────────────────────┐
                    │ SpecKit mode     │   │ Lightweight mode   │
                    │ (default)        │   │ (.dk/ marker)      │
                    └──────────────────┘   └────────────────────┘
```

### SpecKit mode (default)
**When:** big features with formal spec → plan → tasks ceremony. User is on a branch like `005-sio-experiment`. Tasks live at `.specify/specs/005-sio-experiment/tasks.md`.

**Activation:** automatic — dev-kid finds tasks via the resolution chain (`.specify/feature.json` → `.specify/specs/<branch>/tasks.md`).

**Use it when:** the user references `/speckit.specify` / `/speckit.plan` / `/speckit.tasks`, OR the repo already has `.specify/` structure, OR they want the full PRD-doc-plan-doc-tasks-doc paper trail.

### Lightweight mode
**When:** one-off work, small experiments, project that doesn't follow SpecKit. Tasks live at `./.dk/tasks.md`.

**Activation:**
```bash
dev-kid init --lightweight    # scaffolds .dk/tasks.md placeholder
```

**Use it when:** the user wants "just tasks + sentinel + checkpoints", OR the project doesn't have `.specify/` and you don't want to impose ceremony, OR the user explicitly says "lightweight" / "no speckit" / "no numbered branch."

### Coexistence
If a repo has **both** `.dk/tasks.md` AND `.specify/specs/<branch>/tasks.md`, `.dk/` wins (priority 1 > priority 3). To use SpecKit on a project that previously enabled lightweight, delete `.dk/`. They're not mutually-exclusive at install time, but only one set of tasks resolves per `dev-kid orchestrate` invocation.

---

## 3. Canonical workflows (5-line sequences)

### Lightweight mode — full flow
```bash
dev-kid init --lightweight              # creates .dk/tasks.md placeholder
# edit .dk/tasks.md — list tasks in format: `- [ ] T001: description affecting `path/to/file.py``
dev-kid spec-resolve                    # sanity-check: confirms .dk/ wins, shows priority
dev-kid orchestrate "phase-1"           # builds execution_plan.json + symlinks tasks.md → .dk/tasks.md
dev-kid execute                         # preflight gate → waves → sentinel → checkpoints
```

### SpecKit mode — full flow
```bash
# User has already done /speckit.specify and /speckit.tasks; you're on branch 005-feature
dev-kid init-check                      # validates the .specify/ structure
dev-kid orchestrate "phase-1"           # picks up .specify/specs/005-feature/tasks.md
dev-kid execute                         # same execute as lightweight
```

### Resume after compression / new session
```bash
dev-kid recall                          # restores last snapshot
dev-kid status                          # shows current wave + pending tasks
# proceed with whatever wave is in flight
```

### After a task completes (mark + checkpoint)
- Mark the task as `[x]` in `tasks.md` (the symlink — works for both modes)
- The wave executor halts before the next wave until all current-wave tasks are `[x]`
- Sentinel runs automatically after each task if enabled; budget tracker accumulates spend

---

## 4. Anti-patterns (what NOT to do)

| Anti-pattern | Why it breaks | Do instead |
|---|---|---|
| Running `dev-kid orchestrate` without first checking the resolution chain | May pick a stale `specs/*/tasks.md` from a prior feature | `dev-kid spec-resolve` first; verify the source it would pick |
| Creating `.dk/tasks.md` manually inside a SpecKit project to "test lightweight" | Now `.dk/` wins over the user's real SpecKit work — silent confusion | Use `dev-kid init --lightweight` only in fresh / non-SpecKit projects |
| Marking tasks complete in `tasks.md` (the symlink) AND in the target | Symlink IS the target — you'll just duplicate edits | Edit the symlink path; the target updates atomically |
| Running `dev-kid execute --no-preflight` to "save time" | Preflight catches missing Ollama / API key BEFORE waves spend budget | Run preflight; fix the missing tier; then execute |
| Calling `dev-kid orchestrate` after the user makes uncommitted edits to `.dk/tasks.md` | The plan reflects the saved file — what's on disk wins | Save file → orchestrate → execute |
| Adding tasks to `tasks.md` mid-wave | Wave executor read the plan at orchestrate-time; new tasks won't run this wave | Finish current wave → re-orchestrate → new wave picks them up |

---

## 5. Quick troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `Could not resolve tasks.md` (exit 2) | No `.dk/tasks.md` AND no `.specify/specs/<branch>/`, OR branch name doesn't match any spec dir | Run `dev-kid init --lightweight` OR check branch name OR `dev-kid spec-resolve` to see what was tried |
| `dev-kid init --lightweight` hangs in CI | `init.sh` had interactive prompts — fixed in commit `19145e2`, falls back to "N" when stdin is not a TTY | Update dev-kid to ≥ this commit; or pipe `</dev/null` |
| Wave halts on checkpoint, says tasks incomplete | Some `[ ]` tasks were not marked `[x]` before wave end | Mark them complete in `tasks.md` (the symlink), then `dev-kid execute` resumes |
| `Tier 1 (Ollama) not reachable` warning | Ollama not running OR `dev-kid.yml: ollama_url` points wrong | Start Ollama (`ollama serve`) OR edit `dev-kid.yml` URL |
| `ANTHROPIC_API_KEY not set` warning | `.env` not sourced OR key not set | Source `~/dev/.env` OR set `export ANTHROPIC_API_KEY=...` |
| Budget tracker won't reset | Cumulative state in `.claude/sentinel/.budget-state.json` | `dev-kid execute --fresh-budget` resets to $0 |

---

## 6. The agent's mental model

Think of dev-kid as a **safety-rails orchestrator** for AI-driven work:

- **Tasks.md** = the work list, written by you or the user
- **Orchestrate** = compute the safe parallel-execution shape (wave plan)
- **Execute** = run the waves, with sentinel testing each task and checkpoints between waves
- **Recall** = pick up where you left off after compression / new session

It is NOT a replacement for thinking — you still author the tasks, you still write the code. It IS a replacement for ad-hoc loops where you'd otherwise be tracking which file you've edited, whether tests passed, and what to do if they didn't.

When in doubt: ask the user *"want to run this through dev-kid?"* — short answer pivots the entire session structure, so don't assume.

---

## 7. Reference

| For | See |
|---|---|
| Install / first-time human setup | `QUICKSTART.md` |
| Architecture deep-dive (Bash / Python / Rust split) | `INTEGRATION_GUIDE.md` |
| Hook lifecycle (PreCompact, TaskCompleted, etc.) | `HOOKS_REFERENCE.md` |
| Implementation notes (for editing dev-kid itself) | `CLAUDE.md` |
| Subagent / task-level agent design | `TASK_LEVEL_AGENTS.md` |
| Version history | `CHANGELOG.md` |
