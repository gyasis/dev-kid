# Module 9: The Integration Contract Mismatch ⭐ (the centerpiece)

### Teaching Arc
- **Metaphor:** **Calling the wrong phone number from a business card.** The card lists two numbers — "Sales" and "24/7 Support." You need the after-hours fix, but you dial Sales, which is closed, so you get an automated menu that waits forever for a human who never picks up. The number was *valid* — it just wasn't the one that does the job you need. (No restaurant.)
- **Opening hook:** "Everything you just learned — the tiers, the budget, the Ralph Loop — hangs on one line of wiring. And that wiring calls the wrong door. The Sentinel's engine has never actually started."
- **Key insight:** micro-agent ships **two entry points**: `micro-agent` (a single-file generator that *requires a file path* and otherwise drops into an interactive prompt) and `ma-loop` (the actual Ralph Loop with `--tier-config`). The Sentinel calls **`micro-agent`** with `--prompt/--test/--max-runs` and **no file path** → it falls into `interactiveMode` → tries to draw a terminal prompt → **crashes (or, wrapped in a fake terminal, hangs)** → exits non-zero → the Sentinel reads "test failed, escalate." The loop never runs.
- **"Why should I care?":** This is the #1 real-world AI-coding failure: an *integration contract mismatch*. Two parts that each "work" but don't agree on how to talk. You'll learn to smell it: "it always fails the same silent way" = suspect the contract, not the logic.

### Code Snippets (pre-extracted)

File: micro-agent src/cli.ts (lines ~126-135) — the fork in the road
```ts
if (!argv._.filePath || !argv.flags.test) {
  const isValidproject = await isValidProject();
  if (!isValidproject) {
    await invalidProjectWarningMessage();
  } else {
    await interactiveMode(runOptions);   // ← asks a human; no human here
  }
  return;                                // ← runAll() (the real work) NEVER called
}
await runAll(runOptions);
```

File: micro-agent package.json — two doors, one card
```json
{ "bin": {
  "micro-agent": "./dist/cli.mjs",       // single-file generator (what Sentinel calls)
  "ma-loop":     "./dist/ralph-loop.mjs" // the Ralph Loop with --tier-config (what it NEEDS)
}}
```

The reproduction evidence (show as a terminal-output card, three runs):
```
# A) bare dir, no file path:
✖ TTY initialization failed: uv_tty_init returned EINVAL   → exit 1
# B) valid project, no file path:
interactiveMode() → ✖ TTY EINVAL                            → exit 1
# C) real call wrapped in `script -qfc` (fake terminal):
┌  🦾 Micro Agent  ◆ ...  (interactive prompt, waiting for a human)
                                                            → HANGS → exit 124 (timeout)
```

The secondary mismatch — even if it ran, the Sentinel can't read the output:
```
micro-agent prints:           Sentinel's regex wants:
  "Completed in 3 iteration(s)"  →  "Iterations: 3"   ✗ no match → 0
  "Total cost: $0.47"            →  "Cost: $0.47"      ✓ (lucky substring)
  "Duration: 2.5 minutes"        →  "Duration: 2.5s"   ✗ wrong unit → 0
```

### Interactive Elements
- [x] **Group chat animation** — the hero (a *broken* conversation). Actors: Sentinel, micro-agent, (off-stage) ma-loop. Flow: Sentinel "run the fix loop! --prompt --test --max-runs"; micro-agent "...you didn't give me a file path. Entering interactive mode 🤖❓"; micro-agent "(waiting for a human...)"; Sentinel (after timeout) "no answer → exit 1 → must be a test failure, escalate"; caption: *ma-loop, the one who could've done it, was never called.*
- [x] **Spot-the-bug challenge** — show the Sentinel's invocation (`micro-agent --prompt X --test Y --max-runs N`) next to micro-agent's usage (`micro-agent [flags] [file path]` / `ma-loop run <target> --tier-config`). Ask the learner to spot what's missing and which binary should've been called.
- [x] **Code↔English translation** — the `cli.ts:126` branch: explain `!argv._.filePath` ("no file path was given") and that `return` before `runAll` means "the real work never happens."
- [x] **Quiz** — 4 Qs, debugging/architecture. e.g. "Sentinel reports every task as 'all tiers exhausted.' What's the FIRST thing you'd suspect — the models, or the wiring?" "Why did wrapping it in a fake terminal (`script -qfc`) make it *worse* (hang vs crash)?" "What's the clean fix?" (options: route Sentinel to `ma-loop run --tier-config`; keep `micro-agent` for single-file; gate the legacy 2-tier path so it can't collide with the new `--tier-config` feature).
- [x] **Callout** — "aha!": A non-zero exit code is NOT the same as "the work ran and failed." Here it meant "the work never started." Trusting one number hid the whole bug. (Hard pivot into Module 10.)

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Spot the Bug Challenge", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Scenario Quiz", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Tiers & Budget" — all that machinery, never reached.
- **Next module:** "Observability" — why this hid for so long, and how to make failures impossible to miss.
- **Tone/style notes:** Vermillion. This is the emotional peak — let it breathe, use the real evidence verbatim. Frame the fix as "clear paths: `ma` for single-file, `ma-loop` for the loop; Sentinel → `ma-loop`; legacy kept intact but gated so it can't collide with new features." Tooltip: entry point/binary, positional argument, flag, TTY, exit code, interactive mode, regex, integration contract.
