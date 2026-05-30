# Sentinel / Orchestrator Rework — 2026-05-28

**Origin:** dogfooding a real **Rust** build (the `gentle-eye` MCP server) through
dev-kid. The meta-goal of that exercise was *halt-and-fix any tool bug we hit —
the tool bug IS the valued finding.* Three structural gaps surfaced; this rework
closes them. All three were designed via a Claude×Gemini paired-debate and are
recorded here with **what** changed and **why**.

> TL;DR — the orchestrator now (a) only runs the **headless** `ma-loop` (the
> interactive `micro-agent` TUI path is gone), (b) places sentinels **only at
> author-marked real+compilable file-points** (the `[S]` marker), and (c) when a
> compile error originates in a **dependency** rather than the file under repair,
> the **agent fixes the dependency and re-tests** instead of letting `ma-loop`
> mangle a correct file.

---

## (a) Remove the legacy `micro-agent` TUI tier path

**Files:** `cli/sentinel/runner.py`, `cli/sentinel/tier_runner.py`

**What:** Deleted `TierRunner.run_tier1` / `run_tier2` (and the now-orphaned
`_ensure_legacy_tier_config`). `runner.py`'s sentinel dispatch no longer has a
"no `tiers_file` → legacy 2-tier" branch; with no `tiers_file` it now **fails
with actionable guidance** instead of routing into the legacy path. The headless
N-tier `run_tiered` → `ma-loop run <target> -o <objective>` is the **sole**
executor.

**Why:** `run_tier1`/`run_tier2` invoked the builder.io `micro-agent` binary,
which enters an interactive onboarding TUI ("Want to set up a new project?") and
**hangs ~300s/tier in a non-TTY context**. The headless `ma-loop` runner that
fixes this landed in `c23c9e4`, but the sentinel dispatch in `runner.py` was
**never rewired to it** — `tiers_file` projects (like gentle-eye) used
`run_tiered`, while everything else still hit the hanging legacy path. Removing it
eliminates the trap; net **−300 lines**.

---

## (b) `[S]` marker / sentinel-point predicate

**Files:** `cli/orchestrator.py` (`Task.sentinel_point`, `_process_task`,
the wave-dict builder, `_inject_sentinel_tasks`)

**What:** A task line may carry an `[S]` tag — `- [ ] T### [S]: <verb>
affecting \`path\``. The parser detects it (and strips it from the instruction).
`_inject_sentinel_tasks` is now **opt-in marker-driven**: if **any** task in the
run is `[S]`-marked, a sentinel is injected **only** at marked points (each
covering the run of tasks since the previous sentinel); unmarked tasks —
including entire skeleton waves — get **none**. A tasks.md with **zero** `[S]`
markers falls back to the existing `injection_granularity` (backward-compatible).

**Why:** The orchestrator previously injected a sentinel after **every** task
(`per-task` default). That placed a sentinel on a *stub* (`src/models/mod.rs`,
which at the time was a recovered junk container, not compilable Rust). The
sentinel ran `cargo check` against a file that **cannot** pass, the fixer spun,
and the **wave halted** (`SENTINEL-T002`). The fix: a sentinel test-point is only
valid where a **real, compilable file** exists. Crucially, the **intelligence
lives in the task-authoring agent** (it knows which outputs are real+compilable
file-points and marks them); the orchestrator stays a **mechanical gather-and-mark
process** — it just reads `[S]`. The semantic of a marked point is *"all my
dependencies are green, so I am now safely fixable in isolation."*

**Authoring guidance:** mark `[S]` on tasks that **finish a complete, runnable
file**. Do **not** mark skeleton/glue/prerequisite tasks (module declarations,
empty trait stubs) — they exist to make the tree resolve, not to pass tests.

**Mode-agnostic — mark the file `dev-kid spec-resolve` reports.** `[S]` works
identically in dev-kid **lite** (`.dk/tasks.md`) and **SpecKit**
(`.specify/specs/{branch}/tasks.md`): detection is `re.search(r'\[S\]', line)`,
so it ignores `[P]`/`[US#]` tags and both `- [ ] T### [S]:` (lite) and
`- [ ] T001 [P] [S] [US1] …` (SpecKit) line shapes work. The one trap is
*routing*: dev-kid resolves a canonical tasks.md via a priority chain, and editing
the wrong file (e.g. repo-root in a lite project, which orchestrate *replaces*)
means `[S]` never reaches the parser. Run **`dev-kid spec-resolve`** to see the
exact file it will use, and mark `[S]` there. (Origin: 2026-05-28 dogfood — `[S]`
edits to repo-root were silently ignored because lite resolves to `.dk/tasks.md`.)

---

## (c) Cross-file attribution + agent-mediated recovery

**Files:** `cli/sentinel/tier_runner.py`
(`_attribute_cargo_errors`, `_recover_external_file`, `run_tiered`)

**What:** `ma-loop` repairs **one** file (single-file-fix). After a tier fails the
independent test re-run, the orchestrator runs the cargo check with
`--message-format=json` and **attributes each error to its originating file** via
the rustc primary span:

- error's primary span is in the **target** file → it's the target's own bug →
  normal single-file fix (escalate tiers as before).
- error's primary span is in **another** file (a dependency **B**) → the **agent
  fixes B** (a bounded `ma-loop` on B, ≤3 iters) and **re-tests** before
  escalating. One cross-file hop per tiered run (`recovery_done` guard). If B
  can't be auto-fixed, the attribution is surfaced and the run escalates.

**Why:** a `cargo check` error while building file **A** can originate in a
**dependency B** (A is correct; B's interface is wrong/incomplete). rustc often
blames the *call site* A. If `ma-loop` is pointed at A, it will **mangle a correct
A** to chase an error whose real fix is in B — eroding the architecture. Routing
the fix to the *originating* file keeps single-file-fix safe. This is the seed of
the **task-instructor**: the agent (not the single-file `ma-loop`) decides where a
cross-file fix belongs and where to re-enter.

**Scope note:** attribution uses rustc JSON spans, so it is **cargo-specific** for
now (gated on `"cargo" in test_cmd`). Other languages fall through to plain
escalation; per-language attribution is future work.

---

## Verification status

- **(a)** `py_compile` clean; zero dangling refs; live `ma-loop` path intact.
- **(b)** functional test: skeleton wave → 0 sentinels; marked points → 1 sentinel
  each covering its batch.
- **(c)** `_attribute_cargo_errors` unit-tested (B-error → external, A-error → own,
  warnings/non-JSON filtered); integration `py_compile` clean.
- **Pending:** end-to-end validation (real broken-dependency recovery; a real
  `[S]`-driven wave) — happens when gentle-eye re-orchestrates through this build.

## Cross-references

- Design debate + findings: PRD `gentle_eye_devkid_dogfood_2026-05-26`
  (`~/dev/prd/scratch/`).
- `[S]` authoring convention: `.specify/templates/tasks-template.md`.
- The headless `ma-loop` switch this builds on: commit `c23c9e4`.
