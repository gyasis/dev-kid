# Module 3: Building Waves (low-level)

### Teaching Arc
- **Metaphor:** **Boarding an airplane by zones.** Everyone's going to the same place, but you can't all jam the aisle at once. Group by who can move without blocking others; if two passengers need the same seat, one waits. (No restaurant.)
- **Opening hook:** "Your `tasks.md` is just a flat list. How does dev-kid know T003 can run *at the same time* as T001, but T005 has to wait? That's the Orchestrator's whole job."
- **Key insight:** The Orchestrator builds a dependency graph from three signals — **file locks** (two tasks touching the same file can't run together), **explicit deps** ("after T001"), and **`## Wave N` headers** — then greedily packs tasks into the earliest wave where nothing conflicts.
- **"Why should I care?":** Knowing the backtick-path convention means YOU can make the AI's plans correct just by how you phrase a task. And when parallel tasks collide, you'll know the plan — not the code — is wrong.

### Code Snippets (pre-extracted)

File: cli/orchestrator.py — `## Wave N` headers become hard phase boundaries (lines ~123-136)
```python
# Wave-section phase header — `## Wave N`, `### Phase 2`, etc.
if self.WAVE_HEADER_RE.match(line):
    if current_task_lines:
        self._process_task(current_task_lines, task_id, current_wave_idx)
        task_id += 1
        current_task_lines = []
    self._wave_phases.append([])
    current_wave_idx = len(self._wave_phases) - 1
    continue
```

File: cli/orchestrator.py — every task in Wave N depends on all tasks in Waves 1..N-1 (lines ~608-615)
```python
for wave_idx, task_ids in enumerate(self._wave_phases):
    if wave_idx == 0:
        continue  # Wave 1 has no upstream phase
    for tid in task_ids:
        for prior_wave in self._wave_phases[:wave_idx]:
            for prior_tid in prior_wave:
                if prior_tid != tid:
                    graph[tid].add(prior_tid)
```

(Mention, don't necessarily show: file-lock conflicts create *implicit* sequential deps — two tasks naming the same `` `file.py` `` can't share a wave.)

### Interactive Elements
- [x] **Data flow / step animation** — show 5 tasks with file tags flowing into wave buckets: T1(`a.py`) & T2(`b.py`) land in Wave 1 (parallel); T3(`a.py`) collides with T1 → bumped to Wave 2. This is the hero.
- [x] **Code↔English translation** — the wave-phase edge snippet: explain a "dependency graph" (who-waits-on-whom) and why Wave 2 tasks each get an edge to every Wave 1 task.
- [x] **Quiz** — 3 Qs, scenario + architecture. e.g. "Two tasks both edit `config.py` but you forgot the backticks — what goes wrong and how do you fix the *phrasing*?" "You want T009 to run dead last — what's the cheapest way to force that?" (a `## Wave` header).
- [x] **Callout** — "aha!": file-lock detection is just *string matching on backtick paths* — that's why the convention matters.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Scenario Quiz", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Meet the Cast."
- **Next module:** "The Checkpoint Contract" — what happens when a wave actually runs.
- **Tone/style notes:** Vermillion. This is a LOW-LEVEL module — one real algorithm, taught gently. Tooltip: dependency graph, greedy algorithm, regex, parse, edge/node.
