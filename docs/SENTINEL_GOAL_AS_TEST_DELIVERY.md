# Sentinel → ma-loop delivery (Goal-as-Test)

**Status:** implemented 2026-05-29 (PRDs `devkid_sentinel_goal_as_test`,
`maloop_unification_single_entrypoint`). Origin: gentle-eye dogfood.

## The problem this fixed

The Integration Sentinel invoked ma-loop with a vague objective and `-t cargo
check`, and **without a concrete target file** (the objective had no path →
ma-loop ran with `target="."`). Result: ma-loop authored throwaway files that
"passed" by compiling — validating *nothing*. Two structural fixes:

## 1. Deliver the target FILE (never `"."`) — `cli/sentinel/`

- `runner.py` now extracts the task's source files from `file_locks` and passes
  them to the tier runner as `target_files`.
- `tier_runner.py:run_tiered(..., target_files=, criterion=)` uses
  `target_files[0]` as the ma-loop `<target>`. **If no concrete file can be
  resolved, it HARD-FAILS** (`TierResult(final_status="FAIL")`) instead of
  running with `target="."` — an absent target is a blocking failure, because an
  unconstrained agent authors junk across the tree.

## 2. Deliver the CRITERION (the measurable goal) — `cli/sentinel/runner.py`

- `_criterion_from_tasksmd(task, project_root)` reads the resolved `tasks.md`
  (via the single resolver, `cli/resolver.py`) and extracts the task's
  `> DONE:` continuation lines for the covered id(s).
- It's passed to ma-loop as `--criterion`, so ma-loop generates a **strong
  behavioral test** grounded in the real goal (not a trivial/compile-only one).
  See `micro-agent/docs/GOAL_AS_TEST.md` for the ma-loop side.

## Execution-path note (important)

dev-kid does its **own tier escalation in Python** (`tier_runner.run_tiered`
iterates `ralph-tiers.json`), calling `ma-loop run <target> -o … -t … -f cargo
-c <ralph.config.yaml>` **once per tier**. Because it passes `-c`/`--config`
(a ralph.config.yaml), each ma-loop call takes micro-agent's **main flow**
(`runRalphLoop`, simple mode) — **not** `runTierLoop`. (The audit initially
mis-stated this.) The Goal-as-Test helper runs on **both** micro-agent paths, so
either way the behavioral test is generated.

## Observability

Every ma-loop run is indexed into `.dk/observability.db` (`sentinel_runs`:
ts/tier/model/iterations/cost/status/files_changed/errors/log_path) — query it
instead of loading the verbose `.claude/sentinel/ma-loop-*.log`. See
`cli/sentinel/observability.py`.

## Open follow-ups

- dev-kid still maps internal plan ids (T001…) ↔ original authored ids (T201…);
  `_criterion_from_tasksmd` handles both via the instruction lead token, but the
  full execute-flow criterion delivery should be verified end-to-end.
- The temporal filter + in-loop test-immutability live on the micro-agent side
  (see its GOAL_AS_TEST.md).
