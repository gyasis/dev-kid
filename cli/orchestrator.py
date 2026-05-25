#!/usr/bin/env python3
"""
Task Orchestrator - Converts linear tasks into parallel wave execution
"""

import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set


@dataclass
class Task:
    """Represents a single task"""

    id: str
    description: str
    agent_role: str = "Developer"
    file_locks: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    # Tasks this one *blocks* / must come before. Inline "blocks Txxx" or
    # "before Txxx" lands here; analyze_dependencies() converts each into an
    # edge target→self so the target depends on us (not the other way round).
    blocks_tasks: List[str] = field(default_factory=list)
    constitution_rules: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass
class Wave:
    """Represents an execution wave"""

    wave_id: int
    strategy: str  # PARALLEL_SWARM or SEQUENTIAL_MERGE
    tasks: List[Dict]
    rationale: str
    checkpoint_enabled: bool = True


class TaskOrchestrator:
    """Orchestrates task execution with waves and checkpoints"""

    # Maximum tasks per wave. Prevents 50+ task monster waves that overwhelm
    # Claude Code sessions. Configurable via dev-kid.yml wave_size or
    # ConfigSchema.wave_size. Default: 10.
    DEFAULT_MAX_WAVE_SIZE = 10

    # Wave-section header recognized in lightweight-mode tasks.md. Acts as a
    # hard phase boundary — every task under `## Wave N` gets implicit dep
    # edges to every task in Waves 1..N-1 (see analyze_dependencies). Accepts
    # Wave / Phase / Step / Stage with a numeric or alpha id and optional
    # title after `:`, `-`, en-dash, or em-dash.
    WAVE_HEADER_RE = re.compile(
        r"^\s*#{1,6}\s+(?:Wave|Phase|Step|Stage)\s+([0-9A-Za-z]+)"
        r"\s*(?:[:\-–—].*)?$",
        re.IGNORECASE,
    )

    def __init__(
        self,
        tasks_file: str = "tasks.md",
        max_wave_size: int = 0,
        agent_parse: bool = False,
    ):
        self.tasks_file = Path(tasks_file)
        self.tasks: List[Task] = []
        self.waves: List[Wave] = []
        self.file_to_tasks: Dict[str, List[str]] = defaultdict(list)
        self._max_wave_size = max_wave_size or self._load_wave_size()
        # Dependencies declared in a `## Dependencies` prose section.
        # Populated by parse_tasks(), consumed by analyze_dependencies().
        self._prose_deps: Dict[str, List[str]] = {}
        # Wave-section phase membership for lightweight-mode tasks.md.
        # Each list element is the ordered task IDs under one `## Wave N`
        # header. Populated by parse_tasks(); consumed by
        # analyze_dependencies() to emit cross-phase edges so every Wave-N
        # task depends on every task in Waves 1..N-1. Empty when tasks.md
        # has no wave headers (SpecKit / hand-authored flat lists).
        self._wave_phases: List[List[str]] = []
        # Enable LLM-backed dep parser (Tier 2 — opt-in, slower but smarter).
        self._agent_parse = agent_parse or self._agent_parse_enabled_in_yml()

    def _load_wave_size(self) -> int:
        """Load max wave size from dev-kid.yml or config. Falls back to DEFAULT_MAX_WAVE_SIZE."""
        try:
            yml_path = Path("dev-kid.yml")
            if yml_path.exists():
                content = yml_path.read_text(encoding="utf-8")
                for line in content.splitlines():
                    s = line.strip()
                    if s.startswith("wave_size:"):
                        val = s.split(":", 1)[1].split("#")[0].strip()
                        parsed = int(val)
                        if parsed >= 1:
                            return parsed
        except Exception:
            pass
        return self.DEFAULT_MAX_WAVE_SIZE

    def parse_tasks(self) -> None:
        """Parse tasks.md into Task objects"""
        if not self.tasks_file.exists():
            print(f"❌ Error: {self.tasks_file} not found")
            sys.exit(1)

        try:
            content = self.tasks_file.read_text(encoding="utf-8")
        except Exception as e:
            print(f"❌ Error reading {self.tasks_file}: {e}")
            sys.exit(1)

        lines = content.split("\n")

        task_id = 1
        current_task_lines = []
        # Track which wave bucket the next task belongs to. -1 = pre-wave
        # (no wave header seen yet); a wave header bumps this to 0, 1, 2…
        current_wave_idx = -1
        self._wave_phases = []

        for i, line in enumerate(lines):
            # Wave-section phase header — `## Wave N`, `### Phase 2`, etc.
            # Flush any open task block into the OLD wave before bumping the
            # index, so a stray task between the last bullet and the next
            # heading still lands in the correct phase.
            if self.WAVE_HEADER_RE.match(line):
                if current_task_lines:
                    self._process_task(current_task_lines, task_id, current_wave_idx)
                    task_id += 1
                    current_task_lines = []
                self._wave_phases.append([])
                current_wave_idx = len(self._wave_phases) - 1
                continue

            is_task_line = line.startswith("- [ ]") or line.startswith("- [x]")
            is_sentinel_line = (
                "SENTINEL-" in line
            )  # managed by injection, never re-parsed
            if is_task_line and not is_sentinel_line:
                # Process previous task if exists
                if current_task_lines:
                    self._process_task(current_task_lines, task_id, current_wave_idx)
                    task_id += 1

                # Start new task
                current_task_lines = [line]
            elif is_task_line and is_sentinel_line:
                # End any open task block without processing the sentinel line
                if current_task_lines:
                    self._process_task(current_task_lines, task_id, current_wave_idx)
                    task_id += 1
                    current_task_lines = []
            elif current_task_lines and line.strip().startswith("- **Constitution**:"):
                # Add constitution line to current task
                current_task_lines.append(line)
            elif not line.strip() and current_task_lines:
                # Empty line ends task block
                self._process_task(current_task_lines, task_id, current_wave_idx)
                task_id += 1
                current_task_lines = []

        # Process final task if exists
        if current_task_lines:
            self._process_task(current_task_lines, task_id, current_wave_idx)

        # Second pass: parse any `## Dependencies` / `**Dependencies**` prose section.
        # The bullet parser above stops at empty lines, so prose-section deps
        # documented separately would otherwise be silently dropped.
        self._prose_deps = self._parse_dependency_section(content)

    def _process_task(
        self, task_lines: List[str], task_id: int, wave_idx: int = -1
    ) -> None:
        """Process a single task with its metadata.

        wave_idx: index into self._wave_phases the task belongs to, or -1 if
        no `## Wave N` header preceded this task (e.g. flat SpecKit list).
        """

        # First line is the task description
        first_line = task_lines[0]
        completed = "[x]" in first_line
        description = first_line.split("]", 1)[1].strip()

        # Full task block — used for dep extraction so sub-bullets and
        # second-line "Dependencies:" / "Requires:" hints are honored.
        full_text = "\n".join(task_lines)

        # Extract file references from description
        file_locks = self._extract_file_references(description)

        # Observability (no-black-boxes): a task whose verb clearly changes code
        # but resolves to ZERO detected files cannot be protected by file-lock
        # collision safety — it may be scheduled in parallel with a colliding
        # task and race-edit the same file. Surface it loudly rather than
        # silently treating the task as conflict-free.
        if not file_locks and re.search(self._ACTION_VERBS, description, re.IGNORECASE):
            snippet = description[:70] + ("…" if len(description) > 70 else "")
            print(
                f"⚠️  T{task_id:03d}: names no detectable file — file-lock safety "
                f"can't protect it; it may run parallel to a colliding task. "
                f"Wrap paths in backticks, e.g. `src/file.py`.  [{snippet}]",
                file=sys.stderr,
            )

        # Extract dependencies — forward verbs only ("this task needs X first").
        # Reverse verbs (blocks / before) produce edges to OTHER tasks, so they
        # go through a separate extractor + are merged in analyze_dependencies.
        dependencies = self._extract_dependencies(full_text)
        blocks_tasks = self._extract_blocks(full_text)

        # Extract constitution rules from subsequent lines
        constitution_rules = []
        full_text = "\n".join(task_lines)
        constitution_match = re.search(
            r"- \*\*Constitution\*\*: (.+)", full_text, re.MULTILINE
        )
        if constitution_match:
            rules_str = constitution_match.group(1)
            constitution_rules = [r.strip() for r in rules_str.split(",")]

        task = Task(
            id=f"T{task_id:03d}",
            description=description,
            file_locks=file_locks,
            dependencies=dependencies,
            blocks_tasks=blocks_tasks,
            constitution_rules=constitution_rules,
            completed=completed,
        )

        self.tasks.append(task)

        # Record wave membership when a `## Wave N` header has been seen.
        # Defensive guard against the (impossible-in-practice) case where a
        # wave_idx is passed but self._wave_phases hasn't been resized — we
        # silently skip the append rather than crash mid-parse.
        if 0 <= wave_idx < len(self._wave_phases):
            self._wave_phases[wave_idx].append(task.id)

        # Build file-to-task mapping
        for file in file_locks:
            self.file_to_tasks[file].append(task.id)

    # Known extensionless filenames the dot-gated regexes miss entirely
    # (no `.ext` → no match, even when backticked). Collisions on these used
    # to be undetectable. Whole-word matched, so backtick or bare both hit.
    _KNOWN_EXTENSIONLESS = (
        r"Makefile|Dockerfile|Containerfile|Procfile|Rakefile|Gemfile|"
        r"Vagrantfile|Jenkinsfile|Brewfile|CODEOWNERS|LICENSE|NOTICE"
    )

    # Verbs that signal a task actually changes code. Used by the
    # observability warning when such a task resolves to zero file locks.
    _ACTION_VERBS = (
        r"\b(?:implement|add|create|update|build|write|modify|fix|refactor|"
        r"edit|delete|remove|rename|move|wire|integrate|patch|extend|"
        r"scaffold|introduce|register|replace)\b"
    )

    def _extract_file_references(self, description: str) -> List[str]:
        """Extract file paths from a task description.

        File-lock detection is the orchestrator's ONLY signal for same-file
        collisions, so it deliberately errs toward OVER-detection: a false
        lock merely serializes two tasks (safe/slower), while a MISSED lock
        lets them run in the same wave and race-edit the file (unsafe).
        """
        import re

        # Match patterns like: file.py, path/to/file.ts, `src/component.tsx`,
        # `app.svelte` (long ext), and extensionless files like `Makefile`.
        patterns = [
            r"`([^`]+\.[a-zA-Z0-9]+)`",  # backtick-wrapped paths (any ext length)
            r"\b([\w/.-]+\.[a-zA-Z]{2,10})\b",  # bare file paths (ext 2-10 chars)
            r"\b(" + self._KNOWN_EXTENSIONLESS + r")\b",  # extensionless known files
        ]

        files = []
        for pattern in patterns:
            matches = re.findall(pattern, description)
            files.extend(matches)

        return list(set(files))  # deduplicate

    def _extract_dependencies(self, description: str) -> List[str]:
        """Extract forward dependencies ('this task needs X first').

        Recognised verbs (case-insensitive):
            after, depends on, requires, prerequisite for/of, needs
            (plus arrow forms: ->, →)

        Reverse verbs like 'blocks' and 'before' are NOT matched here — they
        produce edges to OTHER tasks and are handled by _extract_blocks().
        """
        import re

        pattern = (
            r"\b(?:after|depends\s+on|requires|needs|"
            r"prerequisite\s+(?:for|of))\s+T(\d{1,4})\b"
        )
        matches = re.findall(pattern, description, re.IGNORECASE)
        # Arrow forms: "T005 → T018" or "T005 -> T018" inside a task bullet.
        # Heuristic: arrow usually means "predecessor → current task", so if
        # T005 → appears in T018's block, T018 depends on T005.
        arrow_matches = re.findall(r"T(\d{1,4})\s*(?:->|→)", description, re.IGNORECASE)
        return [f"T{m.zfill(3)}" for m in matches + arrow_matches]

    def _extract_blocks(self, description: str) -> List[str]:
        """Extract reverse dependencies — T-IDs this task *blocks* (precedes).

        'blocks Txxx' / 'before Txxx' / 'must complete before Txxx' inside
        THIS task's block means: Txxx depends on us. analyze_dependencies()
        converts each into an edge Txxx → self.
        """
        import re

        pattern = (
            r"\b(?:blocks|before|must\s+(?:complete|be\s+done|land)\s+before|"
            r"must\s+precede|precedes)\s+T(\d{1,4})\b"
        )
        matches = re.findall(pattern, description, re.IGNORECASE)
        return [f"T{m.zfill(3)}" for m in matches]

    # ------------------------------------------------------------------
    # Symbol-graph dependency inference
    # ------------------------------------------------------------------
    # Verbs that signal a task DEFINES a symbol (class/function/Protocol).
    # Case-insensitive. Matched only when adjacent to a backticked identifier
    # to avoid flagging narrative prose.
    _DEFINER_VERBS = (
        r"(?:define|create|implement|add|build|introduce|write|"
        r"scaffold|author|establish|register|expose)"
    )
    # Optional kind-word that often follows the verb.
    _KIND_WORDS = (
        r"(?:new\s+)?"
        r"(?:class|protocol|function|method|interface|trait|struct|"
        r"enum|type|module|decorator|fixture|dataclass)?\s*"
    )
    # Regex identifying a valid Python/TS/Rust identifier inside backticks.
    # Rejects things that contain dots/slashes (file paths), * (globs), or
    # spaces. Accepts trailing () to mean "callable".
    _SYMBOL_IDENT_RE = r"([A-Za-z_][A-Za-z0-9_]*(?:\(\))?)"

    def _extract_used_symbols(self, description: str) -> Set[str]:
        """Return backticked identifiers that look like symbols, not file paths."""
        import re

        symbols: Set[str] = set()
        for raw in re.findall(r"`([^`]+)`", description):
            clean = raw.strip().rstrip("()")
            # Reject file paths, globs, version strings
            if "/" in clean or "." in clean or "*" in clean or " " in clean:
                continue
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", clean):
                continue
            # Reject single-letter and common-word false positives
            if len(clean) < 3:
                continue
            symbols.add(clean)
        return symbols

    def _extract_defined_symbols(self, description: str) -> Set[str]:
        """Return backticked symbols this task *defines* (vs. merely references).

        Trigger: a definer verb (define/create/implement/...) appears within
        ~30 characters before a backticked identifier. This conservative window
        avoids flagging unrelated backticks later in the same sentence.
        """
        import re

        pattern = re.compile(
            rf"\b{self._DEFINER_VERBS}\s+{self._KIND_WORDS}`{self._SYMBOL_IDENT_RE}`",
            re.IGNORECASE,
        )
        defined: Set[str] = set()
        for match in pattern.findall(description):
            clean = match.strip().rstrip("()")
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", clean) and len(clean) >= 3:
                defined.add(clean)
        return defined

    def _build_symbol_graph(self) -> Dict[str, Set[str]]:
        """Infer task→task edges from backticked-symbol defines/uses.

        Heuristic:
          1. For each task, collect defined-symbols (verb-gated) and
             used-symbols (any backticked identifier).
          2. First task in document order to *define* a symbol becomes its
             definer.
          3. Later tasks that *use* that symbol get an edge → definer,
             unless the user task also defined it (which would be a redefine,
             not a dependency).

        Returns: {task_id: {definer_task_id, ...}}

        False positives are safer than false negatives here — an extra edge
        serialises tasks that could have been parallel; a missing edge causes
        runtime ImportError. We accept the tradeoff.
        """
        from collections import defaultdict

        task_defines: Dict[str, Set[str]] = {}
        task_uses: Dict[str, Set[str]] = {}
        for task in self.tasks:
            task_defines[task.id] = self._extract_defined_symbols(task.description)
            task_uses[task.id] = self._extract_used_symbols(task.description)

        # First-definer wins (document order).
        symbol_definer: Dict[str, str] = {}
        for task in self.tasks:
            for sym in task_defines[task.id]:
                symbol_definer.setdefault(sym, task.id)

        edges: Dict[str, Set[str]] = defaultdict(set)
        # Precompute document order so edges only point backward.
        order = {task.id: i for i, task in enumerate(self.tasks)}
        for task in self.tasks:
            for sym in task_uses[task.id]:
                if sym in task_defines[task.id]:
                    continue  # This task defines it — not a dep on anyone.
                definer = symbol_definer.get(sym)
                if not definer or definer == task.id:
                    continue
                if order[definer] >= order[task.id]:
                    continue  # Only backward edges — avoid phantom cycles.
                edges[task.id].add(definer)
        return dict(edges)

    def _parse_dependency_section(self, content: str) -> Dict[str, List[str]]:
        """Parse `## Dependencies` / `**Dependencies**` blocks (incl. subsections).

        Returns: {task_id: [list of dep task_ids]}

        Section entry — any heading level 1-6 whose first word is "Dependencies"
        (optionally followed by trailing text like `& Execution Order`), OR a
        bold `**Dependencies**` lead-in.

        Section exit — only at a heading of the SAME OR HIGHER level than the
        one we entered on. This lets `### Within-phase dependencies` subsections
        stay inside a `## Dependencies & Execution Order` block.

        Recognised forms (anywhere in the block, optionally bullet-prefixed):

          Structured rows:
            T018 requires T005, T006
            T018 depends on T005
            T018 -> T005           /  T018 → T005
            T005 blocks T018       (reverse — T018 gets T005 as dep)
            T005 before T018       (reverse)

          Narrative (common in speckit-generated tasks.md):
            T018 must complete before T020 and before T022
            T033 must precede T035
            T018 comes before T020, T022
            T005 must be done before T018

          Arrow lists inside prose:
            T005 → T018 → T020
        """
        import re
        from collections import defaultdict

        deps: Dict[str, List[str]] = defaultdict(list)

        section_header_re = re.compile(
            r"^\s*(#{1,6})\s*Dependencies\b.*$"  # heading form
            r"|^\s*\*\*Dependencies\*\*\s*:?\s*$",  # bold form
            re.IGNORECASE,
        )
        heading_re = re.compile(r"^\s*(#{1,6})\s+\S")

        lines = content.split("\n")
        in_section = False
        entry_level = 0  # # count on the heading that opened the section

        def _record_forward(task_id_num: str, deps_blob: str) -> None:
            task_id = f"T{task_id_num.zfill(3)}"
            for d in re.findall(r"T(\d{1,4})", deps_blob):
                dep_id = f"T{d.zfill(3)}"
                if dep_id != task_id and dep_id not in deps[task_id]:
                    deps[task_id].append(dep_id)

        def _record_reverse(source_num: str, target_blob: str) -> None:
            source = f"T{source_num.zfill(3)}"
            for t in re.findall(r"T(\d{1,4})", target_blob):
                target = f"T{t.zfill(3)}"
                if source != target and source not in deps[target]:
                    deps[target].append(source)

        for line in lines:
            sh = section_header_re.match(line)
            if sh:
                in_section = True
                # Hashes captured in group 1 for heading form; bold form → 0
                hashes = sh.group(1) if sh.group(1) else ""
                entry_level = len(hashes) if hashes else 99
                continue
            if not in_section:
                continue
            # Close on heading of same-or-higher level (smaller # count)
            h = heading_re.match(line)
            if h:
                this_level = len(h.group(1))
                if this_level <= entry_level:
                    in_section = False
                    continue
                # else: subsection — keep parsing inside

            stripped = line.strip().lstrip("-*").strip()
            if not stripped:
                continue

            # --- Narrative forms (prose-friendly) ---
            # "T018 must complete before T020 and before T022"
            # "T033 must precede T035, T036"
            # "T005 must be done before T018"
            # "T018 comes before T020"
            narrative = re.match(
                r"T(\d{1,4}).*?\b(?:must\s+(?:complete|be\s+done|finish|land)\s+before"
                r"|must\s+precede"
                r"|comes\s+before"
                r"|completes\s+before"
                r"|precedes)\b(.*)$",
                stripped,
                re.IGNORECASE,
            )
            if narrative:
                source_num = narrative.group(1)
                tail = narrative.group(2)
                # Collect all T-IDs in the tail; "and before T022" adds T022.
                target_ids = re.findall(r"T(\d{1,4})", tail)
                if target_ids:
                    _record_reverse(source_num, " ".join(f"T{t}" for t in target_ids))
                    continue

            # "X must complete after Y" / "must be done after Y" → forward
            fwd_narrative = re.match(
                r"T(\d{1,4}).*?\b(?:must\s+(?:complete|be\s+done|land)\s+after"
                r"|must\s+follow)\b(.*)$",
                stripped,
                re.IGNORECASE,
            )
            if fwd_narrative:
                task_num = fwd_narrative.group(1)
                tail = fwd_narrative.group(2)
                dep_ids = re.findall(r"T(\d{1,4})", tail)
                if dep_ids:
                    _record_forward(task_num, " ".join(f"T{d}" for d in dep_ids))
                    continue

            # --- Structured forward: T<a> <verb> T<b>[, T<c>...] ---
            fwd = re.match(
                r"T(\d{1,4})\s*[:\-]?\s*"
                r"(?:requires|depends\s+on|after|needs|->|→)?\s*"
                r"((?:T\d{1,4}\s*,?\s*)+)$",
                stripped,
                re.IGNORECASE,
            )
            if fwd:
                _record_forward(fwd.group(1), fwd.group(2))
                continue

            # --- Structured reverse: T<a> blocks/before T<b>[, T<c>...] ---
            rev = re.match(
                r"T(\d{1,4})\s+(?:blocks|before)\s+((?:T\d{1,4}\s*,?\s*)+)$",
                stripped,
                re.IGNORECASE,
            )
            if rev:
                _record_reverse(rev.group(1), rev.group(2))
                continue

            # --- Arrow-chain inside prose: "T005 → T018 → T020" ---
            arrow_chain = re.findall(r"T(\d{1,4})\s*(?:->|→)\s*T(\d{1,4})", stripped)
            for left, right in arrow_chain:
                _record_forward(right, f"T{left}")

        return dict(deps)

    def _validate_dependencies(self, graph: Dict[str, Set[str]]) -> None:
        """Fail fast with a clear error when a dep references a nonexistent task.

        Without this, create_waves() deadlocks and prints the misleading
        "Circular dependency" error (orchestrator.py:266 historic).
        """
        valid_ids = {t.id for t in self.tasks}
        invalid: List[tuple] = []
        for task_id, dep_set in graph.items():
            for dep in dep_set:
                if dep not in valid_ids:
                    invalid.append((task_id, dep))
        if invalid:
            print("❌ Error: Tasks reference predecessors not found in tasks.md:")
            for task_id, dep in invalid:
                print(f"   {task_id} → {dep} (no such task)")
            print(
                "   Fix: correct the typo, add the missing task, or remove the dependency."
            )
            sys.exit(1)

    def analyze_dependencies(self) -> Dict[str, Set[str]]:
        """Build dependency graph from inline + prose-section + file-lock signals."""
        # Gap-filler (opt-in via agent-parse): BEFORE computing file-collision
        # edges, let the LLM infer file locks for prose/zero-file action tasks —
        # so dev-kid can determine parallel/sequential even when the source
        # never encoded a file path. Fallback-only; regex + symbol-graph ran first.
        if self._agent_parse:
            self._infer_missing_file_locks()
        graph = defaultdict(set)

        for task in self.tasks:
            # Explicit forward dependencies from description
            for dep in task.dependencies:
                graph[task.id].add(dep)

            # Reverse-blocks: "this task blocks Txxx" → Txxx depends on us
            for blocked in task.blocks_tasks:
                graph[blocked].add(task.id)

            # Implicit dependencies from file locks
            for file in task.file_locks:
                # Task depends on all previous tasks that touch the same file
                for other_task_id in self.file_to_tasks[file]:
                    if other_task_id != task.id:
                        # Only depend on tasks that come before in original order
                        other_idx = next(
                            i for i, t in enumerate(self.tasks) if t.id == other_task_id
                        )
                        this_idx = next(
                            i for i, t in enumerate(self.tasks) if t.id == task.id
                        )
                        if other_idx < this_idx:
                            graph[task.id].add(other_task_id)

        # Prose `## Dependencies` section deps
        for task_id, dep_ids in self._prose_deps.items():
            for dep in dep_ids:
                graph[task_id].add(dep)

        # Wave-section phase boundaries — `## Wave N` headers in tasks.md
        # establish hard dependency boundaries in lightweight mode. Every
        # task in Wave N gets an edge to every task in Waves 1..N-1.
        # Deterministic and free (no LLM call). Companion / superset of the
        # agent_dep_parser PROMPT_TEMPLATE rule #4 (phase ordering).
        # No-op when tasks.md has no wave headers (self._wave_phases empty).
        for wave_idx, task_ids in enumerate(self._wave_phases):
            if wave_idx == 0:
                continue  # Wave 1 has no upstream phase
            for tid in task_ids:
                for prior_wave in self._wave_phases[:wave_idx]:
                    for prior_tid in prior_wave:
                        if prior_tid != tid:
                            graph[tid].add(prior_tid)

        # Symbol-graph inference (Protocol/class/function defines → uses).
        # Opt-out via dev-kid.yml: orchestrator.symbol_graph: false
        if self._symbol_graph_enabled():
            for task_id, definers in self._build_symbol_graph().items():
                for definer in definers:
                    graph[task_id].add(definer)

        # Agent (LLM) dep parser — catches narrative / semantic deps that
        # regex + symbol graph miss. Opt-in via --agent-parse or dev-kid.yml.
        if self._agent_parse:
            self._merge_agent_deps(graph)

        # Validate every referenced predecessor exists — fail fast with a clear
        # message instead of letting create_waves() report "Circular dependency".
        self._validate_dependencies(graph)

        # Cache the graph so render_plan_summary() can show per-task upstream
        # deps without re-running analyze_dependencies (which has validation
        # side effects and would double-print warnings).
        self._last_dep_graph: Dict[str, Set[str]] = {
            tid: set(deps) for tid, deps in graph.items()
        }

        return graph

    def _list_project_files(self, cap: int = 400) -> List[str]:
        """Return git-tracked repo-relative file paths (capped) for LLM inference.

        Bounded to keep the prompt + cost small. Empty list if not a git repo.
        """
        import subprocess

        try:
            result = subprocess.run(
                ["git", "ls-files"],
                capture_output=True,
                text=True,
                check=False,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                files = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
                return files[:cap]
        except Exception:
            pass
        return []

    def _infer_missing_file_locks(self) -> None:
        """LLM gap-filler: infer file locks for prose/zero-file ACTION tasks.

        Closes the determination gap: a task like "refactor the login flow" names
        no file, so regex + symbol-graph find nothing and it would be scheduled
        in parallel with a colliding task. Here the LLM infers the files it likely
        touches (from the real project file list), and those become file locks so
        the existing wave/collision logic protects it. Inferred locks are LOW
        CONFIDENCE and surfaced for review. Fallback-only + bounded + Ollama-first.
        """
        candidates = [
            t
            for t in self.tasks
            if not t.completed
            and not t.file_locks
            and re.search(self._ACTION_VERBS, t.description, re.IGNORECASE)
        ]
        if not candidates:
            return

        project_files = self._list_project_files()
        if not project_files:
            return

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from agent_dep_parser import infer_files_via_agent
        except Exception as exc:
            print(f"   ⚠️  file-inference import failed: {exc}")
            return

        model, url = self._agent_parse_config()
        inferred = infer_files_via_agent(
            [(t.id, t.description) for t in candidates],
            project_files,
            model=model,
            ollama_url=url,
            valid_files=set(project_files),
        )
        if not inferred:
            return

        by_id = {t.id: t for t in self.tasks}
        n_files = 0
        n_tasks = 0
        for tid, files in inferred.items():
            task = by_id.get(tid)
            if not task:
                continue
            new = [f for f in files if f not in task.file_locks]
            if not new:
                continue
            task.file_locks.extend(new)
            for f in new:
                self.file_to_tasks[f].append(task.id)
            n_files += len(new)
            n_tasks += 1
        if n_files:
            print(
                f"   🔮 Inferred {n_files} file-lock(s) for {n_tasks} prose task(s) "
                f"via {model} (LOW-CONFIDENCE — review; wrap real paths in "
                f"backticks to make them authoritative)."
            )

    def _merge_agent_deps(self, graph: Dict[str, Set[str]]) -> None:
        """Call the LLM dep parser and merge its edges into the graph."""
        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from agent_dep_parser import extract_deps_via_agent
        except Exception as exc:
            print(f"   ⚠️  agent_dep_parser import failed: {exc}")
            return

        model, url = self._agent_parse_config()
        valid_ids = {t.id for t in self.tasks}
        agent_deps = extract_deps_via_agent(
            self.tasks_file,
            model=model,
            ollama_url=url,
            valid_task_ids=valid_ids,
        )
        # Cycle-safe merge: only add an edge if it doesn't create a backward
        # reference based on simple transitive reachability from the target.
        added = 0
        for task_id, dep_ids in agent_deps.items():
            for dep in dep_ids:
                if dep not in graph[task_id] and not self._would_create_cycle(
                    graph, task_id, dep
                ):
                    graph[task_id].add(dep)
                    added += 1
        if added:
            print(f"   ✅ Agent parser merged {added} new edge(s) into graph")

    @staticmethod
    def _would_create_cycle(
        graph: Dict[str, Set[str]], source: str, target: str
    ) -> bool:
        """Return True if adding edge source→target would close a cycle."""
        # Walk deps of target; if we reach source, adding source→target = cycle.
        seen: Set[str] = set()
        stack = [target]
        while stack:
            node = stack.pop()
            if node == source:
                return True
            if node in seen:
                continue
            seen.add(node)
            stack.extend(graph.get(node, set()))
        return False

    def _symbol_graph_enabled(self) -> bool:
        """Return True if orchestrator.symbol_graph is not explicitly disabled."""
        return self._read_yml_bool("orchestrator", "symbol_graph", default=True)

    def _agent_parse_enabled_in_yml(self) -> bool:
        """Return True if orchestrator.agent_parse: true in dev-kid.yml."""
        return self._read_yml_bool("orchestrator", "agent_parse", default=False)

    def _agent_parse_config(self) -> tuple:
        """Return (model, ollama_url) for the agent dep parser.

        Falls back to sentinel.tier1 values (they use the same Ollama host).
        """
        model = self._read_yml_value("orchestrator", "agent_parse_model") or ""
        url = self._read_yml_value("orchestrator", "agent_parse_url") or ""
        if not model:
            # Reuse sentinel tier1 model as sensible default
            model = self._read_yml_value("sentinel.tier1", "model") or "qwen3-coder:30b"
        if not url:
            url = (
                self._read_yml_value("sentinel.tier1", "ollama_url")
                or "http://localhost:11434"
            )
        return (model, url)

    def _read_yml_bool(self, section: str, key: str, default: bool = False) -> bool:
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return default
            content = yml_path.read_text(encoding="utf-8")
            in_section = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith(f"{section}:"):
                    in_section = True
                    continue
                if in_section:
                    if stripped and not line.startswith(" ") and ":" in stripped:
                        break
                    if stripped.startswith(f"{key}:"):
                        val = stripped.split(":", 1)[1].strip().lower()
                        return val not in ("false", "0", "no", "off", '""', "''")
        except Exception:
            pass
        return default

    def _read_yml_value(self, section: str, key: str) -> str:
        """Read a scalar value from a named section (supports nested 'sentinel.tier1')."""
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return ""
            content = yml_path.read_text(encoding="utf-8")
            parts = section.split(".")
            depth = 0
            for line in content.splitlines():
                stripped = line.strip()
                indent = len(line) - len(line.lstrip())
                if depth < len(parts):
                    target = parts[depth] + ":"
                    if stripped.startswith(target) and indent == depth * 2:
                        depth += 1
                        continue
                if depth == len(parts):
                    expected_indent = depth * 2
                    if (
                        indent == expected_indent
                        and stripped
                        and not stripped.startswith("#")
                        and not stripped.startswith(f"{parts[-1]}:")
                    ):
                        if not stripped[0].isalpha():
                            continue
                        if ":" in stripped and not stripped.startswith(f"{key}:"):
                            if indent < expected_indent:
                                break
                    if stripped.startswith(f"{key}:"):
                        return (
                            stripped.split(":", 1)[1]
                            .split("#")[0]
                            .strip()
                            .strip('"')
                            .strip("'")
                        )
                    if indent < expected_indent and stripped:
                        break
        except Exception:
            pass
        return ""

    def create_waves(self) -> None:
        """Group tasks into execution waves"""
        dependency_graph = self.analyze_dependencies()

        # Skip tasks already marked [x] in tasks.md — never re-execute
        pending_tasks = [t for t in self.tasks if not t.completed]
        skipped = len(self.tasks) - len(pending_tasks)
        if skipped:
            print(f"   Skipping {skipped} already-completed task(s) [x]")

        # Spec 002 audit fix #3 — refuse 100%-skip case loudly.
        # A 100%-complete tasks.md usually means "wrong file loaded" (e.g. the
        # symlink got reset to a stale spec). Failing silently with 0 waves
        # produced the user's #1 confusion event.
        # Bypass: --allow-empty (set ALLOW_EMPTY_WAVES=1 in env).
        if pending_tasks == [] and len(self.tasks) > 0:
            if os.environ.get("ALLOW_EMPTY_WAVES") != "1":
                import sys

                print()
                print(
                    "⚠️  All",
                    len(self.tasks),
                    "tasks in tasks.md are already marked [x].",
                )
                print()
                print("   This usually means ONE of:")
                print(
                    "     (a) Feature is genuinely complete — set ALLOW_EMPTY_WAVES=1 to acknowledge."
                )
                print(
                    "     (b) Wrong tasks.md is loaded — devkid resolved to a stale/wrong spec."
                )
                print()
                print("   Diagnose:")
                print(
                    "     dev-kid spec-resolve            # show which tasks.md was picked + why"
                )
                print("     ls -la tasks.md                  # check symlink target")
                print("     cat .specify/feature.json        # check speckit pointer")
                print()
                print("   Refusing to write an empty execution_plan.json. Exit 3.")
                sys.exit(3)

        # Track which tasks are assigned (seed with completed task IDs so
        # dependency resolution works correctly for remaining tasks)
        assigned_tasks = {t.id for t in self.tasks if t.completed}
        wave_id = 1

        while len(assigned_tasks) < len(self.tasks):
            # Only consider pending (incomplete) tasks for wave assignment
            remaining = [t for t in pending_tasks if t.id not in assigned_tasks]
            if not remaining:
                break
            wave_tasks = []
            wave_files = set()
            # Snapshot "assigned before this wave began". Without this,
            # sibling tasks added earlier in the same for-loop iteration
            # falsely satisfy each other's deps, flattening the wave graph.
            assigned_before_this_wave = set(assigned_tasks)

            for task in remaining:
                if task.id in assigned_tasks:
                    continue

                # Deps must be in a STRICTLY EARLIER wave, not this one.
                deps_satisfied = all(
                    dep in assigned_before_this_wave
                    for dep in dependency_graph[task.id]
                )

                if not deps_satisfied:
                    continue

                # Check file lock conflicts within this wave
                file_conflict = any(f in wave_files for f in task.file_locks)

                if file_conflict:
                    # Move to next wave
                    continue

                # Wave size cap — stop adding to this wave once we hit the limit.
                # Remaining eligible tasks will be picked up in the next wave.
                if len(wave_tasks) >= self._max_wave_size:
                    break

                # This task can be added to current wave
                wave_tasks.append(task)
                wave_files.update(task.file_locks)
                assigned_tasks.add(task.id)

            if not wave_tasks:
                # No tasks could be assigned - circular dependency or error
                print(
                    "❌ Error: Circular dependency or unresolvable conflicts detected"
                )
                sys.exit(1)

            # Determine strategy
            strategy = "PARALLEL_SWARM" if len(wave_tasks) > 1 else "SEQUENTIAL_MERGE"

            # Annotate each task with testability based on wave position
            task_dicts = []
            for t in wave_tasks:
                deps = list(dependency_graph[t.id])
                # A task is "isolated" if it has no dependencies and no
                # downstream tasks in later waves depend on its file_locks.
                # An isolated task can be tested immediately after completion.
                # A "dependent" task has upstream deps — it can be tested but
                # only after its deps are satisfied (which they are, since
                # wave assignment guarantees this).
                # "deferred" means testing should wait for downstream
                # consumers — but we don't defer by default; Claude decides.
                has_deps = len(deps) > 0
                testability = {
                    "isolated": not has_deps,
                    "has_upstream_deps": has_deps,
                    "upstream_dep_ids": deps,
                    "wave_position": wave_id,
                    "can_test_now": True,  # deps satisfied by wave ordering
                    "test_hint": (
                        "isolated-unit" if not has_deps else "integration-post-deps"
                    ),
                }
                task_dicts.append(
                    {
                        "task_id": t.id,
                        "agent_role": "Developer",
                        "instruction": t.description,
                        "file_locks": t.file_locks,
                        "constitution_rules": t.constitution_rules,
                        "testability": testability,
                        "completion_handshake": f"Upon success, update tasks.md line containing '{t.description}' to [x]",
                        "dependencies": deps,
                    }
                )

            # Create wave
            wave = Wave(
                wave_id=wave_id,
                strategy=strategy,
                tasks=task_dicts,
                rationale=f"Wave {wave_id}: {len(wave_tasks)} independent task(s) with no file conflicts",
                checkpoint_enabled=True,
            )

            self.waves.append(wave)
            wave_id += 1

    def _load_sentinel_config(self) -> bool:
        """Return True if sentinel injection is enabled via dev-kid.yml."""
        try:
            import yaml  # optional dependency
        except ImportError:
            try:
                # Minimal YAML parsing without the yaml library
                yml_path = Path("dev-kid.yml")
                if not yml_path.exists():
                    return False
                content = yml_path.read_text(encoding="utf-8")
                # Find 'enabled:' under 'sentinel:' block
                in_sentinel = False
                for line in content.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("sentinel:"):
                        in_sentinel = True
                        continue
                    if in_sentinel:
                        if stripped.startswith("enabled:"):
                            value = stripped.split(":", 1)[1].strip().lower()
                            return value not in ("false", "0", "no", "off")
                        elif (
                            stripped
                            and not stripped.startswith("#")
                            and ":" in stripped
                            and not line.startswith(" ")
                        ):
                            # New top-level key — sentinel block ended
                            break
                return False
            except Exception:
                return False

        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return False
            data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
            return bool(data.get("sentinel", {}).get("enabled", False))
        except Exception:
            return False

    def _load_sentinel_tier_info(self) -> tuple:
        """Return (tier1_model, tier1_url, tier2_model) from dev-kid.yml, with defaults."""
        defaults = (
            "qwen3-coder:30b",
            "http://localhost:11434",
            "claude-sonnet-4-20250514",
        )
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return defaults
            content = yml_path.read_text(encoding="utf-8")
            t1_model = t1_url = t2_model = None
            in_sentinel = in_tier1 = in_tier2 = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("sentinel:"):
                    in_sentinel = True
                    continue
                if in_sentinel:
                    if stripped.startswith("tier1:"):
                        in_tier1, in_tier2 = True, False
                    elif stripped.startswith("tier2:"):
                        in_tier1, in_tier2 = False, True
                    elif stripped and not line.startswith(" ") and ":" in stripped:
                        break  # left sentinel block
                    if in_tier1:
                        if stripped.startswith("model:"):
                            t1_model = stripped.split(":", 1)[1].strip()
                        elif stripped.startswith("ollama_url:"):
                            t1_url = stripped.split(":", 1)[1].strip()
                    if in_tier2 and stripped.startswith("model:"):
                        t2_model = stripped.split(":", 1)[1].strip()
            return (
                t1_model or defaults[0],
                t1_url or defaults[1],
                t2_model or defaults[2],
            )
        except Exception:
            return defaults

    def _load_sentinel_granularity(self) -> tuple:
        """Return (granularity, n) from dev-kid.yml. Defaults: ('per-task', 3)."""
        granularity = "per-task"
        n = 3
        try:
            yml_path = Path("dev-kid.yml")
            if not yml_path.exists():
                return (granularity, n)
            content = yml_path.read_text(encoding="utf-8")
            in_sentinel = False
            for line in content.splitlines():
                stripped = line.strip()
                if stripped.startswith("sentinel:"):
                    in_sentinel = True
                    continue
                if in_sentinel:
                    if stripped and not line.startswith(" ") and ":" in stripped:
                        break
                    if stripped.startswith("injection_granularity:"):
                        granularity = stripped.split(":", 1)[1].strip()
                    elif stripped.startswith("injection_n:"):
                        try:
                            n = int(stripped.split(":", 1)[1].strip())
                        except ValueError:
                            pass
        except Exception:
            pass
        return (granularity, max(1, n))

    def _inject_sentinel_tasks(self, waves: List["Wave"], tasks_file: Path) -> None:
        """Insert SENTINEL tasks according to injection_granularity in dev-kid.yml.

        Granularity modes:
          per-task : one SENTINEL after every developer task (default)
          per-wave : one SENTINEL at end of each wave (covers all tasks in wave)
          per-n    : one SENTINEL every N developer tasks within a wave

        Atomically appends matching '- [ ] SENTINEL-<id>: ...' lines to tasks.md.
        Called only when sentinel.enabled = true in dev-kid.yml.

        Args:
            waves: List of Wave objects (modified in-place).
            tasks_file: Path to tasks.md for atomic append.
        """
        granularity, n = self._load_sentinel_granularity()
        sentinel_lines_to_append: List[str] = []

        for wave in waves:
            dev_tasks = list(wave.tasks)
            injected: List[Dict] = []

            if granularity == "per-wave":
                # One sentinel at the end of the wave, covering all tasks
                injected.extend(dev_tasks)
                last_task = dev_tasks[-1]
                covered = ", ".join(t["task_id"] for t in dev_tasks)
                sentinel_id = f"SENTINEL-W{wave.wave_id}"
                sentinel_instruction = (
                    f"Sentinel validation for wave {wave.wave_id} "
                    f"({covered}): verify all implementations pass tests"
                )
                sentinel_task = {
                    "task_id": sentinel_id,
                    "agent_role": "Sentinel",
                    "instruction": sentinel_instruction,
                    "file_locks": list(last_task.get("file_locks", [])),
                    "constitution_rules": [],
                    "completion_handshake": (
                        f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                    ),
                    "dependencies": [t["task_id"] for t in dev_tasks],
                    "parent_task_id": last_task["task_id"],
                }
                injected.append(sentinel_task)
                sentinel_lines_to_append.append(
                    f"- [ ] {sentinel_id}: {sentinel_instruction}"
                )

            elif granularity == "per-n":
                # One sentinel every N developer tasks
                for i, task in enumerate(dev_tasks):
                    injected.append(task)
                    if (i + 1) % n == 0 or i == len(dev_tasks) - 1:
                        batch = dev_tasks[max(0, i + 1 - n) : i + 1]
                        covered = ", ".join(t["task_id"] for t in batch)
                        sentinel_id = f"SENTINEL-{task['task_id']}"
                        sentinel_instruction = f"Sentinel validation for {covered}: verify implementations pass tests"
                        sentinel_task = {
                            "task_id": sentinel_id,
                            "agent_role": "Sentinel",
                            "instruction": sentinel_instruction,
                            "file_locks": list(task.get("file_locks", [])),
                            "constitution_rules": [],
                            "completion_handshake": (
                                f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                            ),
                            "dependencies": [t["task_id"] for t in batch],
                            "parent_task_id": task["task_id"],
                        }
                        injected.append(sentinel_task)
                        sentinel_lines_to_append.append(
                            f"- [ ] {sentinel_id}: {sentinel_instruction}"
                        )

            else:
                # per-task (default): one SENTINEL after every developer task
                for task in dev_tasks:
                    injected.append(task)
                    sentinel_id = f"SENTINEL-{task['task_id']}"
                    sentinel_instruction = f"Sentinel validation for {task['task_id']}: verify implementation passes tests"
                    sentinel_task = {
                        "task_id": sentinel_id,
                        "agent_role": "Sentinel",
                        "instruction": sentinel_instruction,
                        "file_locks": list(task.get("file_locks", [])),
                        "constitution_rules": [],
                        "completion_handshake": (
                            f"Upon success, update tasks.md line containing '{sentinel_instruction}' to [x]"
                        ),
                        "dependencies": [task["task_id"]],
                        "parent_task_id": task["task_id"],
                    }
                    injected.append(sentinel_task)
                    sentinel_lines_to_append.append(
                        f"- [ ] {sentinel_id}: {sentinel_instruction}"
                    )

            wave.tasks = injected

        # Atomic append to tasks.md
        if sentinel_lines_to_append and tasks_file.exists():
            existing = tasks_file.read_text(encoding="utf-8")
            # Only append lines not already present
            new_lines = [
                line for line in sentinel_lines_to_append if line not in existing
            ]
            if new_lines:
                separator = "\n" if existing.endswith("\n") else "\n\n"
                updated = existing + separator + "\n".join(new_lines) + "\n"
                temp = tasks_file.with_suffix(".tmp")
                temp.write_text(updated, encoding="utf-8")
                temp.rename(tasks_file)

    def generate_execution_plan(self, phase_id: str = "default") -> Dict:
        """Generate complete execution plan in JSON schema format"""
        return {
            "execution_plan": {
                "phase_id": phase_id,
                "waves": [
                    {
                        "wave_id": wave.wave_id,
                        "strategy": wave.strategy,
                        "rationale": wave.rationale,
                        "tasks": wave.tasks,
                        "checkpoint_after": {
                            "enabled": wave.checkpoint_enabled,
                            "verification_criteria": f"Verify all Wave {wave.wave_id} tasks are marked [x] in tasks.md",
                            "git_agent": "git-version-manager",
                            "memory_bank_agent": "project-bank-keeper",
                        },
                    }
                    for wave in self.waves
                ],
            }
        }

    def render_plan_summary(
        self, *, verbose: bool = False, show_diff: bool = True
    ) -> str:
        """Human-readable summary of the parsed plan.

        Caller is responsible for having called parse_tasks(),
        analyze_dependencies(), and create_waves() first — this method is
        pure formatting over existing state.

        verbose: include per-task dep graph dump
        show_diff: include declared-vs-computed wave mapping (no-op when
                   self._wave_phases is empty — flat / SpecKit lists)
        """
        parts: List[str] = []
        parts.append(
            f"\n📋 Plan Summary — {len(self.tasks)} task(s) → "
            f"{len(self.waves)} computed wave(s)"
        )

        # Declared waves (from `## Wave N` headers in tasks.md)
        if self._wave_phases:
            non_empty_count = sum(1 for w in self._wave_phases if w)
            parts.append(
                f"\n📐 DECLARED WAVES (from `## Wave N` headers, "
                f"{non_empty_count} non-empty):"
            )
            for idx, task_ids in enumerate(self._wave_phases, 1):
                if task_ids:
                    parts.append(
                        f"   Wave {idx}: {len(task_ids)} task(s)  "
                        f"[{', '.join(task_ids)}]"
                    )

        # Computed waves (after deps + file-locks)
        parts.append("\n🌊 COMPUTED WAVES (after deps + file-locks):")
        for wave in self.waves:
            parts.append(
                f"   Wave {wave.wave_id} ({wave.strategy}, "
                f"{len(wave.tasks)} task(s)):"
            )
            for task in wave.tasks:
                instruction = task.get("instruction", "")
                trunc = (
                    instruction
                    if verbose
                    else instruction[:70] + ("…" if len(instruction) > 70 else "")
                )
                parts.append(f"      {task['task_id']}: {trunc}")

        # Declared → computed mapping (the diff users came for)
        if show_diff and self._wave_phases:
            parts.append("\n🔗 DECLARED → COMPUTED MAPPING:")
            task_to_computed = {
                t["task_id"]: w.wave_id for w in self.waves for t in w.tasks
            }
            for idx, task_ids in enumerate(self._wave_phases, 1):
                if not task_ids:
                    continue
                computed = sorted(
                    {task_to_computed[t] for t in task_ids if t in task_to_computed}
                )
                if len(computed) == 1:
                    marker = "✓ single wave"
                elif all(b - a == 1 for a, b in zip(computed, computed[1:])):
                    marker = "✓ contiguous block"
                else:
                    marker = "⚠ NON-CONTIGUOUS — deps split across phase boundary"
                parts.append(
                    f"   Declared Wave {idx} → Computed Wave(s) {computed}   {marker}"
                )

        # Per-task dep graph (verbose only)
        if verbose and getattr(self, "_last_dep_graph", None):
            parts.append("\n🧮 DEPENDENCY GRAPH (per-task upstream deps):")
            for task in self.tasks:
                deps = sorted(self._last_dep_graph.get(task.id, set()))
                if deps:
                    parts.append(f"   {task.id} ← {', '.join(deps)}")

        return "\n".join(parts)

    def execute(
        self,
        phase_id: str = "default",
        *,
        verify: bool = False,
        verify_only: bool = False,
    ) -> None:
        """Parse tasks and generate execution plan.

        verify: print full plan summary, prompt y/N, then write (or abort)
        verify_only: print full plan summary, exit BEFORE writing — pure read
        """
        print("🔍 Parsing tasks...")
        self.parse_tasks()
        print(f"   Found {len(self.tasks)} tasks")

        if not self.tasks:
            print("❌ No tasks found in tasks.md — nothing to execute.")
            print("   Add tasks in the format: - [ ] T001: Description")
            sys.exit(1)

        print("📊 Analyzing dependencies...")
        dep_graph = self.analyze_dependencies()
        total_deps = sum(len(deps) for deps in dep_graph.values())
        print(f"   Detected {total_deps} dependencies")

        print("🌊 Creating execution waves...")
        self.create_waves()
        print(f"   Organized into {len(self.waves)} waves")

        # Sentinel injection (post-wave-assignment, only if enabled)
        if self._load_sentinel_config():
            tier1_model, tier1_url, tier2_model = self._load_sentinel_tier_info()
            granularity, n = self._load_sentinel_granularity()
            granularity_label = {
                "per-task": "per-task  (SENTINEL after every task)",
                "per-wave": "per-wave  (one SENTINEL at end of each wave)",
                "per-n": f"per-{n}    (SENTINEL every {n} tasks)",
            }.get(granularity, granularity)
            print("🛡️  Integration Sentinel: ENABLED")
            print(f"   Tier 1 → micro-agent via Ollama  ({tier1_model} @ {tier1_url})")
            print(
                f"   Tier 2 → micro-agent via cloud   ({tier2_model}, on Tier 1 exhaustion)"
            )
            print(f"   Granularity: {granularity_label}")
            self._inject_sentinel_tasks(self.waves, self.tasks_file)
            sentinel_count = sum(
                1
                for w in self.waves
                for t in w.tasks
                if isinstance(t, dict) and t.get("agent_role") == "Sentinel"
            )
            print(f"   Injected {sentinel_count} SENTINEL tasks across waves")
        else:
            print("⬜ Integration Sentinel: DISABLED  (no micro-agent testing)")
            print("   Set sentinel.enabled: true in dev-kid.yml to activate.")

        plan = self.generate_execution_plan(phase_id)

        # dbt dependency ordering: if dbt_project.yml exists, override wave assignments
        if Path("dbt_project.yml").exists():
            try:
                import re as _re
                import sys as _sys

                _sys.path.insert(0, str(Path(__file__).parent))
                from dbt_graph import CycleDetector, DBTGraph, DBTTopologicalSort

                graph = DBTGraph().load(".")
                print(f"   🌿 dbt project detected — applying DAG-aware wave ordering")

                if graph.nodes:
                    cycle = CycleDetector.detect_cycle(graph)
                    if cycle:
                        print(f"   ❌ Circular dependency detected: {cycle}")
                        print(
                            "   Halting orchestration. Fix the circular ref() before proceeding."
                        )
                        _sys.exit(1)

                    def _find_dbt_model_name(
                        task_dict: dict, _graph: DBTGraph, _file_to_model: dict
                    ) -> "str | None":
                        """Find a dbt model name for a task by checking:
                        1. File locks ending in .sql — extract stem (filename without .sql)
                        2. Task instruction text — look for any word matching a known graph node
                        """
                        # Check file locks for .sql paths
                        for fl in task_dict.get("file_locks", []):
                            # Direct file_path → model lookup from manifest/regex data
                            model_name = _file_to_model.get(fl)
                            if model_name:
                                return model_name
                            # Stem-based fallback: models/stg_orders.sql → stg_orders
                            if fl.endswith(".sql"):
                                stem = Path(fl).stem
                                if stem in _graph.nodes:
                                    return stem
                        # Check instruction text for known model names
                        instruction = task_dict.get("instruction", "")
                        words = _re.findall(r"\b\w+\b", instruction.lower())
                        for word in words:
                            if word in _graph.nodes:
                                return word
                        return None

                    # Map file_path → model_name for tasks in the plan
                    file_to_model = graph.get_file_to_model_map()
                    task_model_names: list[str] = []
                    task_to_model: dict[str, str] = {}
                    for wave in plan["execution_plan"]["waves"]:
                        for task in wave["tasks"]:
                            model_name = _find_dbt_model_name(
                                task, graph, file_to_model
                            )
                            if model_name and task["task_id"] not in task_to_model:
                                task_model_names.append(model_name)
                                task_to_model[task["task_id"]] = model_name

                    print(f"   📊 {len(task_model_names)} dbt model task(s) identified")

                    if task_model_names:
                        wave_overrides = DBTTopologicalSort.assign_waves(
                            task_model_names, graph
                        )

                        # Snapshot original wave assignments for non-dbt tasks
                        task_id_to_orig_wave: dict[str, int] = {}
                        for orig_wave in plan["execution_plan"]["waves"]:
                            for task in orig_wave["tasks"]:
                                task_id_to_orig_wave[task["task_id"]] = orig_wave[
                                    "wave_id"
                                ]

                        # Collect all tasks by id for rebuild
                        all_tasks_by_id: dict[str, dict] = {}
                        for orig_wave in plan["execution_plan"]["waves"]:
                            for task in orig_wave["tasks"]:
                                all_tasks_by_id[task["task_id"]] = task

                        new_waves_by_num: dict[int, list] = {}
                        for task_id, task in all_tasks_by_id.items():
                            model = task_to_model.get(task_id)
                            if model:
                                # dbt task: use DAG-derived wave number
                                wave_num = wave_overrides.get(model, 1)
                            else:
                                # Non-dbt task: preserve original file-lock-derived wave
                                wave_num = task_id_to_orig_wave.get(task_id, 1)
                            new_waves_by_num.setdefault(wave_num, []).append(task)

                        if new_waves_by_num:
                            max_wave = max(new_waves_by_num.keys())
                            new_waves = []
                            for wid in range(1, max_wave + 1):
                                tasks_in_wave = new_waves_by_num.get(wid, [])
                                if not tasks_in_wave:
                                    continue
                                # Determine strategy: SEQUENTIAL_MERGE if any file lock
                                # conflicts exist within this wave, else PARALLEL_SWARM
                                wave_file_locks: set[str] = set()
                                has_conflict = False
                                for wt in tasks_in_wave:
                                    for fl in wt.get("file_locks", []):
                                        if fl in wave_file_locks:
                                            has_conflict = True
                                            break
                                        wave_file_locks.add(fl)
                                    if has_conflict:
                                        break
                                if has_conflict or len(tasks_in_wave) == 1:
                                    strategy = "SEQUENTIAL_MERGE"
                                else:
                                    strategy = "PARALLEL_SWARM"
                                new_waves.append(
                                    {
                                        "wave_id": wid,
                                        "strategy": strategy,
                                        "rationale": f"dbt dependency-ordered wave {wid}",
                                        "tasks": tasks_in_wave,
                                        "checkpoint_after": {
                                            "enabled": True,
                                            "verification_criteria": f"Verify all Wave {wid} tasks are marked [x] in tasks.md",
                                            "git_agent": "git-version-manager",
                                            "memory_bank_agent": "project-bank-keeper",
                                        },
                                    }
                                )
                            plan["execution_plan"]["waves"] = new_waves
                            print(
                                f"   dbt DAG applied: {len(task_model_names)} model(s) reordered across {len(new_waves)} wave(s)"
                            )
            except SystemExit:
                raise
            except Exception as _dbt_err:
                print(f"   ⚠️  dbt wave ordering failed (non-fatal): {_dbt_err}")

        # Verifier output (Track B): print the full plan BEFORE writing.
        # verify_only = pure-read preview, never writes execution_plan.json.
        # verify     = preview then prompt y/N before writing.
        if verify or verify_only:
            print(self.render_plan_summary(verbose=True, show_diff=True))
            if verify_only:
                print(
                    "\n📜 verify-only mode — execution_plan.json NOT written. "
                    "Re-run without --verify-only (or with --verify) to apply."
                )
                return
            # verify mode — gate the write on user confirmation
            print(
                "\nWrite execution_plan.json and finalize this plan? [y/N]: ",
                end="",
                flush=True,
            )
            try:
                answer = sys.stdin.readline().strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = ""
            if answer not in ("y", "yes"):
                print("Aborted — execution_plan.json NOT written.")
                return

        # Output to execution_plan.json (atomic write)
        output_file = Path("execution_plan.json")
        temp_file = output_file.with_suffix(".tmp")
        try:
            temp_file.write_text(json.dumps(plan, indent=2), encoding="utf-8")
            temp_file.rename(output_file)  # Atomic on POSIX
            print(f"✅ Execution plan written to: {output_file}")
        except Exception as e:
            print(f"❌ Error writing execution plan: {e}")
            if temp_file.exists():
                temp_file.unlink()
            sys.exit(1)

        # Brief summary (always-on at end of orchestrate — preserved from
        # pre-Track-B behavior so existing tooling parsing this output works).
        print("\n📋 Wave Summary:")
        for wave in self.waves:
            print(
                f"   Wave {wave.wave_id} ({wave.strategy}): {len(wave.tasks)} task(s)"
            )
            for task in wave.tasks:
                print(f"      - {task['task_id']}: {task['instruction'][:60]}...")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Task Orchestrator - Wave-based parallel execution"
    )
    parser.add_argument(
        "--tasks-file", default="tasks.md", help="Path to tasks.md file"
    )
    parser.add_argument("--phase-id", default="default", help="Phase identifier")
    parser.add_argument(
        "--agent-parse",
        action="store_true",
        help="Enable LLM-backed dep extraction (Ollama). "
        "Slower, but catches narrative deps regex misses. "
        "Opt-in via dev-kid.yml: orchestrator.agent_parse: true",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Print the full plan (declared waves, computed waves, "
        "declared→computed mapping, dep graph) and prompt y/N before "
        "writing execution_plan.json.",
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Print the full plan and EXIT WITHOUT writing "
        "execution_plan.json. Pure-read preview, like `dev-kid spec-resolve` "
        "but covering deps + wave grouping.",
    )

    args = parser.parse_args()

    if args.verify and args.verify_only:
        print(
            "❌ --verify and --verify-only are mutually exclusive. "
            "Use --verify-only for a pure preview, --verify to preview + "
            "prompt-then-write."
        )
        sys.exit(2)

    orchestrator = TaskOrchestrator(args.tasks_file, agent_parse=args.agent_parse)
    orchestrator.execute(
        args.phase_id, verify=args.verify, verify_only=args.verify_only
    )


if __name__ == "__main__":
    main()
