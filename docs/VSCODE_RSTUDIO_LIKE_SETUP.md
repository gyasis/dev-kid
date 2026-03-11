# VS Code / Cursor: RStudio-like layout for R (keep Python/Rust as-is)

Use VS Code or Cursor in a more RStudio-like way for R (source + console + plots), while keeping your normal setup for Python/Rust.

## 1. RStudio-like layout in VS Code

RStudio has: **Source (left)** | **Console (top-right)** + **Plots/Help/Environment (bottom-right)**.

VS Code cannot do two stacked panels on the right. You can get close with:

- **Code on the left**, **terminal/panel on the right** (one panel: console + output + plot viewer).

### Option A: Panel on the right (recommended for R)

Moves the whole panel (terminal, output, debug console, **and** R plot viewer) to the right side.

**User setting** (global):

```json
"workbench.panel.defaultLocation": "right"
```

- **R**: Code left, R terminal and httpgd plots on the right → very RStudio-like.
- **Python/Rust**: Same layout; terminal on the right. If you prefer terminal at bottom for dev, use Option B or C.

### Option B: Keep panel at bottom for Python/Rust, right only for R (workspace)

- **Default**: Don’t set `workbench.panel.defaultLocation` (panel stays at bottom).
- **R projects**: In each R project, add `.vscode/settings.json`:

```json
{
  "workbench.panel.defaultLocation": "right"
}
```

Then for R work you get “panel on the right”; for other projects, panel stays at bottom.

### Option C: Cursor profiles (R vs Dev)

1. **Cursor** → **Profiles** → **Create profile** (e.g. “R”).
2. In that profile, set `workbench.panel.defaultLocation` to `"right"`.
3. Keep your default profile for Python/Rust (panel at bottom).
4. Switch profile when you switch between R and dev work.

---

## 2. R setup in VS Code (RStudio-like workflow)

Install once:

1. **R** (≥ 3.4.0) from [CRAN](https://cloud.r-project.org/).
2. **VS Code extension**: [R (REditorSupport.r)](https://marketplace.visualstudio.com/items?itemName=REditorSupport.r).
3. **In R**:
   ```r
   install.packages("languageserver")  # LSP: completion, hover, diagnostics
   install.packages("httpgd")          # Plots in VS Code
   ```
4. **Radian** (optional but nice): `pip install -U radian` — better console (highlighting, multiline).

### Daily R workflow (like RStudio)

1. Open your `.R` (or `.Rmd`) file.
2. **R: Create R terminal** (Command Palette `Ctrl+Shift+P`).
3. Run code:
   - **Ctrl+Enter**: run line or selection (sends to R terminal).
   - **Ctrl+Shift+S**: source entire file.
4. Plots from `httpgd` open in the R extension’s plot viewer (in the panel or sidebar).
5. **Workspace viewer**: click the R icon in the Activity Bar for objects/packages/help (similar to RStudio’s Environment/Help).

So: **source left**, **console + plots in the panel** (right if you use Option A or B/C for R).

---

## 3. Optional: terminal in editor area (split like “code | console”)

If you want the R **terminal** as a second editor column (code | console) instead of in the panel:

1. **Terminal: Create New Terminal in Editor Area** (Command Palette).
2. Create R terminal and drag its tab into that editor area so you get **Editor | R terminal**.
3. Or set:
   ```json
   "terminal.integrated.defaultLocation": "editor"
   ```
   (New terminals open in the editor area; you can then split.)

Use this if you prefer “two columns” over “panel on the right”. Your Python/Rust workflow can keep using the default terminal (panel) unless you also enable this.

---

## 4. Summary

| Goal                         | What to do                                                                 |
|-----------------------------|----------------------------------------------------------------------------|
| RStudio-like for R          | Panel on right (Option A global, or B workspace / C profile for R only).  |
| R run/source                | R extension + “R: Create R terminal” + Ctrl+Enter / Ctrl+Shift+S.         |
| Plots in VS Code            | Install `httpgd` in R; use R extension’s plot viewer.                     |
| Keep Python/Rust unchanged  | Use Option B (R-only workspace) or Option C (separate “R” profile).        |

If you tell me whether you want “panel right for everything” or “only for R projects”, I can give you the exact `settings.json` snippet to paste (user vs workspace).
