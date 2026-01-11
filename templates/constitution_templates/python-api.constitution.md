# Project Constitution

**Purpose**: Immutable development rules for Python API project

---

## Technology Standards

- Python 3.11+ required for all backend code
- FastAPI framework for all REST APIs
- Pydantic v2 for data validation and serialization
- SQLAlchemy ORM for database access (no raw SQL queries)
- Alembic for database migrations
- asyncio/await for concurrency (never use threading.local)
- Type hints required for all functions (mypy strict mode)
- Use contextvars for async-safe context (not threading.local)

## Architecture Principles

- Single Responsibility Principle (SRP) - one class, one purpose
- Dependency Injection via FastAPI dependency system
- Repository pattern for all data access
- Service layer for business logic (separate from API routes)
- Clean separation: Routes → Services → Repositories → Models
- No business logic in route handlers
- No database queries in service layer (use repositories)

## Testing Standards

- pytest with >80% code coverage required
- Unit tests required for all public functions
- Integration tests required for all API endpoints
- Use fixtures for database setup and teardown
- Mock external APIs and services
- Test happy path AND error cases
- No tests should depend on each other (isolation required)

## Code Standards

- Ruff for formatting and linting (faster than Black + flake8 combined)
- Line length: 88 characters
- isort for import sorting (or use ruff's import sorting)
- Docstrings required for all public functions (Google style)
- Type hints required (mypy strict mode enforced)
- Max function complexity: 10 cyclomatic
- Max file length: 500 lines
- No wildcard imports (from x import *)
- Descriptive variable names (no single-letter except loop counters)

## Security Standards

- No hardcoded secrets (use environment variables)
- Input validation with Pydantic on all API inputs
- SQL injection prevention (ORM only, no raw SQL)
- Authentication required for all non-public endpoints
- Rate limiting on all public endpoints
- HTTPS only in production
- Sanitize all user inputs
- Use parameterized queries only

## Error Handling Standards

- Use custom exception classes (inherit from base exceptions)
- Never swallow exceptions silently
- Log all errors with context
- Return appropriate HTTP status codes
- User-friendly error messages (no stack traces to clients)
- Structured error responses with error codes

## Logging Standards

- Structured logging (JSON format)
- Include request IDs in all logs
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- No sensitive data in logs (passwords, tokens, PII)
- Timestamp all log entries
- Include user context when available
