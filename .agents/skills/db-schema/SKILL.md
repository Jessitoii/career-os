---
name: db-schema
description: Use when writing database migrations, queries, or ORM models for this project. Triggers on: "migration yaz", "tablo oluştur", "PostgreSQL şema", "PGVector", "SQL sorgu", "Alembic", "index ekle", "ENUM güncelle", "application_data JSONB", "cv_performance_stats view", "interaction_logs", "veritabanı modeli".
---

# Database Schema Skill

## Use this skill when
- Writing a new Alembic migration
- Adding columns, indexes, or tables
- Writing complex analytical queries (funnel, CV performance, session stats)
- Debugging a query on `applications`, `job_listings`, or `interaction_logs`
- Adding a new `application_status` ENUM value

## Do not use this skill when
- Application business logic that happens to touch the DB (use the relevant domain skill)

## Schema Quick Reference

### Core Tables
| Table | Primary Key | Key Columns |
|---|---|---|
| `user_profiles` | UUID | `email`, `preferences JSONB` |
| `cv_documents` | UUID | `profile_id`, `version_name`, `metadata JSONB` |
| `job_listings` | UUID | `external_id`, `source`, `relevance_score`, `embedding vector(384)`, `status` |
| `applications` | UUID | `job_id`, `profile_id`, `cv_id`, `status`, `application_data JSONB` |
| `interaction_logs` | UUID | `application_id`, `actor`, `action_type`, `payload JSONB` |
| `platform_rate_limits` | TEXT (platform) | `min_wait_seconds`, `max_wait_seconds`, `daily_cap` |
| `user_sessions` | UUID | `profile_id`, `platform`, `encrypted_session_path` |

### application_status ENUM Values
`scraped` → `scored` → `pending_approval` → `approved` → `applying` → `applied` → `interview` / `rejected` / `ghosted` / `withdrawn` / `offer`

### Key Indexes
```sql
CREATE INDEX idx_job_listings_external_id ON job_listings(external_id);
CREATE INDEX idx_job_listings_relevance   ON job_listings(relevance_score);
CREATE INDEX idx_applications_status      ON applications(status);
CREATE INDEX idx_listing_embedding        ON job_listings USING ivfflat (embedding l2_ops);
```

### Useful Views
```sql
-- CV performance: which version converts best?
SELECT * FROM cv_performance_stats;

-- Funnel analysis
SELECT
    COUNT(*) FILTER (WHERE status = 'scraped')          as total_scraped,
    COUNT(*) FILTER (WHERE status = 'scored')           as matched,
    COUNT(*) FILTER (WHERE status = 'applied')          as applied,
    COUNT(*) FILTER (WHERE status = 'interview')        as interview,
    ROUND(100.0 * COUNT(*) FILTER (WHERE status='interview') 
          / NULLIF(COUNT(*) FILTER (WHERE status='applied'), 0), 2) as interview_rate
FROM applications;
```

## Instructions

### Adding a Migration (Alembic)
```bash
alembic revision --autogenerate -m "add_column_X_to_Y"
# Review the generated file in alembic/versions/
# Apply:
alembic upgrade head
```

### Adding a New ENUM Value
```sql
ALTER TYPE application_status ADD VALUE 'pending_later' AFTER 'pending_approval';
```
Note: PostgreSQL ENUM additions cannot be rolled back easily — test on staging first.

### Querying JSONB Fields
```python
# application_data contains nested JSON — use -> and ->> operators
await db.fetchrow("""
    SELECT application_data->>'cover_letter_path' as cover_letter,
           application_data->'user_answers' as answers
    FROM applications WHERE id = $1
""", application_id)
```

### Vector Similarity Query (Semantic Duplicate Check)
```sql
-- Find jobs with >95% cosine similarity to a given embedding
SELECT id, 1 - (embedding <-> $1::vector) as similarity
FROM job_listings
WHERE 1 - (embedding <-> $1::vector) >= 0.95
ORDER BY similarity DESC
LIMIT 5;
```

## Safety
- NEVER run `DROP TABLE` or `TRUNCATE` without a confirmed backup.
- All schema changes go through Alembic — no manual `ALTER TABLE` in production.
- `encrypted_session_path` column must never appear in SELECT * queries in logs.
