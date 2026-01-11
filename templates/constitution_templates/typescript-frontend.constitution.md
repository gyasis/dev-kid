# Project Constitution

**Purpose**: Immutable development rules for TypeScript Frontend project

---

## Technology Standards

- TypeScript 5.0+ with strict mode enabled
- React 18+ OR Next.js 14+ for UI framework
- React Query (TanStack Query) for server state management
- Zustand OR Redux Toolkit for client state (choose one)
- TailwindCSS for styling (utility-first approach)
- Zod for runtime validation and type inference
- Vitest for unit testing (faster than Jest)
- Playwright for E2E testing

## Architecture Principles

- Component-based architecture
- Container/Presentational component pattern
- Hooks for state and side effects (no class components)
- Single Responsibility Principle (one component, one purpose)
- Composition over inheritance
- Custom hooks for reusable logic
- Separation of concerns: UI components separate from business logic

## Testing Standards

- Vitest with >80% code coverage required
- Unit tests for all utility functions and custom hooks
- Component tests with React Testing Library
- E2E tests for critical user flows (Playwright)
- Test user interactions, not implementation details
- Mock API calls in unit tests
- No snapshot testing (brittle and unmaintainable)

## Code Standards

- ESLint with strict TypeScript rules
- Prettier for code formatting
- No `any` type usage (use `unknown` if truly unknown)
- Explicit return types for all functions
- Named exports preferred over default exports
- Functional components only (no class components)
- Max file length: 300 lines
- Descriptive component and variable names

## Component Standards

- One component per file
- Props interface defined above component
- Use TypeScript interfaces for props (not types)
- Destructure props in function signature
- Early returns for conditional rendering
- Extract complex JSX into separate components
- Keep render method simple and readable

## State Management Standards

- Use React Query for server state (API data)
- Use Zustand/Redux for global client state only
- Local component state with useState when possible
- No prop drilling (use context or state management)
- Immutable state updates only
- Normalize complex state structures

## Security Standards

- Sanitize all user inputs before rendering
- Use DOMPurify for rendering HTML from user
- No eval() or Function() constructor
- Validate API responses with Zod
- HTTPS only in production
- Implement CSRF protection
- No sensitive data in localStorage (use httpOnly cookies)

## Performance Standards

- Lazy load routes with React.lazy()
- Memoize expensive computations with useMemo
- Memoize callbacks with useCallback where appropriate
- Virtualize long lists (react-window)
- Optimize images (next/image or similar)
- Code splitting for large bundles
- Lighthouse score >90 for performance

## Accessibility Standards

- All interactive elements keyboard accessible
- Semantic HTML elements
- ARIA labels for custom components
- Color contrast ratio >4.5:1
- Focus indicators visible
- Screen reader tested
- WCAG 2.1 Level AA compliance
