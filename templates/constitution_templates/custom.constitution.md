# Project Constitution

**Purpose**: Define immutable development rules for your project

**Instructions**: Fill in each section with rules specific to your project.
Delete this instructions block when complete.

---

## Technology Standards

- [Specify programming languages and versions]
- [Specify frameworks and their versions]
- [Specify databases and tools]
- [Specify package managers]
- [Add more technology standards...]

## Architecture Principles

- [Define architectural patterns (e.g., MVC, Clean Architecture)]
- [Specify design principles (e.g., SOLID, DRY, KISS)]
- [Define layer separation rules]
- [Add more architectural principles...]

## Testing Standards

- [Specify minimum code coverage percentage]
- [Define required test types (unit, integration, E2E)]
- [Specify testing frameworks]
- [Define test isolation requirements]
- [Add more testing standards...]

## Code Standards

- [Specify code formatters and linters]
- [Define naming conventions]
- [Specify documentation requirements]
- [Define complexity limits]
- [Define file/function size limits]
- [Add more code standards...]

## Security Standards

- [Specify authentication/authorization methods]
- [Define secrets management approach]
- [Specify input validation requirements]
- [Define encryption requirements]
- [Add more security standards...]

## Task Orchestration Standards

- Declare per-task dependencies in `tasks.md` as structured rows so `dev-kid orchestrate` can build correct wave ordering. See `.specify/templates/tasks-template.md` §"Task-Level Dependencies" for accepted forms.
- Preferred forms: `TXXX requires TYYY[, TZZZ]` (forward) or `TXXX blocks TYYY[, TZZZ]` (reverse). Avoid vague prose like "T018 needs to happen after T005 eventually".
- When a task defines a symbol (Protocol, class, function) that another task imports, either:
  a) declare the dep explicitly: `T018 requires T005`, OR
  b) use a definer verb + backticked identifier in the defining task: `T005 Define Protocol \`BasePromptBuilder\``. The symbol graph will infer the edge automatically.

## Additional Sections (Optional)

Add any project-specific sections here:

### Example: Deployment Standards
- [Define deployment process]
- [Specify environment requirements]

### Example: Performance Standards
- [Define performance benchmarks]
- [Specify optimization requirements]

### Example: Accessibility Standards
- [Define WCAG compliance level]
- [Specify accessibility testing requirements]
