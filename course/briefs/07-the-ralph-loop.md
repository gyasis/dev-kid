# Module 7: The Ralph Loop — micro-agent as the Engine (high-level + the heart)

### Teaching Arc
- **Metaphor:** A **persistent apprentice locksmith.** You don't hand them the finished key — you hand them the lock (the test) and say "keep filing until it turns." They try, test, learn, try again, escalating to a master locksmith only if they're stuck. (No restaurant.)
- **Opening hook:** "Step 3 of the Sentinel said 'run a test-fix loop.' That loop has a name — the **Ralph Loop** — and it IS micro-agent. This is the engine that actually *writes the fix*."
- **Key insight:** The Ralph Loop runs an agent in a cycle — generate → run the test → if red, learn and retry — until the test passes or a budget runs out. micro-agent's `ma-loop` runs three roles (Librarian → Artisan → Critic), can start in a cheap **simple** mode then **escalate to full**, and supports an N-tier model ladder via `--tier-config`.
- **"Why should I care?":** This is the single most powerful idea in the system: *you describe success as a test, and an AI loops until it's true.* Knowing this lets you frame work to AI as "make this test pass," which is far more reliable than "write this code."

### Code Snippets (pre-extracted)

File: micro-agent src/cli/ralph-loop.ts — the `ma-loop run` command's real options (lines ~33-84)
```ts
program
  .command('run')
  .description('Run Ralph Loop iterations for a file or objective')
  .argument('<target>', 'Target file or objective to achieve')
  .option('-o, --objective <text>', 'Explicit objective')
  .option('-t, --test <command>', 'Test command to run (e.g., "npm test")')
  .option('-i, --max-iterations <n>', 'Maximum iterations', '30')
  .option('-b, --max-budget <n>', 'Maximum cost in USD', '2.00')
  .option('--simple [n]', 'Run simple mode (Artisan+Tests) for N iters before escalating')
  .option('--full', 'Skip simple mode — Librarian→Artisan→Critic→Tests from iteration 1')
  .option('--tier-config <path>', 'JSON tier config — enables N-tier escalation mode')
```

The three roles (teach as characters):
- **Librarian** — gathers context/research before the fix.
- **Artisan** — writes the actual code change.
- **Critic** — reviews the change before tests run.

### Interactive Elements
- [x] **Group chat animation** — the hero. Actors: Librarian, Artisan, Critic, Test. Flow: Test "still red"; Librarian "here's the relevant context"; Artisan "patch v2"; Critic "looks safe, ship to test"; Test "🟢 green!" → loop exits.
- [x] **Code↔English translation** — the `ma-loop run` options: explain `<target>` (the file OR objective), `--test` (how it knows it's done), `--max-iterations` / `--max-budget` (the stop conditions), and `--tier-config` (escalate to stronger models). Crucially note: this is the **`ma-loop`** binary, not `micro-agent`.
- [x] **Quiz** — 3 Qs. e.g. "What makes the loop *stop*?" (test passes OR budget/iterations hit) "Why is 'describe success as a test' more reliable than 'write the code'?" "Simple mode runs 5 iterations then escalates — why start cheap?"
- [x] **Callout** — "aha!": the Ralph Loop turns *verification* (a test) into the *spec*. The test is the prompt.

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Inside the Sentinel" (step 3 = the test loop).
- **Next module:** "Tiers & the Money Guard" — how the loop escalates models without burning cash.
- **Tone/style notes:** Vermillion. Emphasize the binary name **`ma-loop`** (vs `micro-agent`) — it's the crux of Module 9. Tooltip: iteration, budget, escalation, tier, agent role, test command.
