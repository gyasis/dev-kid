# Module 8: The Tier Ladder & the Money Guard (low-level, economy-first)

### Teaching Arc
- **Metaphor:** **Triage in an ER.** Start with the cheapest, fastest responder (a local model); only escalate to the expensive specialist (a cloud model) if the case is still unresolved — and a hospital administrator (the budget tracker) can shut the whole ward if the bill runs away. (No restaurant.)
- **Opening hook:** "AI calls cost money. Dev-Kid's answer: try the free local model first, escalate only when stuck, and keep a running tab that can slam the brakes."
- **Key insight:** `ralph-tiers.json` defines an escalation ladder (free local → cheap cloud → strong cloud → human handoff). A **global BudgetTracker** sums cost across *every* sentinel in a run and halts before the ladder bankrupts you.
- **"Why should I care?":** This is "economy-first" made concrete. When you steer AI systems, you want exactly this instinct: cheap-first, escalate-on-need, hard cap. You can demand it by name.

### Code Snippets (pre-extracted)

File: ralph-tiers.json — the ladder (cheap → expensive)
```json
{ "tiers": [
  { "name": "all-local",  "models": { "artisan": "ollama/qwen3-coder:30b", "critic": "ollama/deepseek-r1:32b" } },
  { "name": "groq-fast-free", "models": { "artisan": "groq/llama-3.3-70b-versatile" } },
  { "name": "claude-code-handoff", "type": "handoff", "requires_marker": "allow-handoff" }
] }
```

File: cli/sentinel/budget_tracker.py — the money guard (lines ~120-145)
```python
def would_exceed(self, projected_cost: float) -> bool:
    """True if recording projected_cost would push cumulative past the global cap."""
    return (self._cumulative_cost + projected_cost) > self.budget_usd

def is_exhausted(self) -> bool:
    return self._cumulative_cost >= self.budget_usd

def record(self, cost_usd, duration_sec, task_id=None) -> None:
    self._cumulative_cost += float(cost_usd)
    ...
    self._persist()   # survives crashes / resumes
```

File: cli/sentinel/budget_tracker.py — the early-warning siren (~lines 165-174)
```python
return (f"⚠️  CUMULATIVE BUDGET WARNING: ${self._cumulative_cost:.2f} of "
        f"${self.budget_usd:.2f} spent across {self._task_count} sentinel(s)")
```

### Interactive Elements
- [x] **Data flow / step animation** — the hero: a task climbing the ladder. Local tier (free) tries & fails → groq (cheap) tries & fails → cloud (paid) → each step the budget bar fills; if it would overflow, the rung is skipped with a 🛑.
- [x] **Code↔English translation** — `would_exceed` / `record`: explain "cumulative" (sum across ALL tasks, not one), and why state is persisted to disk (a resumed run remembers what it already spent — no budget-reset abuse).
- [x] **Quiz** — 3 Qs. e.g. "Why track budget *cumulatively* across 65 tasks instead of per-task?" (65 × $5 = $325) "A free local tier should never be skipped by the budget guard — why?" (it costs $0) "What's the 'handoff' tier for?" (hand the hard one to a human/Claude Code session for $0).
- [x] **Callout** — "aha!": "Recall gaps are acceptable; runaway bills are not." Economy-first is a design value, not an afterthought.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Config Badges", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Ralph Loop."
- **Next module:** "The Integration Bug" — the centerpiece: all this machinery, wired to the wrong binary.
- **Tone/style notes:** Vermillion. LOW-LEVEL. Tooltip: tier, escalation, cumulative, persist, cap, handoff, local vs cloud model. Note `--tier-config` belongs to `ma-loop` (sets up Module 9).
