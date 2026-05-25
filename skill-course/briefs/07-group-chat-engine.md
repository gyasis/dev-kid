# Module 7: The Group Chat Engine (element deep-dive)

### Teaching Arc
- **Metaphor:** A **stage play where actors enter on cue.** Each line is pre-written and hidden in the wings; a brief hush (the typing dots) tells you who's about to speak, then they step into the light, one at a time. (No restaurant.)
- **Opening hook:** "Those iMessage-style conversations between components? The whole script is sitting in the page from the start — hidden — and revealed one bubble at a time."
- **Key insight:** Every `.chat-window` auto-initializes. Messages start `display:none`, each tagged with `data-sender`. The engine builds an **actor map** (each sender's initial + color) by scanning the messages, shows a typing indicator wearing the next speaker's avatar, then reveals the bubble. `showNext` / `showAll` / `reset` drive it.
- **"Why should I care?":** It teaches a core UI idea — *the data is all there; the experience is in the timing of reveal.* That's animation, onboarding flows, and progressive disclosure in a nutshell.

### Code Snippets (pre-extracted)

File: chat HTML — a hidden, tagged message
```html
<div class="chat-message" data-sender="actor-a" style="display:none">
  <div class="chat-avatar" style="background: var(--color-actor-1)">A</div>
  <div class="chat-bubble">
    <span class="chat-sender">Actor A</span>
    <p>Hey, I need the data for this item.</p>
  </div>
</div>
```

File: main.js — building the actor map + revealing on cue (lines ~326-358)
```javascript
const actors = {};
messages.forEach(msg => {
  const sender = msg.dataset.sender;
  const avatar = $('.chat-avatar', msg);
  if (avatar && !actors[sender]) actors[sender] = { initial: avatar.textContent.trim(), style: avatar.style.background };
});
function showNext() {
  const msg = messages[index]; const sender = msg.dataset.sender;
  if (typingEl && actors[sender]) { /* show typing dots wearing sender's avatar */ typingEl.style.display = 'flex'; }
  setTimeout(() => { typingEl.style.display = 'none'; msg.style.display = 'flex'; index++; }, 800);
}
```

### Interactive Elements
- [x] **LIVE group chat** — the hero: a working chat (e.g., the Main Agent dispatching briefs, or any small 4-message exchange) the reader plays WHILE learning how it works. Unique container `id`.
- [x] **Code↔English translation** — the actor-map + showNext: explain `dataset.sender` (a label on each message), why it scans messages to learn the cast automatically, and the 800ms "typing" delay that makes it feel human.
- [x] **Numbered step cards** — the reveal lifecycle: hidden → typing dots → bubble appears → advance index.
- [x] **Quiz** — 3 Qs. e.g. "How does the engine know each actor's color/initial?" (scans the messages) "Are the messages fetched live or already on the page?" (already there, hidden).
- [x] **Callout** — "aha!": progressive disclosure — withholding info you already have, to control pace and attention.

### Reference Files to Read
- `references/interactive-elements.md` → "Group Chat Animation", "Numbered Step Cards", "Code ↔ English Translation Blocks", "Multiple-Choice Quizzes", "Callout Boxes", "Glossary Tooltips"
- `references/content-philosophy.md` → all
- `references/gotchas.md` → all

### Connections
- **Previous module:** "The Quiz Family."
- **Next module:** "The Flow Animation Engine."
- **Tone/style notes:** TEAL accent (global). Odd module → alternating background. The chat needs `.chat-next-btn`/`.chat-all-btn`/`.chat-reset-btn` and a unique `id` + matching typing-avatar id (`{id}-typing-avatar`). Tooltip: progressive disclosure, data-sender, actor map, display:none, setTimeout, avatar.
