#!/usr/bin/env python3
"""
LLM-backed dependency parser for tasks.md.

Sends tasks.md to a local Ollama model and asks for a structured JSON
dependency graph. Complements the regex-based parser in orchestrator.py
by catching narrative / semantic deps that regex can't express:

  - "T018 (DynamicPromptGenerator impl) is exercised by the integration test
    in T022"  →  T022 requires T018
  - "Once T043 lands, the pre-existing tests in T044–T046 will run against
    the shim path"  →  T044/T045/T046 require T043
  - Phase-ordering where all tasks in Phase N+1 inherit deps on all tasks
    in Phase N

Output schema (strict JSON):
    {
      "edges": [
        {"from": "T018", "to": "T005", "reason": "T018 imports Protocol from T005"}
      ]
    }

Convention: "from" DEPENDS ON "to" (the `from` task needs the `to` task first).

Cache:
    Results are cached at `.claude/deps-cache.json` keyed on tasks.md mtime.
    Subsequent runs within the same edit window skip the LLM call.

Usage (standalone):
    python3 cli/agent_dep_parser.py --tasks-file tasks.md
    python3 cli/agent_dep_parser.py --tasks-file tasks.md --model qwen3-coder:30b

Usage (library, called from orchestrator.py):
    from agent_dep_parser import extract_deps_via_agent
    deps = extract_deps_via_agent(tasks_file, model=..., ollama_url=...)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen3-coder:30b"
DEFAULT_TIMEOUT_SEC = 180

# Provider prefixes match ralph-tiers.json convention: "provider/model_name".
# Bare model names (no "/") default to Ollama for backward compatibility.
SUPPORTED_PROVIDERS = ("ollama", "openai", "google", "gemini", "anthropic")

PROMPT_TEMPLATE = """You are a task-dependency extractor for a software project's tasks.md.

Given the tasks.md content below, extract every task-to-task dependency you \
can infer from the text. Look at:

1. EXPLICIT phrasing: "T018 requires T005", "blocks T021", "must complete \
before T020", "after T004", "depends on T005", "T005 → T018".
2. SYMBOL imports: if one task defines a class/Protocol/function (via verbs \
like "Implement", "Define", "Create", "Add", "Scaffold") and a later task \
imports or exercises that same symbol, emit an edge.
3. TEST→IMPL ordering: a test task that exercises behaviour introduced by \
another task depends on that task if test-first-fail-first convention is \
used; otherwise the impl depends on the test. Look at surrounding prose to \
decide — default to TEST→IMPL (test written first, fails, then impl fixes).
4. PHASE ordering: if prose says "Phase N depends on Phase M", emit one edge \
from each Phase-N task to the LAST task of Phase M (the phase-gate task). \
Don't fan out to every upstream task — just the gate.
5. INTEGRATION / end-to-end tests: if a task is described as an integration \
or e2e test exercising multiple prior tasks, emit one edge per prior task it \
exercises.

Rules:
- Output ONLY valid JSON in the exact schema below. No prose. No markdown fences.
- Every "from" and "to" MUST be a T-ID that appears in tasks.md.
- Do NOT emit self-edges (from == to).
- Do NOT emit duplicate edges.
- Skip SENTINEL-* tasks entirely (they're managed separately).
- If confidence is low, omit the edge rather than guessing.

Schema:
{{"edges": [{{"from": "T018", "to": "T005", "reason": "..."}}]}}

Convention: "from" DEPENDS ON "to" (the from task needs the to task first).

TASKS.MD:
```
{tasks_content}
```

JSON output:
"""


def _normalize_tid(tid: str) -> str:
    """Normalize 'T1', 't018', ' T5 ' → 'T001'. Returns '' on failure."""
    if not tid:
        return ""
    m = re.match(r"T(\d{1,4})\s*$", str(tid).strip().upper())
    if not m:
        return ""
    return f"T{m.group(1).zfill(3)}"


def _http_post_json(url: str, payload: dict, headers: dict, timeout: int) -> dict:
    """Shared HTTP POST helper. Returns parsed JSON body or raises RuntimeError."""
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8")[:400]
        except Exception:
            pass
        raise RuntimeError(
            f"HTTP {exc.code} from {url}: {detail or exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Cannot reach {url}: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {exc}") from exc


def query_ollama(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """POST to Ollama /api/generate."""
    data = _http_post_json(
        f"{ollama_url.rstrip('/')}/api/generate",
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_ctx": 16384},
        },
        {"Content-Type": "application/json"},
        timeout,
    )
    return data.get("response", "")


def query_openai(
    prompt: str,
    model: str = "gpt-4o-mini",
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """POST to OpenAI /v1/chat/completions. Requires OPENAI_API_KEY env var."""
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENAI_API_KEY not set")
    data = _http_post_json(
        "https://api.openai.com/v1/chat/completions",
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        timeout,
    )
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def query_gemini(
    prompt: str,
    model: str = "gemini-2.5-flash",
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """POST to Gemini /v1beta/models/{model}:generateContent.

    Requires GOOGLE_API_KEY or GEMINI_API_KEY env var.
    """
    key = (
        os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
    )
    if not key:
        raise RuntimeError("GOOGLE_API_KEY / GEMINI_API_KEY not set")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    data = _http_post_json(
        url,
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        },
        {"Content-Type": "application/json"},
        timeout,
    )
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def query_anthropic(
    prompt: str,
    model: str = "claude-haiku-4-5-20251001",
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """POST to Anthropic /v1/messages. Requires ANTHROPIC_API_KEY env var."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")
    data = _http_post_json(
        "https://api.anthropic.com/v1/messages",
        {
            "model": model,
            "max_tokens": 4096,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        },
        {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        timeout,
    )
    try:
        return data["content"][0]["text"] or ""
    except (KeyError, IndexError, TypeError):
        return ""


def query_model(
    prompt: str,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = DEFAULT_TIMEOUT_SEC,
) -> str:
    """Dispatch to the right provider based on model prefix.

    Recognised prefixes: ollama/, openai/, google/, gemini/, anthropic/.
    Bare model names (no "/") default to Ollama for backwards compatibility.
    """
    if "/" in model:
        provider, model_name = model.split("/", 1)
        provider = provider.lower()
    else:
        provider, model_name = "ollama", model

    if provider == "ollama":
        return query_ollama(prompt, model_name, ollama_url, timeout)
    if provider == "openai":
        return query_openai(prompt, model_name, timeout)
    if provider in ("google", "gemini"):
        return query_gemini(prompt, model_name, timeout)
    if provider == "anthropic":
        return query_anthropic(prompt, model_name, timeout)
    raise RuntimeError(
        f"Unknown provider '{provider}' — supported: {', '.join(SUPPORTED_PROVIDERS)}"
    )


def parse_agent_output(response: str) -> Dict[str, List[str]]:
    """Extract edges from LLM output. Tolerant of markdown fences + trailing text.

    Returns a {task_id: [dep_ids]} mapping. Invalid/malformed edges are skipped.
    """
    if not response:
        return {}

    cleaned = response.strip()

    # Strip leading ```json / ``` fences
    fence_re = re.compile(r"^```(?:json)?\s*\n?", re.IGNORECASE)
    cleaned = fence_re.sub("", cleaned, count=1)
    if cleaned.rstrip().endswith("```"):
        cleaned = cleaned.rstrip()[:-3].rstrip()

    # Fall back: grab the outermost {...} block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start < 0 or end < 0 or end <= start:
        return {}
    blob = cleaned[start : end + 1]

    try:
        data = json.loads(blob)
    except json.JSONDecodeError:
        # Try a cleanup pass for common LLM mistakes (trailing comma etc.)
        blob2 = re.sub(r",\s*([}\]])", r"\1", blob)
        try:
            data = json.loads(blob2)
        except json.JSONDecodeError:
            return {}

    deps: Dict[str, List[str]] = {}
    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        frm = _normalize_tid(edge.get("from", ""))
        to = _normalize_tid(edge.get("to", ""))
        if not frm or not to or frm == to:
            continue
        deps.setdefault(frm, [])
        if to not in deps[frm]:
            deps[frm].append(to)
    return deps


def _cache_path(project_root: Path = None) -> Path:
    root = Path(project_root) if project_root else Path.cwd()
    return root / ".claude" / "deps-cache.json"


def extract_deps_via_agent(
    tasks_file: Path,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    timeout: int = DEFAULT_TIMEOUT_SEC,
    project_root: Optional[Path] = None,
    use_cache: bool = True,
    valid_task_ids: Optional[set] = None,
) -> Dict[str, List[str]]:
    """Main entry point — returns agent-inferred deps for tasks_file.

    Args:
        tasks_file: path to tasks.md
        model: Ollama model name
        ollama_url: Ollama HTTP endpoint
        timeout: request timeout seconds
        project_root: project root for cache path (default: cwd)
        use_cache: if True and cache is fresh, skip the LLM call
        valid_task_ids: if provided, filter edges referencing unknown T-IDs

    Returns:
        {task_id: [dep_task_ids, ...]}
    """
    tasks_file = Path(tasks_file)
    if not tasks_file.exists():
        print(f"   ⚠️  Agent parser: {tasks_file} does not exist")
        return {}

    try:
        mtime = tasks_file.stat().st_mtime
    except OSError:
        mtime = 0.0

    cache_path = _cache_path(project_root)

    if use_cache and cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
            if (
                cache.get("file") == str(tasks_file)
                and cache.get("mtime") == mtime
                and cache.get("model") == model
            ):
                cached_deps = cache.get("deps", {})
                if cached_deps:
                    edges = sum(len(v) for v in cached_deps.values())
                    print(
                        f"   🤖 Agent parser: {edges} edge(s) from cache "
                        f"(tasks.md unchanged since last run)"
                    )
                    return cached_deps
        except Exception:
            pass

    try:
        content = tasks_file.read_text(encoding="utf-8")
    except Exception as exc:
        print(f"   ⚠️  Agent parser read error: {exc}")
        return {}

    provider_hint = model.split("/", 1)[0] if "/" in model else "ollama"
    where = ollama_url if provider_hint == "ollama" else provider_hint
    print(f"   🤖 Agent parser: calling {model} (@ {where})")
    prompt = PROMPT_TEMPLATE.format(tasks_content=content)

    try:
        response = query_model(
            prompt, model=model, ollama_url=ollama_url, timeout=timeout
        )
    except Exception as exc:
        print(f"   ⚠️  Agent parser LLM call failed: {exc}")
        print("   ℹ️  Orchestration continues with regex-only parser")
        return {}

    deps = parse_agent_output(response)

    if valid_task_ids is not None:
        filtered: Dict[str, List[str]] = {}
        for task_id, dep_ids in deps.items():
            if task_id not in valid_task_ids:
                continue
            kept = [d for d in dep_ids if d in valid_task_ids]
            if kept:
                filtered[task_id] = kept
        dropped = sum(len(v) for v in deps.values()) - sum(
            len(v) for v in filtered.values()
        )
        if dropped:
            print(
                f"   ℹ️  Agent parser: dropped {dropped} edge(s) referencing unknown task IDs"
            )
        deps = filtered

    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps(
                {
                    "file": str(tasks_file),
                    "mtime": mtime,
                    "model": model,
                    "deps": deps,
                    "raw_response_preview": response[:5000],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
    except Exception as exc:
        print(f"   ⚠️  Agent parser cache write failed (non-fatal): {exc}")

    edges = sum(len(v) for v in deps.values())
    print(f"   📊 Agent parser: extracted {edges} edge(s) across {len(deps)} task(s)")
    return deps


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="agent_dep_parser",
        description="LLM-backed dependency extractor for tasks.md (standalone).",
    )
    parser.add_argument("--tasks-file", default="tasks.md")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument(
        "--no-cache", action="store_true", help="Ignore cache, force fresh LLM call"
    )
    parser.add_argument(
        "--print-raw", action="store_true", help="Dump raw LLM response after parsing"
    )
    args = parser.parse_args()

    deps = extract_deps_via_agent(
        Path(args.tasks_file),
        model=args.model,
        ollama_url=args.ollama_url,
        timeout=args.timeout,
        use_cache=not args.no_cache,
    )

    print(
        json.dumps(
            {"edges": [{"from": k, "to": v} for k, vs in deps.items() for v in vs]},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
