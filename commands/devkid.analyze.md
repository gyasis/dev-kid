---
name: devkid.analyze
description: Optional agent pass that reads task wording, adds the file paths the orchestrator needs (backticked), and re-runs. The dev-kid library stays deterministic and agent-free — this is help, not a dependency.
---

# Dev-Kid Analyze — agent-assisted task formatting

## The layering (read this first)

dev-kid's orchestrator is **deterministic and agent-free**: it computes parallel
vs sequential waves purely from the **file paths named in each task**. Two tasks
that touch the same file are forced into different waves; everything else can run
in parallel. No LLM, no network — it just works when tasks name their files.

The **only** thing the engine can't do alone is read a vague, prose task
("refactor the login flow") and *know* which file it touches. There it prints a
loud `⚠️ names no detectable file` warning and moves on (treating it as
unlocked — possibly unsafe).

**This skill is the optional second pass.** YOU (the agent driving dev-kid) read
those flagged tasks, figure out which files they actually touch, and annotate
them so the engine's existing wave logic protects them. The library never calls
you and never depends on you — run dev-kid without this and it still works.

```
dev-kid library  (deterministic, no agent)   ← always works on its own
        ▲ optional
   this skill: agent reads wording → adds `paths` → re-runs
```

## When to use

- After `dev-kid orchestrate` prints `⚠️ names no detectable file` warnings, or
- Before orchestrating a prose / SpecKit-generated task list that doesn't name files.

## Hard rules (do not break these)

1. **Never edit a SpecKit-symlinked source.** Check `readlink -f tasks.md`. If it
   points into `.specify/` (or anywhere you don't own), write your annotated
   version to a dev-kid-owned **`dk-tasks.md`** and orchestrate THAT. Only edit
   `tasks.md` in place if it is a plain, user-owned file — and confirm first.
2. **Only add paths you VERIFIED** by reading the repo. Wrap them in backticks.
   Do not guess — a wrong lock is worse than a flagged gap.
3. **Format, don't rewrite intent.** Keep each task's id and meaning; just make
   the files explicit. Add `after T0xx` / `## Wave N` only when the ordering is real.

## Steps

1. **See what the engine sees:**
   ```bash
   dev-kid orchestrate --verify-only
   ```
   Note every `⚠️ names no detectable file` task and the current wave grouping.
2. **Check ownership of the source:**
   ```bash
   readlink -f tasks.md        # in .specify/ or not yours → write dk-tasks.md instead
   ```
3. **For each flagged task:** read the relevant code (grep/read), decide which
   file(s) it modifies, and make them explicit in backticks, e.g.:
   ```
   - [ ] T003: improve login error handling affecting `src/auth.py`
   ```
4. **Write the annotated list** to `dk-tasks.md` (or in place only if user-owned).
5. **Re-run and confirm the gap is gone:**
   ```bash
   dev-kid orchestrate --tasks-file dk-tasks.md --verify-only   # expect: no ⚠️, waves look right
   dev-kid orchestrate --tasks-file dk-tasks.md                 # writes execution_plan.json
   ```
6. **Execute:** `dev-kid execute`.

## Why this is safe and decoupled

- The dev-kid **library** is unchanged — deterministic, no LLM, works without this skill.
- This skill is **agent-side**; dev-kid never imports or requires it.
- The **SpecKit source is never mutated** — you write a dev-kid-owned `dk-tasks.md`.
- Re-running is **completion-aware**: `[x]` tasks are skipped, so you can format,
  fix, and re-orchestrate mid-flight without redoing finished work.
