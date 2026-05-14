---
description: Triggered manually or scheduled in the morning. Starts the entire scraping, filtering, scoring, and application process.
---

## Pre-Checks (Before Starting)

1. **Daily cap check** — verify today's application count from the `platform_rate_limits` table:
   ```sql
   SELECT jl.source, COUNT(*) as today_count, prl.daily_cap
   FROM applications a
   JOIN job_listings jl ON a.job_id = jl.id
   JOIN platform_rate_limits prl ON jl.source = prl.platform
   WHERE a.applied_at::date = CURRENT_DATE
   GROUP BY jl.source, prl.daily_cap;
   ```

2. **Stealth plugin check** — verify that the `create_stealth_context()` function in `stealth.py` is
   active and tested (must pass on bot.sannysoft.com).

3. **Ollama status** — check that the embedding model is
   running with `curl http://localhost:11434/api/tags`.

4. **Redis/Celery status** — verify that the workers are
   ready with `celery -A app.celery_app status`.

## Initialization Steps

1. Add a new record to the `user_sessions` table (`is_active = TRUE`).
2. Queue the `run_daily_session.delay(profile_id)` Celery task.
3. Send a notification to Telegram: `"🚀 Session started. Scanning sources..."`
4. Monitor the terminal output — `celery -A app.celery_app worker --loglevel=info`

## Expected Output

- Terminal: Session ID and `DISCOVERY` state log
- Telegram: Start message
- DB: Active `user_sessions` record

## Error Cases

- **If Ollama is not running**: Run `ollama serve`, verify that the `ollama pull nomic-embed-text` model is
  installed.
- **If Redis cannot connect**: `docker-compose up redis -d` (or service manager).
- **If Daily cap is full**: Do not start the session, notify the user.

## Related Skill
`session-lifecycle` — for orchestrator details.
