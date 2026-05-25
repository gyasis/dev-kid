# Changelog

All notable changes to dev-kid. Format roughly follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versions follow [SemVer](https://semver.org/).

---

## v2.3.0 — 2026-05-25

Minor release. Reworks how `dev-kid init` deploys Claude Code hooks (copy →
symlink), adds broken-link detection to `init-check`, fixes a watchdog
exit-code bug that produced a confusing shell error, and documents the
hook master-switch / per-project deactivation properly.

### Changed

- **`dev-kid init` now SYMLINKS hook scripts instead of copying them.**
  Each `<project>/.claude/hooks/*.sh` is a symlink to the install-managed
  canonical source at `~/.dev-kid/templates/.claude/hooks/`. Rationale:
  - **Single source of truth** — one edit to a template propagates to every
    project on the machine; no more drifting per-project copies that silently
    diverge from the canonical hook.
  - **No repo pollution** — `.claude/` is gitignored per project, so the
    symlinks are machine-local and never committed.
  - `settings.json` is still **copied** (not symlinked): it's per-project
    config the user tweaks (e.g. `DEV_KID_HOOKS_ENABLED`).
  - Re-running `dev-kid init` on a project with old *copied* hooks converts
    them to symlinks in place (`ln -sfn`).
  - The per-file symlink loop also retires the old `cp -r …*` + `rm -rf
    .claude/hooks/hooks/` nested-glob cleanup hack.

### Added

- **`dev-kid init-check` now FAILs on broken hook symlinks.** If the install
  moved or was removed, the symlinks dangle and Claude Code can't run the
  hooks. The check reports the broken names and hints `re-run 'dev-kid init'`
  to re-point them. (`check_claude_hooks` in `cli/init_check.py`.)
- **HOOKS_REFERENCE.md**: a "Hook Deployment Model" section explaining the
  symlink layout + repair path, and a "Deactivating dev-kid for a project"
  recipe — `DEV_KID_HOOKS_ENABLED` documented as the master switch, with the
  *persistent* `settings.json` `env`-block method clearly distinguished from
  the *ephemeral* shell `export`.

### Fixed

- **Watchdog binary resolution swallowed its own failure.** Three call sites
  used `local watchdog_bin=$(find_watchdog_binary) || exit 1`. Because the
  `local` builtin always returns exit 0, it masked the command
  substitution's exit code — so `|| exit 1` never fired when the binary was
  missing, and execution fell through to run an *empty* command, printing the
  confusing `dev-kid: line 724: : command not found` on top of the real
  "binary not found" message. Split declaration from assignment at all three
  sites (`cmd_watchdog_check`, `cmd_watchdog_report`, `cmd_task_complete`) so
  the guard fires and the command exits cleanly with just the helpful message.

### Upgrade notes

- Existing projects keep working with their copied hooks. To adopt the
  symlink model (and pick up future template edits automatically), re-run
  `dev-kid init` in the project. No data is lost — `settings.json` and
  `.dk/tasks.md` are left untouched.

## v2.2.1 — 2026-05-22

Patch release for the install script.

### Fixed

- `scripts/install.sh` aborted with `cp: cannot stat 'DEV_KID.md'` partway
  through (DEV_KID.md was removed during the `db3df65` "repo cleanup for
  public-facing release" but install.sh kept referencing it). Anyone cloning
  a fresh copy hit this immediately.
- Post-install help text said `cat $INSTALL_DIR/DEV_KID.md` for the same
  missing file. Now points at the first available of `README.md` /
  `QUICKSTART.md` / `CHANGELOG.md`.
- install.sh's own `VERSION=` header was lagging at `2.0.0`. Synced to
  match the CLI's `2.2.1` so the install banner doesn't lie.

### Changed

- Documentation-file copy is now graceful: a loop with `[ -f ]` guards. Any
  doc file removed in future repo cleanup will be skipped with a warning
  instead of bailing the entire install.

---

## v2.2.0 — 2026-05-22

Catch-up release. The version string had drifted (README claimed v2.2 since
April, but `VERSION=` was still `2.0.0` and no tag was cut). This release
ships everything accumulated since v2.0.0 — the sentinel-stack rewrite, the
budget+handoff system, the preflight gate, init-check, AND a fresh
adversarial-audit autonomy pass.

### Added — sentinel-stack rewrite

- `feat: rewrite sentinel tier ladder for Ollama+Google+OpenAI mix, add gates`
  Tier-runner can now mix providers per tier instead of being Ollama-only.
- `feat: close wave-orchestration gaps + add sentinel solo + LLM dep parser`
  Sentinel can now run standalone (not only in-wave); LLM-backed dependency
  parser fallback via `--agent-parse` flag.
- `feat: add openai/google/anthropic providers to agent_dep_parser`
  Three-provider support for the dep-parser tier.

### Added — preflight + init-check tooling

- `feat(cli): add preflight gate and init-check validator`
  Default preflight gate before `dev-kid execute`; 10-check `init-check`
  validates project setup.
- `docs: surface preflight + init-check in slash commands and README`

### Added — budget tracker + Claude Code handoff tier

- `feat(sentinel): cumulative budget tracker + Claude Code handoff tier`
  Sentinel tracks cumulative spend across runs; Claude Code is the new
  top-tier escalation path.
- `feat(slash+hook): handoff slash commands + auto-notifier hook for
  proactive Claude Code awareness`

### Added — Spec 002 autonomy & reconciliation pass (2026-05-22)

Adversarial audit on real-world friction during a 49-task spec implementation
(Spec 002 of `prdone`). Two locked north stars from the user:

  1. **Attach to A tasks.md no matter what** — silent re-routing must die.
  2. **Preflight must not require Anthropic** when sentinel is disabled.

13 fixes synthesized from 8 + 11 hunter findings (5 overlapping). All
backward-compatible.

- **`dev-kid spec-resolve`** (alias: `which-spec`) — pure-read introspection.
  Prints the resolution triple (`git branch` / `.specify/feature.json` /
  `tasks.md` symlink) + the resolved tasks.md + WHY. No side effects.
  Surfaces 100%-complete state with a warning so silent empty-wave plans
  can't happen. The "assembly-line floor inspection" tool.
- **`--force-symlink`** flag on `dev-kid orchestrate` — explicitly overrides
  an existing valid `tasks.md` symlink. Without this flag the existing
  symlink is HONORED (was previously silently overwritten).
- **`speckit alignment` check** in `dev-kid init-check` — cross-references
  branch ↔ feature.json ↔ tasks.md symlink and reports divergence as FAIL.
  Now 11 checks (was 10).
- **`dev-kid --version` / `-v`** aliases for the existing `version` subcommand.
- **Preflight cache** at `<project>/.devkid/.preflight-ok` (30-min TTL,
  env-hash-keyed). Prevents per-wave re-prompting in interactive flows.
- **Non-TTY auto-yes** in `preflight.sh` — scripts/cron/agent contexts now
  proceed without hanging on `read` from a closed stdin.

### Changed — orchestrate resolution chain (Spec 002)

`dev-kid orchestrate` resolves tasks.md via a layered chain with explicit
precedence (was: branch-only, overwrote everything). New precedence:

  1. Existing valid `tasks.md` symlink (HONORED — pass `--force-symlink` to override)
  2. `.specify/feature.json` `feature_directory` / `name` field
  3. `.specify/specs/<branch>/tasks.md` (speckit standard layout)
  4. `specs/<branch>/tasks.md` (speckit without `.specify/` prefix)
  5. `specs/*/tasks.md` MOST-RECENTLY-MODIFIED (was: alphabetical first)

The chosen source + reason is now printed explicitly before any symlink
mutation. No more silent re-routes.

### Changed — preflight gate (Spec 002)

- Now reads `sentinel.enabled` from `dev-kid.yml`. When `false`, the provider
  readiness check is skipped entirely (was: gated even when sentinel was off,
  requiring `--no-preflight`).
- Failure message lists the three bypass options:
  `sentinel.enabled: false` / `--no-preflight` / source provider keys.

### Changed — orchestrate refuses 100%-skip (Spec 002)

When 100% of tasks are already `[x]`, refuses to write an empty
`execution_plan.json` and exits 3 with a diagnostic pointing at
`dev-kid spec-resolve`. Bypass: `ALLOW_EMPTY_WAVES=1`.

### Changed — wave_executor (Spec 002)

`_wave_already_complete` no longer swallows `FileNotFoundError` /
`PermissionError` as "wave incomplete" (which caused infinite replay loops
on broken symlinks). Now fails fast with exit 2 and a diagnostic. Also
strengthens task-line matching: prefers task-id boundary match, falls back
to substring (reduces cross-spec collisions on shared phrases).

### Fixed — pre-existing source bugs

- `a653d62` fix(init): respect user's "no" answer to sentinel prompt
- `f393dc7` fix(sentinel): wrap micro-agent in `script -qfc` pseudo-TTY to
  defeat EINVAL crash
- `c18b24d` fix(help): escape `$` in `--fresh-budget` help text so bash
  doesn't interpolate `$0`
- `a6c84d3` fix+docs: `.attic/` collision in `sweep_stale_handoffs` +
  README v2.2
- `4a6ef82` fix: address adversarial bug-hunter findings on budget+handoff
  feature

### Fixed — Spec 002 audit findings

- `.specify/feature.json` was previously read by NOTHING. Hand-edits to that
  file were dead writes. Now it's priority-1 in the resolution chain.
- Manual `tasks.md` symlinks were silently overwritten by `ln -sf` based on
  the git-branch-derived path. Now honored unless `--force-symlink`.
- Glob fallback used alphabetical sort, so `specs/001-*` always beat
  `specs/002-*` even when 002 was the active work. Now mtime-newest.
- `dev-kid execute --yes` refused with "providers not ready" even when
  `sentinel.enabled: false` made provider keys irrelevant.
- Non-TTY contexts (`dev-kid execute` from a script with no stdin) hung on
  the interactive `read -r -p "Proceed?"` line.
- Symlink-overwrite messaging now differentiates create / replace / refresh
  cases (was: all three printed as informational).

### Migration notes

No action required. All changes are backward-compatible:
- Projects with existing valid `tasks.md` symlinks now have them HONORED
  instead of overwritten — this matches user intent.
- Projects with `sentinel.enabled: false` now skip the preflight gate; if
  you relied on the old refusal as a sanity check, set `sentinel.enabled:
  true`.
- Projects that hit the silent-empty-wave bug get a loud refusal now;
  legitimate "feature done" runs need `ALLOW_EMPTY_WAVES=1`.

### Internals

- `VERSION=` string bumped 2.0.0 → 2.2.0 (was untagged for ~6 weeks while
  README and merge commits already claimed v2.2)
- All Spec 002 fixes verified live on `~/dev/projects/prdone`
  (002-html-companions branch)
- Audit synthesis: 8 targeted + 11 sweep adversarial-bug-hunter findings →
  13 unique fixes

---

## v2.0.0 — 2026-04-19

Baseline. Original release.
