# Module 1: What Dev-Kid Does

### Teaching Arc
- **Metaphor:** A **general contractor** who takes a homeowner's messy renovation wish-list and turns it into a scheduled crew plan — who works in parallel, who waits on whom, and a building inspector who signs off each phase before the next starts. (Do NOT use restaurant/kitchen.)
- **Opening hook:** "You wrote a plain checklist in `tasks.md`, typed `dev-kid orchestrate`, then `dev-kid execute` — and somehow your AI coding agent built the whole thing in coordinated batches without stepping on its own toes. Here's the machine behind that."
- **Key insight:** Dev-Kid turns a flat human to-do list into a *safe, parallel, self-checking* build pipeline that an AI coding agent (Claude Code) executes — with checkpoints so nothing silently breaks.
- **"Why should I care?":** This is the 30,000-ft map. Once you know the four stations data passes through, you can tell the AI *exactly* where a problem lives ("the plan is wrong" vs "execution stalled" vs "validation failed").

### Code Snippets (pre-extracted)

The whole system is one pipeline. Show this as the hero data-flow, not code:
```
tasks.md  →  orchestrator.py  →  execution_plan.json  →  wave_executor.py
(your list)   (the planner)       (the schedule)          (the foreman)
```

File: a typical `tasks.md` line (the format the whole system parses)
```
- [ ] T001: Implement the auth module affecting `src/auth.py`
- [ ] T002: Add login UI affecting `src/ui/login.tsx`
```

File: cli/dev-kid (the bash CLI routes a command to a Python module)
```bash
python3 "$DEV_KID_ROOT/cli/orchestrator.py" "${py_args[@]}"
...
python3 "$DEV_KID_ROOT/cli/wave_executor.py" "${remaining_args[@]}"
```

File: execution_plan.json shape (what the planner produces)
```json
{ "execution_plan": { "phase_id": "...", "waves": [
  { "wave_id": 1, "strategy": "PARALLEL_SWARM", "tasks": [...], "checkpoint_after": {...} }
] } }
```

### Interactive Elements
- [x] **Data flow animation** — actors: `tasks.md`, Orchestrator, `execution_plan.json`, Wave Executor. Steps: the checklist travels right, gets reshaped into a wave schedule, then the foreman picks it up and dispatches work. This is the hero visual.
- [x] **Code↔English translation** — the `tasks.md` line: explain `- [ ]` (unchecked box = not done), `T001` (task id), and why the backtick path `` `src/auth.py` `` matters (it's a machine-readable signal, covered next module).
- [x] **Quiz** — 3 Qs, scenario style. e.g. "The AI built everything but two tasks that edit the same file ran at the same time and clobbered each other — which station failed to do its job?" (answer: the Orchestrator's plan).
- [x] **Callout** — "aha!": dev-kid doesn't write code — it *choreographs* the AI that writes code.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Scenario Quiz", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all (always)
- `references/gotchas.md` → all (always)
- `references/design-system.md` → only for the data-flow animation tokens

### Connections
- **Previous module:** none (this is the opener).
- **Next module:** "Meet the Cast" — names and personalities of every component.
- **Tone/style notes:** Accent = vermillion. Actor names used course-wide: **The Orchestrator** (planner), **The Wave Executor** (foreman), **The Sentinel** (inspector), **The Watchdog** (night guard), **Ralph Loop / micro-agent** (the tireless apprentice), **Memory Bank** (the archive), **Hooks** (reflexes). Tooltip every term: CLI, Python module, JSON, parse.
