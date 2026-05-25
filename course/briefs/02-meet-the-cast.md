# Module 2: Meet the Cast

### Teaching Arc
- **Metaphor:** A **theater company** — each member has one job: the playwright (Orchestrator) writes the running order, the stage manager (Wave Executor) calls cues, the critic (Sentinel) reviews each scene, the night watchman (Rust Watchdog) makes sure no actor is left locked in the building. (No restaurant.)
- **Opening hook:** "Before we trace anything, meet the people in the building. When something breaks, you need to know *who* to point the AI at."
- **Key insight:** Dev-Kid is a handful of small, single-responsibility parts in three languages (Bash CLI, Python brains, one Rust daemon) — plus an external apprentice it hires, micro-agent.
- **"Why should I care?":** Naming the actors gives you the vocabulary to steer the AI precisely — "the watchdog is leaking processes" lands better than "something's stuck."

### Code Snippets (pre-extracted)

File: directory layout (from the repo)
```
dev-kid/
├── cli/dev-kid            ← Bash CLI: routes commands
├── cli/orchestrator.py    ← turns tasks.md into waves
├── cli/wave_executor.py   ← runs waves, enforces checkpoints
├── cli/sentinel/          ← the per-task validator (10+ modules)
├── rust-watchdog/         ← compiled process/container monitor (~1.8MB)
├── skills/*.sh            ← bash workflow automations
└── memory-bank/           ← persistent project memory
```

File: micro-agent `package.json` bin map (the apprentice it hires — TWO faces)
```json
{ "bin": {
  "micro-agent": "./dist/cli.mjs",       // single-file generator
  "ma":          "./dist/cli.mjs",        // alias
  "ma-loop":     "./dist/ralph-loop.mjs"  // the autonomous "Ralph Loop"
}}
```

### Interactive Elements
- [x] **Architecture diagram** (interactive, clickable actors) — the hero. Boxes: CLI, Orchestrator, Wave Executor, Sentinel, Watchdog, micro-agent (with its TWO faces ma / ma-loop), Memory Bank, Hooks. Clicking each shows a one-line job description.
- [x] **Icon-label rows** — one row per actor: icon + name + "its one job in 6 words."
- [x] **Code↔English translation** — the bin map: explain that one tool exposes two different commands, and foreshadow that picking the wrong one is the bug in Module 9.
- [x] **Quiz** — 3 Qs, "which actor?" scenarios. e.g. "Tasks are running but two ran in parallel that shouldn't have — whose fault?" / "A finished task's process never got cleaned up — who's supposed to catch that?"

### Reference Files to Read
- `references/interactive-elements.md` → "Interactive Architecture Diagram", "Icon-Label Rows", "Visual File Tree", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "What Dev-Kid Does" — the 4-station pipeline.
- **Next module:** "Building Waves" — a deep look at the Orchestrator's job.
- **Tone/style notes:** Vermillion. Use the course-wide actor names. The micro-agent "two faces" (ma vs ma-loop) is a planted seed — mention it intriguingly, don't resolve it yet. Tooltip: Bash, Rust, daemon, compiled binary, container.
