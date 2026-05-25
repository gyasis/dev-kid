# Module 8: The Flow Animation Engine (element deep-dive)

### Teaching Arc
- **Metaphor:** A **subway line map.** Each station lights up as the train reaches it, and a little dot glides along the track between stops. The route is printed on the map (the steps); the engine just walks it. (No restaurant.)
- **Opening hook:** "The step-by-step data-flow diagrams — the ones where boxes light up and a dot flies between them — are driven by a tiny JSON 'route' baked into one attribute."
- **Key insight:** A `data-steps` JSON array is the script. Each step can `highlight` an actor (looked up **scoped to the container**) and optionally fly a `packet` `from`/`to` (coordinates computed with `getBoundingClientRect` relative to the container). One famous gotcha: a single apostrophe inside a label silently breaks the whole JSON.
- **"Why should I care?":** It's a clean example of *data-driven animation* — and the apostrophe trap + the duplicate-id pitfall are exactly the kind of silent bugs that teach you to suspect the data, not the engine.

### Code Snippets (pre-extracted)

File: flow HTML — the route lives in one attribute
```html
<div class="flow-animation" data-steps='[
  {"highlight":"flow-actor-1","label":"User clicks the button"},
  {"highlight":"flow-actor-2","label":"Backend calls the DB","packet":true,"from":"actor-2","to":"actor-3"}
]'>
  <div class="flow-actor" id="flow-actor-1">...</div>
  <div class="flow-packet" id="flow-packet"></div>
</div>
```

File: main.js — advancing one step (lines ~424-436)
```javascript
function next() {
  const s = stepsData[step];
  $$('.flow-actor', containerEl).forEach(a => a.classList.remove('active'));
  if (s.highlight) {
    const hEl = $('#' + s.highlight, containerEl) || $('#flow-' + s.highlight);
    if (hEl) hEl.classList.add('active');           // ← scoped to THIS flow
  }
  if (s.packet && s.from && s.to) animatePacket('flow-' + s.from, 'flow-' + s.to);
  step++;
}
```

The gotchas worth teaching (from the skill's own warnings + a real fix in the sibling course):
- A `'` inside a label ends the `data-steps='...'` attribute early → `JSON.parse` fails silently. Use `&apos;`.
- If two flow animations on one page reuse `flow-actor-1` etc., a *global* id lookup grabs the first one — the packet flies to the wrong place. Fix: scope the lookup to the container.

### Interactive Elements
- [x] **LIVE flow animation** — the hero: a working multi-step flow (e.g., the whole skill pipeline) the reader steps through. Unique actor ids within the container; `data-steps` with apostrophes escaped as `&apos;`.
- [x] **Code↔English translation** — `next()`: explain `data-steps` (a list of steps as data), "highlight" (light up a box), and the scoped lookup `$('#id', containerEl)` (find it *inside this animation*, not the whole page).
- [x] **Spot-the-bug challenge** — show a `data-steps` with a raw apostrophe in a label (or a packet using a duplicated global id); learner clicks the offending line. Explanation: the JSON terminates early / the wrong element is found.
- [x] **Quiz** — 3 Qs, debugging. e.g. "Your flow animation does nothing and the console shows a JSON error — first suspect?" (an apostrophe in a label) "Two flows on a page; the second's packet flies off-screen — why?" (duplicate ids + global lookup).
- [x] **Callout** — "aha!": data-driven animation — change the JSON, change the show; the engine never changes.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Spot the Bug Challenge", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Group Chat Engine."
- **Next module:** "The Visual Family" — the mostly-CSS structured elements.
- **Tone/style notes:** TEAL accent (global). Even module → alternating background. CRITICAL: the live flow's own `data-steps` must have apostrophes escaped as `&apos;` or it won't run (practice what you preach). Tooltip: JSON, JSON.parse, attribute delimiter, getBoundingClientRect, scoped vs global lookup, id.
