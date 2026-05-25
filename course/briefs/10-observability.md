# Module 10: Observability — No Black Boxes (the finale)

### Teaching Arc
- **Metaphor:** A **flight data recorder.** A plane that crashes teaches you nothing if there's no black box — but a plane with full telemetry turns every incident into a lesson. The goal isn't zero failures; it's zero *invisible* failures. (No restaurant.)
- **Opening hook:** "The bug in Module 9 didn't hide because it was subtle. It hid because nothing *said* it was happening — a crash got quietly relabeled 'test failed, escalate.' That's the cardinal sin."
- **Key insight:** **Observability / 'no black boxes' is a constitution principle** for dev-kid (and a global rule for all of Gyasi's development). A failure must always be *visible as what it actually is*. Concrete reflexes: surface stderr/stdout, warn on anomalies (a paid model reporting $0 ≈ a parse miss), and *independently verify* success instead of trusting one exit code. The Rust Watchdog applies the same idea to processes — it catches orphans and zombies the token-based world can't see.
- **"Why should I care?":** This is the master skill for steering AI. An AI that fails silently will waste hours; an AI you've instructed to *show its work and verify its claims* fails loudly and cheaply. Demand observability by name.

### Code Snippets (pre-extracted)

File: cli/sentinel/tier_runner.py — fix #6: don't trust the exit code, re-run the test
```python
# #6 — confirm micro-agent's success with an independent test re-run.
if final_status == "PASS":
    confirmed, confirm_tail = _run_test_command(test_cmd, Path.cwd())
    if not confirmed:
        final_status = "FAIL"
        print("      ⚠️  exited 0 but independent test re-run FAILED")
```

File: cli/sentinel/tier_runner.py — fix #5: a $0 paid run is a red flag, not a free lunch
```python
is_paid_tier = bool(artisan_model) and not artisan_model.startswith("ollama")
if is_paid_tier and tier_cost == 0.0:
    print("      ⚠️  paid model reported $0.00 cost — likely a parse miss; "
          "cumulative budget may understate spend")
```

The anti-pattern (state it plainly as a "before"):
```
crash/hang  →  exit 1  →  "tier exhausted"  →  escalate   (BLACK BOX: the truth is gone)
```
The fix is to make each arrow *say what it saw*: surface the stderr tail, the $0 warning, the independent re-run result.

The Watchdog angle (process observability):
- Orphan = process still alive but its task is marked done. Zombie = task running but the process died. Both are *invisible* to a token-based agent; the Rust Watchdog sees them because it watches real PIDs.

### Interactive Elements
- [x] **Data flow animation** — the hero, a before/after. "Before": crash → exit1 → escalate, each step a closed gray box (truth lost). "After": the same path but each arrow emits a visible signal (stderr tail, ⚠️ $0 warning, re-run result) so the human sees the real cause.
- [x] **Code↔English translation** — fix #6 (`_run_test_command`): explain "don't believe 'I passed' — go check the tests yourself," tying back to the Module 4 checkpoint principle (verify, don't trust).
- [x] **Quiz** — 4 Qs, the capstone. e.g. "An AI agent says 'done' and exits 0 — what's the cheapest way to not get burned?" (re-run the verification) "A paid API step logs $0 — celebrate or investigate?" "What's the difference between a bug and a *black-box* bug, and which is worse?" "How would you instruct an AI tool to be observable?" (surface errors, verify claims, no silent fallbacks).
- [x] **Callout** — "aha!": *Crashes and bugs are acceptable and even useful — if they're observable.* The enemy isn't failure; it's invisibility.
- [x] **Pattern/feature cards** — the observability toolkit: (1) Surface stderr/stdout, (2) Warn on anomalies, (3) Independently verify, (4) Watch real processes, (5) Always write the manifest.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Scenario Quiz", "Callout Boxes", "Pattern/Feature Cards", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Integration Bug" — the case study in invisibility.
- **Next module:** none — this is the finale. End with a confident send-off: the learner can now name the parts, trace the flow, AND demand observability from any AI system they steer.
- **Tone/style notes:** Vermillion. Callbacks welcome — Module 4 ("no silent failures"), Module 6 ("manifest always written"), Module 9 (the silent escalation). This is the thesis the whole course was building toward. Tooltip: observability, telemetry, stderr/stdout, orphan/zombie process, PID, exit code, fallback.
