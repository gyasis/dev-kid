# Module 5: The Sentinel — A Bouncer for Every Task (high-level)

### Teaching Arc
- **Metaphor:** A **bouncer at the door** of each wave's checkpoint. Before any task's work is allowed past the velvet rope (the git commit), the bouncer checks IDs: no fake code, tests actually pass, the change didn't blow up the scope. (No restaurant.)
- **Opening hook:** "Between 'the AI says the task is done' and 'we commit it,' dev-kid slips in an inspector that tries to *disprove* the work. Meet the Integration Sentinel."
- **Key insight:** The Sentinel runs a fixed pipeline per task: **placeholder scan → resolve test command → run a fix-it test loop → interface diff → change-radius check → cascade → always write a manifest.** It can FAIL/HALT, PASS, or SKIP.
- **"Why should I care?":** This is the difference between "AI claims done" and "proven done." Understanding the gates tells you exactly what kind of badness each one catches.

### Code Snippets (pre-extracted)

File: cli/sentinel/runner.py — the pipeline (docstring, the cleanest summary)
```python
# SentinelRunner.run() orchestrates the complete pipeline:
#   1. Placeholder scan (pre-test-loop)
#   2. Test framework detection
#   3. Tiered micro-agent test loop (Tier 1 Ollama → Tier 2 cloud)
#   4. Interface diff
#   5. Change radius evaluation
#   6. Cascade analysis
#   7. Manifest writing
```

File: cli/sentinel/runner.py — a real gate: stub code in production fails the wave (~lines 140-149)
```python
if violations and fail_on_detect:
    print(f"      🚫 Sentinel: {len(violations)} placeholder violation(s) detected")
    result_obj.result = "FAIL"
    result_obj.should_halt_wave = True
```

File: dev-kid.yml — it ships OFF by default (the bootstrap clue, foreshadows Module 9)
```yaml
sentinel:
  enabled: false
  mode: auto
```

### Interactive Elements
- [x] **Group chat animation** — the hero. Actors: Wave Executor, Sentinel, Test Loop, Manifest. Flow: Executor "task T001 says done"; Sentinel "let me check — any TODO/stub code? tests green? scope sane?"; on a stub found → "🚫 FAIL, halting"; manifest "logged either way."
- [x] **Code↔English translation** — the placeholder-fail snippet: explain `should_halt_wave = True` as "pull the emergency brake on the whole wave."
- [x] **Quiz** — 3 Qs. e.g. "The AI left a `# TODO: implement later` in shipped code — which gate catches it?" "Sentinel returns SKIP, not FAIL — what does that tell you?" (config/env issue, not bad code) "Why might a brand-new dev-kid project have sentinel OFF?"
- [x] **Callout** — "aha!": the Sentinel is built to *distrust* the AI — PASS is earned, not assumed.

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Permission/Config Badges", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Checkpoint Contract."
- **Next module:** "Inside the Sentinel" — the module map and the three-axis change radius.
- **Tone/style notes:** Vermillion. `enabled: false` is a planted clue — note it as curious ("why ship your safety system OFF?") but don't resolve until Module 9. Tooltip: stub/placeholder, manifest, interface, halt, config.
