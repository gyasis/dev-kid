# Module 6: The Quiz Family (element deep-dive)

### Teaching Arc
- **Metaphor:** A **game-show buzzer panel.** You lock in a choice, hit "check," and the panel lights green or red with an instant explanation — no host, no waiting. The answer key was wired into the panel from the start. (No restaurant.)
- **Opening hook:** "Every quiz in this course knows its own answer and its own explanations — before you ever click. The 'grading' is just a string comparison."
- **Key insight:** Quizzes are **declarative**: the HTML carries the answer (`data-correct`) and feedback (`data-explanation-right` / `-wrong`). `main.js` exposes `selectOption`, `checkQuiz`, `resetQuiz`; checking just compares the selected `data-value` to `data-correct` and reveals the matching explanation. Drag-and-drop and "spot the bug" are the same idea with different data attributes.
- **"Why should I care?":** "Declarative" (describe the what, let the engine do the how) is one of the biggest ideas in modern software. Seeing it in a 10-line quiz makes the concept concrete.

### Code Snippets (pre-extracted)

File: quiz HTML — the answer key lives in the markup
```html
<div class="quiz-question-block"
     data-correct="option-b"
     data-explanation-right="Exactly — because X is responsible for Y."
     data-explanation-wrong="Not quite. Think about where Y lives...">
  <button class="quiz-option" data-value="option-b" onclick="selectOption(this)">
    <div class="quiz-option-radio"></div><span>Answer B</span>
  </button>
  <div class="quiz-feedback"></div>
</div>
```

File: main.js — the entire "grader" (lines ~191-201)
```javascript
if (selected.dataset.value === correct) {
  selected.classList.add('correct');
  feedback.innerHTML = '<strong>Exactly!</strong> ' + rightExp;
} else {
  selected.classList.add('incorrect');
  const correctBtn = $(`.quiz-option[data-value="${correct}"]`, q);
  if (correctBtn) correctBtn.classList.add('correct');
  feedback.innerHTML = '<strong>Not quite.</strong> ' + wrongExp;
}
```

### Interactive Elements
- [x] **LIVE multiple-choice quiz** — a working quiz the reader uses WHILE learning how it works (meta).
- [x] **Drag-and-drop matching** — the hero second element: match each quiz attribute (`data-correct`, `data-value`, `data-explanation-wrong`) to its job. Demonstrates the drag-drop member of the family too.
- [x] **Code↔English translation** — the grader snippet: explain `===` (exact match), `dataset.value` (reads a `data-value` attribute), and that the feedback was pre-written by the author.
- [x] **Quiz** — 3 Qs (meta). e.g. "Where does a quiz store its correct answer?" (in the HTML, `data-correct`) "Add a 4th option — what's the ONLY thing the engine needs to grade it?" (a `data-value`).
- [x] **Callout** — "aha!": declarative design — the data describes the truth; one generic engine acts on it. Same pattern as config files, CSS, and SQL.

### Reference Files to Read
- `references/interactive-elements.md` → "Multiple-Choice Quizzes", "Drag-and-Drop Matching", "Scenario Quiz", "Spot the Bug Challenge", "Code ↔ English Translation Blocks", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "Glossary Tooltips."
- **Next module:** "The Group Chat Engine."
- **Tone/style notes:** TEAL accent (global). Even module → alternating background. Give the live quiz + dnd unique container `id`s. Tooltip: declarative, attribute, data-attribute, string comparison, dataset, event handler/onclick.
