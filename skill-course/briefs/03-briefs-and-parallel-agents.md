# Module 3: Briefs & Parallel Agents (the pipeline)

### Teaching Arc
- **Metaphor:** A **film shoot with a shot list.** The director scouts once, then hands each camera crew a single shot brief — pre-loaded with everything for that scene — so crews shoot in parallel without re-reading the whole screenplay. (No restaurant.)
- **Opening hook:** "Ten modules got written at the same time by separate AI agents that never read the codebase. How? A work order called a brief."
- **Key insight:** Simple codebases → one agent writes modules sequentially. Complex ones → the main agent writes a **brief per module** (with code snippets pre-extracted), then dispatches **parallel writing agents** that only see their brief + a few reference sections. This is a token-economy move: agents never re-read the codebase.
- **"Why should I care?":** This is how to scale AI work without blowing the context budget — pre-digest the inputs into self-contained work orders. You can demand this pattern from any AI system: "give each worker only what it needs."

### Code Snippets (pre-extracted)

File: module-brief-template.md — what a brief contains
```
## Module N: [Title]
### Teaching Arc      — metaphor, hook, key insight, "why care?"
### Code Snippets     — pre-extracted from the codebase (verbatim, with paths)
### Interactive Elements — checklist of what to build
### Reference Files   — only the sections this agent needs
### Connections       — prev/next module, tone notes
```

File: SKILL.md — the parallel dispatch rule
```
Dispatch modules to subagents in batches of up to 3. Each agent receives:
 - Its module brief
 - content-philosophy.md and gotchas.md
 - Only the sections of interactive-elements.md / design-system.md it needs
What agents do NOT receive: the full codebase, SKILL.md, other briefs.
```

### Interactive Elements
- [x] **Group chat animation** — the hero. Actors: Main Agent, Brief, Writer-1, Writer-2, Writer-3. Flow: Main Agent "here are your 3 briefs"; Writers (in parallel) "on it"; Writer-1 "module 1 written"; Writer-2 "module 2 written"; Main Agent "now I assemble + consistency-check."
- [x] **Code↔English translation** — the brief template: explain why "pre-extracted code snippets" is the critical token-saving step (the agent never opens the real repo).
- [x] **Numbered step cards** — the pipeline: analyze → design curriculum → write briefs → dispatch parallel writers → assemble → review.
- [x] **Quiz** — 3 Qs, architecture/decision. e.g. "Why NOT give each writing agent the whole codebase?" (token cost + drift) "When would the skill skip briefs and write sequentially?" (simple codebase).
- [x] **Callout** — "aha!": separating *planning* (briefs) from *production* (writing) is the same split as a blueprint vs the construction crew.

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Numbered Step Cards", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Directory & build.sh."
- **Next module:** "Navigation & Reveal" — the first deep-dive into a main.js engine (how the page comes alive as you scroll).
- **Tone/style notes:** TEAL accent (global). Course-wide names. Odd module → alternating background. Group chat container needs a unique `id` and unique typing-avatar id. Tooltip: subagent, parallel, context budget, brief/work order, dispatch.
