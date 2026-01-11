# Project Constitution

**Purpose**: Immutable development rules for Data Engineering project

---

## Technology Standards

- Python 3.11+ for all data pipelines
- Apache Airflow 2.7+ OR Prefect 2.0+ for orchestration
- dbt 1.6+ for data transformations
- Snowflake OR BigQuery OR Redshift for data warehouse
- pandas OR polars for data processing (polars preferred for large datasets)
- SQLAlchemy for database connections
- Great Expectations for data quality testing
- Poetry OR uv for dependency management

## Architecture Principles

- ELT over ETL (transform in warehouse when possible)
- Idempotent pipelines (re-running produces same result)
- Incremental processing where applicable
- Separate staging, intermediate, and production layers
- Data contracts between pipeline stages
- Schema versioning for all data models
- Lineage tracking for all transformations

## Data Quality Standards

- Data validation at every pipeline stage
- Schema enforcement with Great Expectations
- Null check expectations on non-nullable columns
- Range checks on numeric columns
- Enum validation on categorical columns
- Uniqueness constraints on ID columns
- Referential integrity checks on foreign keys
- Data quality metrics tracked and monitored

## Testing Standards

- pytest with >70% code coverage required
- Unit tests for all transformation logic
- Integration tests for full pipeline runs
- Data quality tests with Great Expectations
- Test with sample data that covers edge cases
- Mock external data sources
- Validate schema changes don't break downstream

## Code Standards

- Ruff for formatting and linting
- Type hints required (mypy strict mode)
- Docstrings required (Google style with examples)
- SQL style guide: lowercase keywords, uppercase table names
- dbt models: one model per file
- Max SQL query complexity: 5 CTEs
- Descriptive column names (no abbreviations)
- Include business logic comments in SQL

## Pipeline Standards

- DAG structure: Extract → Load → Transform (ELT)
- Atomic tasks (one responsibility per task)
- Clear task dependencies defined
- Retry logic with exponential backoff
- Alerting on pipeline failures
- SLA monitoring for critical pipelines
- Idempotency: safe to re-run failed tasks
- Checkpoint/resume for long-running pipelines

## dbt Standards

- Staging models: one-to-one with source tables
- Intermediate models: reusable transformations
- Mart models: business-facing tables
- Use refs() for all model dependencies
- Singular tests for custom data quality checks
- Generic tests for common validations
- Materializations: views for dev, tables for prod
- Document all models and columns

## Security Standards

- No credentials in code (use secret managers)
- Row-level security where applicable
- Column-level encryption for PII
- Audit logging for data access
- Data masking for non-production environments
- RBAC for warehouse access
- Compliance with GDPR/CCPA where applicable

## Monitoring Standards

- Pipeline execution time tracked
- Data freshness monitored
- Row count changes monitored
- Data quality metrics dashboarded
- Alert on anomalies (volume, distribution)
- Lineage graphs maintained
- Cost monitoring for warehouse queries
