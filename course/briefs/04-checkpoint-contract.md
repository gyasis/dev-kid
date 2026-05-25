# Module 4: The Checkpoint Contract (low-level)

### Teaching Arc
- **Metaphor:** **A lock on a canal.** A boat can't enter the next chamber until the current one is verified full and the gate confirms it. No "close enough" — the water level is checked, then the gate opens. (No restaurant.)
- **Opening hook:** "A wave finished... or did it? Dev-Kid refuses to start the next wave until it can *prove* the last one is done. That refusal is the safety mechanism that keeps an over-eager AI honest."
- **Key insight:** The Wave Executor is **verification-gated**: after each wave it re-reads `tasks.md`, confirms every task is marked `[x]`, and **HALTS** if not — then commits a git checkpoint. Progress is only ever *claimed* if it's *proven on disk*.
- **"Why should I care?":** This is your guardrail against AI "I'm done!" hallucinations. If the executor halts, the AI said done but didn't mark it done — you've caught a lie cheaply.

### Code Snippets (pre-extracted)

File: cli/wave_executor.py — verification gate (around lines 186-218)
```python
def verify_wave_completion(self, wave_id: int, tasks: List[Dict]) -> bool:
    # Check if each task line contains [x]
    for task in tasks:
        ...
        if "[x]" in line:
            ...  # task verified complete
    ...
verified = self.verify_wave_completion(wave_id, tasks)
```

File: cli/wave_executor.py — the HALT path (the safety reflex)
```python
print(f"      ❌ Sentinel HALT: {msg}")
```

Conceptually: verify → (if pass) `_update_progress()` → `_git_checkpoint()` → next wave. (if fail) HALT.

### Interactive Elements
- [x] **Group chat animation** — the hero. Actors: Wave Executor, tasks.md, Git. Flow: Executor → tasks.md "are all of you marked [x]?"; tasks.md "T002 still says [ ]"; Executor → "HALT. Not committing." (Then a second happy-path run where all are [x] → Git "checkpoint committed ✓".)
- [x] **Code↔English translation** — `verify_wave_completion`: explain `[x]` vs `[ ]` as a checkbox on disk, and "return True only if ALL are checked."
- [x] **Quiz** — 3 Qs, debugging. e.g. "Execution stopped after Wave 1 with 'HALT'. The AI swears it finished. Where's the truth?" (tasks.md markers) "Why commit a git checkpoint after every wave instead of at the end?" (recover/rewind safely).
- [x] **Callout** — "aha!": "No silent failures" — the executor would rather stop loudly than continue on a guess. (Plant the observability theme for Module 10.)

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Building Waves."
- **Next module:** "The Sentinel" — between finishing a wave and checkpointing it, an inspector runs.
- **Tone/style notes:** Vermillion. Tooltip: git commit, checkpoint, halt, verification, marker. The "no silent failures" callout is a deliberate setup for the observability finale.
