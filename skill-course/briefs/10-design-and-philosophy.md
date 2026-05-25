# Module 10: Design & Content Philosophy (the finale)

### Teaching Arc
- **Metaphor:** A **gallery's house style.** The warm lighting, the one typeface on every placard, the rule that each label fits on an index card — invisible individually, but together they're why the whole space feels like one coherent place instead of a junk drawer. (No restaurant.)
- **Opening hook:** "You've seen the machine and every part. The last secret is taste — the rules that turn a pile of working widgets into something that actually teaches."
- **Key insight:** Two rule-sets do the heavy lifting. The **design system**: warm off-white backgrounds (never cold), one bold accent, distinctive display type (Bricolage Grotesque, NOT Inter/Roboto), alternating module backgrounds. The **content philosophy**: every screen ≥50% visual, metaphors-first (and never "restaurant"), code↔English over prose, quizzes that test *application* not memory, aggressive glossary tooltips, and "why should I care?" before "how does it work?".
- **"Why should I care?":** These are transferable standards for ANY explainer you commission from AI. "Make it warm, one accent, show-don't-tell, define every term" is a spec you can now hand over with confidence.

### Code Snippets (pre-extracted)

File: _base.html — the entire theming surface is four variables
```html
<style>
  :root {
    --color-accent:       #2A7B9B;
    --color-accent-hover: #1F6280;
    --color-accent-light: #E4F2F7;
    --color-accent-muted: #5A9DB8;
  }
</style>
```

The content-philosophy rules (quote as a checklist — these are verbatim principles):
```
- Max 2-3 sentences per text block; every screen ≥ 50% visual.
- Metaphors first, then reality — and NEVER the "restaurant" metaphor.
- Code ↔ English translations beat paragraphs about code.
- Quizzes test application (what would you do?), not definitions.
- Tooltip EVERY technical term on first use — the vocabulary IS the learning.
- Answer "why should I care?" before "how does it work?".
```

(The writing agent should READ `references/design-system.md` for the full token system and `references/content-philosophy.md` for the full rules, and quote a few real tokens/lines.)

### Interactive Elements
- [x] **Before/after demonstration** — the hero: the SAME content shown twice — once as a dense gray wall of text, once rebuilt as the course would (cards + a tooltip + a metaphor). Let the contrast make the argument.
- [x] **Pattern/feature cards** — one card per philosophy rule (≥50% visual, metaphors-first, code↔English, application-quizzes, tooltips, why-care-first).
- [x] **Code↔English translation** — the `:root` accent variables: explain "CSS custom properties" (named, reusable values) and how changing four lines re-themes an entire course.
- [x] **Quiz** — 4 Qs, the capstone (synthesizes the whole course). e.g. "You're commissioning an explainer from an AI — name three rules from this course you'd put in the spec." "Why alternate module backgrounds?" (visual rhythm) "Why ban the restaurant metaphor?" (overused → stops teaching).
- [x] **Callout** — "aha!": tools don't teach — *taste* does. The engines are necessary; the philosophy is what makes it land. End with a confident send-off (the learner can now read this skill, build with it, AND judge any explainer by these standards).

### Reference Files to Read
- `references/design-system.md` → the palette, typography, spacing tokens, alternating backgrounds (READ THIS — it's the subject)
- `references/content-philosophy.md` → all (the subject)
- `references/interactive-elements.md` → "Pattern/Feature Cards", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Scenario Quiz", "Callout Boxes", "Glossary Tooltips"
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Visual Family."
- **Next module:** none — this is the finale. Send the learner off able to point the skill at any repo AND critique any explainer by these standards. Callbacks welcome to Module 1 (the recursion) — they've now seen the whole factory.
- **Tone/style notes:** TEAL accent (global). Even module → alternating background. This is the thesis. Tooltip: CSS custom property/variable, design system, typography, palette, design token, accent.
