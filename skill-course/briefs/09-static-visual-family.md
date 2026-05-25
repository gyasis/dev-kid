# Module 9: The Visual Family — Structure Over Prose (element deep-dive)

### Teaching Arc
- **Metaphor:** **Gallery fixtures.** Pedestals, wall labels, dioramas, and display cases — a kit of ways to present an artifact so visitors *scan* instead of *read*. Most need no electricity (CSS only); a couple have a single switch (a sliver of JS). (No restaurant.)
- **Opening hook:** "Not every element animates. The course's secret weapon is a family of *structured visuals* that replace paragraphs — file trees, cards, badges, step lists — mostly pure CSS."
- **Key insight:** This family converts text into scannable structure. Most are HTML+CSS only (file tree, pattern cards, icon rows, step cards, badges, callouts, flow diagrams). Two have a touch of JS: the **architecture diagram** (`arch-component` click → fills `arch-description`) and the **layer toggle** (`showLayer` swaps which `.layer` is visible).
- **"Why should I care?":** The content philosophy says every screen must be ≥50% visual. This is the toolbox that makes that possible — and knowing it lets you tell AI "show this as cards, not a paragraph."

### Code Snippets (pre-extracted)

File: architecture diagram HTML — clickable components
```html
<div class="arch-diagram">
  <div class="arch-component" data-desc="Reads the codebase and writes module HTML" onclick="...">
    <div class="arch-icon">🤖</div><span>Writing Agent</span>
  </div>
  <div class="arch-description" id="arch-desc">Click any component to learn what it does</div>
</div>
```

File: main.js — the only JS the diagram needs (lines ~457-465)
```javascript
$$('.arch-component').forEach(comp => {
  comp.addEventListener('click', function () {
    const diagram = this.closest('.arch-diagram');
    $$('.arch-component', diagram).forEach(c => c.classList.remove('active'));
    this.classList.add('active');
    const descEl = $('.arch-description', diagram);
    if (descEl) descEl.textContent = this.dataset.desc || '';
  });
});
```

File: a pure-CSS structured visual (no JS at all) — pattern cards
```html
<div class="pattern-cards">
  <div class="pattern-card">
    <div class="pattern-icon">🔄</div>
    <h4 class="pattern-title">Verbatim Copy</h4>
    <p class="pattern-desc">styles.css & main.js are copied, never regenerated.</p>
  </div>
</div>
```

### Interactive Elements
- [x] **LIVE interactive architecture diagram** — the hero: a clickable map of the skill's own pipeline (each component reveals its job in `arch-description`).
- [x] **LIVE layer toggle** — show a sample built up in layers (HTML → +CSS → +JS), demonstrating the `showLayer` switch.
- [x] **Code↔English translation** — the `arch-component` click handler: explain `closest` (find the nearest enclosing diagram), `dataset.desc` (the text stored on the box), and that everything else in this family is pure CSS.
- [x] **Pattern/feature cards** — a card per family member (file tree, icon rows, step cards, badges, callouts) with a one-line "use it when…".
- [x] **Quiz** — 3 Qs, decision. e.g. "You have a 5-item list in a paragraph — which family member fixes it?" (cards / icon rows) "Which two members need JavaScript?" (arch diagram, layer toggle).
- [x] **Callout** — "aha!": structure IS explanation — a good layout teaches before a single word is read.

### Reference Files to Read
- `references/interactive-elements.md` → "Interactive Architecture Diagram", "Layer Toggle Demo", "Pattern/Feature Cards", "Visual File Tree", "Icon-Label Rows", "Numbered Step Cards", "Permission/Config Badges", "Flow Diagrams", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Flow Animation Engine."
- **Next module:** "Design & Content Philosophy" — the house style that ties it all together.
- **Tone/style notes:** TEAL accent (global). Odd module → alternating background. Give the arch diagram + layer demo their own ids. Tooltip: closest, dataset, CSS, layout, structured data, toggle.
