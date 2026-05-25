# Module 1: What This Skill Does (+ the recursion)

### Teaching Arc
- **Metaphor:** A **museum exhibit designer** who takes a crate of raw artifacts (a codebase) and turns it into a guided, interactive gallery with placards, dioramas, and "try-it" stations — instead of dumping the crate on a table. (No restaurant.)
- **Opening hook:** "You just walked through an interactive course this skill built. Now we open the workshop — and here's the twist: THIS page was built by the exact same machine."
- **Key insight:** codebase-to-course reads a project, designs a curriculum, and emits a **self-contained, browsable course directory** — animated, quizzed, plain-English — that runs in a browser with zero setup.
- **"Why should I care?":** Understanding the factory lets you point it at any repo (yours or a GitHub find) and know what knobs exist — depth, module count, which interactive elements show up.

### Code Snippets (pre-extracted)

File: SKILL.md — the four-phase process (paraphrase as a flow, quote the phase names)
```
Phase 1: Codebase Analysis      → read files, trace flows, find the "cast"
Phase 2: Curriculum Design      → 4-10 modules, simple vs complex build path
Phase 2.5: Module Briefs        → one brief per module (complex path only)
Phase 3: Build the Course       → write module HTML (sequential or parallel)
Phase 4: Assemble & Open        → build.sh → index.html
```

File: the output directory (what the skill produces)
```
course-name/
  styles.css       ← copied verbatim (never regenerated)
  main.js          ← copied verbatim (the interactivity engine)
  _base.html       ← shell: title, accent, nav dots
  modules/01-*.html … ← the only files written fresh
  index.html       ← assembled by build.sh
```

### Interactive Elements
- [x] **Data flow animation** — the hero. Actors: Codebase → Analysis → Curriculum → Briefs → Module Writers → build.sh → index.html. Walk a repo turning into a course.
- [x] **Code↔English translation** — the output directory tree: explain "self-contained" (no server, opens as a file), and why CSS/JS are copied not generated.
- [x] **Quiz** — 3 Qs, application. e.g. "You point it at a GitHub repo — what's the FIRST thing it does before writing any HTML?" (analysis) "Why does it output a folder instead of one big HTML file?" (teases Module 2).
- [x] **Callout** — "aha!": the course you take is itself a worked example of the thing it teaches — recursion you can click through.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** none (opener).
- **Next module:** "The Directory & build.sh" — how that output folder is structured and assembled.
- **Tone/style notes:** Accent = TEAL (set globally — don't hardcode). Course-wide character names: **The Skill** (the factory), **The Brief** (the work order), **The Writing Agents** (the parallel crew), **build.sh** (the assembler), and the JS pieces are **Engines** that auto-power-on. Lean into the recursive/meta angle throughout the course. Tooltip: codebase, self-contained, directory, boilerplate, render.
