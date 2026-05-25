# Tasks

<!-- ───────────────────────────────────────────────────────────────────────
  HOW DEV-KID READS THIS FILE  (delete this comment once you're comfortable)

  • One task per line:        - [ ] T001: <what to do>
  • WRAP EVERY FILE PATH IN BACKTICKS. This is the signal the orchestrator
    uses to stop two tasks that touch the SAME file from running in the same
    parallel wave (which would race-edit the file). Example:
        - [ ] T002: add the login handler affecting `src/auth.py`
  • Backticks are REQUIRED (not optional) for:
        – extensionless files:        `Makefile`, `Dockerfile`, `LICENSE`
        – long/uncommon extensions:   `app.svelte`, `schema.graphql`, `build.gradle`
        – any path you want GUARANTEED detected
  • Declare order when it matters:  "after T001"  /  "depends on T003".
  • Hard phases:  put `## Wave 1`, `## Wave 2` … headers above groups of tasks —
    everything under Wave N waits for everything in Waves 1..N-1.

  BEFORE you run `dev-kid orchestrate`, run:
        dev-kid analyze        (alias: dev-kid lint-tasks)
  It shows, per task, which files were detected and which tasks can run in
  parallel — and FLAGS any action task that names no detectable file (those
  can't be protected from collisions). Fix the flags, then orchestrate.
─────────────────────────────────────────────────────────────────────────── -->

## Wave 1

- [ ] T001: Scaffold the project layout and write the `README.md`
- [ ] T002: Define the data models in `src/models.py`
- [ ] T004: Add a build target to the `Makefile`

## Wave 2

- [ ] T003: Implement the API layer in `src/api.py` (depends on T002)
- [ ] T005: Write API tests in `tests/test_api.py` (depends on T003)
