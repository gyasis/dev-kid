# Module 6: Inside the Sentinel (low-level)

### Teaching Arc
- **Metaphor:** A **building inspection with a fixed clipboard.** Each line item is a separate specialist (electrical, plumbing, structural). One clipboard, many checks, and a signed report filed *every time* — pass or fail. (No restaurant.)
- **Opening hook:** "The Sentinel isn't one blob — it's a folder of small specialists. Open `cli/sentinel/` and you meet them."
- **Key insight:** Each check is its own module. The **change-radius** check is the cleverest: a *three-axis budget* — too many files, too many lines, OR any interface change trips it. And a **manifest** (3 files) is written on every run so there's always a paper trail.
- **"Why should I care?":** When the Sentinel blocks you, knowing *which axis* tripped (files vs lines vs interface) tells you exactly how to respond — split the task, or accept the interface change.

### Code Snippets (pre-extracted)

File: cli/sentinel/ — the module map (file tree)
```
cli/sentinel/
├── runner.py            # orchestrates the pipeline
├── placeholder_scanner.py  # TODO/FIXME/stub detector
├── interface_diff.py    # public API surface diff (Python/TS/Rust)
├── cascade_analyzer.py  # 3-axis change-radius + cascade warnings
├── manifest_writer.py   # writes manifest.json + diff.patch + summary.md
└── tier_runner.py       # the test-fix loop (next module)
```

File: cli/sentinel/cascade_analyzer.py — the three-axis budget (lines ~75-86)
```python
violations: list[str] = []
if files_count > self._max_files:
    violations.append("files")
if lines_total > self._max_lines:
    violations.append("lines")
if interface_changes_count > 0 and not self._allow_interface:
    violations.append("interface")
budget_exceeded = bool(violations)
```

File: dev-kid.yml — the budget you're spending against
```yaml
change_radius:
  max_files: 3
  max_lines: 150
  allow_interface_changes: false
```

### Interactive Elements
- [x] **Interactive architecture diagram** OR **visual file tree** — the hero: the `cli/sentinel/` folder, each module clickable → its one job.
- [x] **Code↔English translation** — the three-axis snippet: explain that `violations` is a *list* (you can trip more than one axis at once), and what each axis means in plain terms.
- [x] **Quiz** — 3 Qs, architecture/debugging. e.g. "Sentinel blocked a task that changed 1 file and 4 lines — which axis tripped?" (interface) "A manifest exists even though the run errored — why is 'always write the report' a deliberate design choice?" (observability — paper trail).
- [x] **Callout** — "aha!": the manifest is written in a `try/finally` so it survives even crashes — *the report always gets filed.* (Observability seed.)

### Reference Files to Read
- `references/interactive-elements.md` → "Visual File Tree", "Interactive Architecture Diagram", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Config Badges", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Sentinel" (philosophy).
- **Next module:** "The Ralph Loop" — the engine inside step 3 (the test-fix loop).
- **Tone/style notes:** Vermillion. LOW-LEVEL module. Tooltip: module/package, interface/API surface, manifest, diff/patch, budget. The "manifest always written" callout feeds the observability finale.
