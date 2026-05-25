# Module 4: The Navigation & Reveal Engine (element deep-dive)

### Teaching Arc
- **Metaphor:** A **guided gallery tour** with a "you-are-here" dot that slides along a map, and spotlights that click on the moment you step into each room. Nothing is lit until you arrive — that's what keeps the space calm. (No restaurant.)
- **Opening hook:** "As you scroll, the top bar fills, dots light up, and content fades in right on cue. None of that is magic — it's one small file watching your scroll position."
- **Key insight:** `main.js` reads scroll position to drive the progress bar + nav dots (active vs visited), uses an **IntersectionObserver** to add `.visible` to any `.animate-in` element when it enters view (reveal-on-scroll), and maps arrow keys to module jumps.
- **"Why should I care?":** "Scrollytelling" is everywhere (news features, product pages). Knowing it's just *scroll position → class changes* demystifies it — and lets you ask AI for it precisely ("reveal each section on scroll with an IntersectionObserver").

### Code Snippets (pre-extracted)

File: main.js — reveal-on-scroll (lines ~95-104)
```javascript
const revealObserver = new IntersectionObserver(entries => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible');
      revealObserver.unobserve(entry.target);
    }
  });
}, { rootMargin: '0px 0px -8% 0px', threshold: 0.08 });

$$('.animate-in').forEach(el => revealObserver.observe(el));
```

File: main.js — which nav dot is "active" vs "visited" (lines ~41-58)
```javascript
function updateNavDots() {
  const scrollMid = window.scrollY + window.innerHeight / 2;
  modules.forEach((mod, i) => {
    const dot = navDots[i];
    const top = mod.offsetTop, bottom = top + mod.offsetHeight;
    if (scrollMid >= top && scrollMid < bottom) { dot.classList.add('active'); }
    else if (window.scrollY + window.innerHeight > top) { dot.classList.add('visited'); }
  });
}
```

### Interactive Elements
- [x] **Data flow / step animation** — the hero: "you scroll" → observer notices an element crossed the threshold → adds `.visible` → CSS fades it in. Show the trigger→class→animation chain.
- [x] **Code↔English translation** — the IntersectionObserver: explain "observer" (a watcher that fires when an element enters the screen), `isIntersecting` (it's now visible), and `unobserve` (stop watching once revealed — do it once).
- [x] **Quiz** — 3 Qs. e.g. "Content only animates in the FIRST time you scroll to it — which line makes it one-time?" (`unobserve`) "What drives the nav dot turning teal?" (scroll midpoint inside the module).
- [x] **Callout** — "aha!": the page doesn't 'know' what scrolling means — it just reacts to the browser reporting positions. Reactivity = watch a value, change a class.

### Reference Files to Read
- `references/interactive-elements.md` → "Message Flow / Data Flow Animation", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Briefs & Parallel Agents."
- **Next module:** "Glossary Tooltips" — the cleverest small engine in the file.
- **Tone/style notes:** TEAL accent (global). This begins the element-by-element deep-dive arc (Modules 4-9). Even module → alternating background. Tooltip: IntersectionObserver, threshold, viewport, class, scroll position, reactivity.
