# Project Constitution

**Purpose**: Immutable development rules for Full-Stack project

---

## Technology Standards - Backend

- Python 3.11+ OR Node.js 20+ for backend
- FastAPI (Python) OR Express/Fastify (Node.js) for APIs
- PostgreSQL OR MySQL for relational data
- Redis for caching and sessions
- Docker for containerization
- Type hints (Python) OR TypeScript (Node.js) required

## Technology Standards - Frontend

- TypeScript 5.0+ with strict mode
- React 18+ OR Next.js 14+ for UI
- TailwindCSS for styling
- React Query for server state
- Zod for validation (both frontend and backend)

## Architecture Principles

- Monorepo structure (backend + frontend in same repo)
- API-first design (OpenAPI/Swagger spec)
- RESTful API design OR GraphQL (choose one)
- Backend: Routes → Services → Repositories → Models
- Frontend: Pages → Containers → Components → Hooks
- Shared types between frontend and backend
- Clear API contracts with versioning

## Testing Standards

- >80% code coverage for backend
- >75% code coverage for frontend
- Unit tests for business logic
- Integration tests for API endpoints
- E2E tests for critical user flows
- Contract testing between frontend and backend
- Performance testing for API endpoints

## Code Standards - Backend

- Ruff (Python) OR ESLint + Prettier (Node.js)
- Type hints/TypeScript required everywhere
- Docstrings/JSDoc required for public APIs
- Max function complexity: 10 cyclomatic
- Max file length: 500 lines
- No business logic in route handlers

## Code Standards - Frontend

- ESLint with strict TypeScript rules
- Prettier for formatting
- No `any` type usage
- Functional components only
- Named exports preferred
- Max file length: 300 lines

## API Design Standards

- RESTful conventions (GET, POST, PUT, DELETE)
- Versioned API endpoints (/api/v1/...)
- Consistent error response format
- Pagination for list endpoints
- Rate limiting on all endpoints
- Request/response validation with schemas
- OpenAPI documentation for all endpoints

## Security Standards

- Authentication: JWT OR OAuth2 (choose one)
- Password hashing with bcrypt (12+ rounds)
- HTTPS only in production
- CORS configuration for allowed origins
- Input validation on both frontend and backend
- SQL injection prevention (ORM only)
- XSS prevention (sanitize user inputs)
- CSRF protection for state-changing operations
- Rate limiting on auth endpoints

## Database Standards

- ORM/Query Builder only (no raw SQL)
- Migrations for all schema changes
- Foreign key constraints enforced
- Indexes on frequently queried columns
- Soft deletes for user data
- Timestamps (created_at, updated_at) on all tables
- Database connection pooling
- Transaction management for multi-step operations

## State Management Standards

- Backend: Session management with Redis
- Frontend: React Query for server state
- Frontend: Zustand/Redux for client state
- No duplicated state between frontend and backend
- Optimistic updates where appropriate
- Cache invalidation strategy defined

## Monitoring & Observability

- Structured logging (JSON format)
- Request IDs tracked across stack
- APM for backend (Sentry, DataDog, etc.)
- Error tracking for frontend (Sentry)
- Metrics: Response time, error rate, throughput
- Health check endpoints
- Database query performance monitoring

## Deployment Standards

- Docker Compose for local development
- Kubernetes OR Docker Swarm for production
- CI/CD pipeline (GitHub Actions, GitLab CI)
- Automated testing in CI
- Blue-green OR rolling deployments
- Database migrations run before deployment
- Environment-specific configuration (dev, staging, prod)
- Secrets managed with vault OR cloud secret manager
