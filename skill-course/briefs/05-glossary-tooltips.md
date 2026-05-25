# Module 5: The Glossary Tooltip Engine (element deep-dive)

### Teaching Arc
- **Metaphor:** **Museum placards on a movable arm.** The placard floats out exactly where you're looking — and crucially, it's mounted on the *ceiling rail* (the page body), not bolted inside the display case, so the case's glass walls can never crop it. (No restaurant.)
- **Opening hook:** "Hover any dashed word in this course and a definition pops up — even inside a dark code block that 'hides' its overflow. That's a deliberate trick."
- **Key insight:** A term is just `<span class="term" data-definition="...">`. The engine builds the tooltip in JS, appends it to `document.body` (NOT inside the term), and positions it with `position: fixed` + `getBoundingClientRect()`. That's what stops `overflow: hidden` ancestors (like code blocks) from clipping it; it also flips below the word if there's no room above.
- **"Why should I care?":** This is the difference between a course that *claims* to be beginner-friendly and one that *is* — and a masterclass in the classic "my popup keeps getting cut off" bug, which you'll now know how to diagnose.

### Code Snippets (pre-extracted)

File: a term in the HTML (all an author writes)
```html
<span class="term" data-definition="A background script that runs even when you're not looking at the page.">service worker</span>
```

File: main.js — positioning that escapes clipping (lines ~116-132)
```javascript
function positionTooltip(term, tip) {
  const rect = term.getBoundingClientRect();
  const tipWidth = Math.min(320, Math.max(200, window.innerWidth * 0.8));
  let left = rect.left + rect.width / 2 - tipWidth / 2;
  left = Math.max(8, Math.min(left, window.innerWidth - tipWidth - 8));
  tip.style.left = left + 'px';
  document.body.appendChild(tip);          // ← appended to BODY, not the term
  const tipHeight = tip.offsetHeight;
  if (rect.top - tipHeight - 12 < 0) {     // no room above → flip below
    tip.style.top = (rect.bottom + 8) + 'px';
    tip.classList.add('flip');
  } else {
    tip.style.top = (rect.top - tipHeight - 8) + 'px';
  }
}
```

(CSS note worth quoting: `.term-tooltip { position: fixed; z-index: 10000; }` — fixed, not absolute.)

### Interactive Elements
- [x] **LIVE demonstration** — the module text itself should be DENSE with `.term` tooltips so the reader experiences the engine while learning it. Call this out explicitly ("the word you just hovered used this exact code").
- [x] **Code↔English translation** — `positionTooltip`: explain `getBoundingClientRect` (where is this word on screen, right now?), why `document.body.appendChild` dodges clipping, and the flip-if-no-room-above logic.
- [x] **Spot-the-bug challenge** — show a broken version that appends the tooltip *inside* the `.term` (or uses `position: absolute` within a `overflow:hidden` code block); the learner clicks the line that causes clipping. Explanation: must append to body + position:fixed.
- [x] **Quiz** — 3 Qs, debugging. e.g. "Your tooltip gets cut off inside a scrolling box — what's the fix?" (append to body, position:fixed) "Why `cursor: pointer` and not `cursor: help` on terms?" (inviting/clickable).
- [x] **Callout** — "aha!": 'append to body + fixed positioning' is THE universal escape hatch for popups trapped by `overflow: hidden`.

### Reference Files to Read
- `references/interactive-elements.md` → "Glossary Tooltips", "Spot the Bug Challenge", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Navigation & Reveal."
- **Next module:** "The Quiz Family" — the interactive-check engines.
- **Tone/style notes:** TEAL accent (global). Odd module → alternating background. Be EXTRA generous with live tooltips here (the medium is the message). Tooltip: getBoundingClientRect, position fixed vs absolute, overflow hidden, z-index, DOM, append.
