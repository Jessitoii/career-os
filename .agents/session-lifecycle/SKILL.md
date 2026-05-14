---
name: session-lifecycle
description: Use when working on the daily agent session flow, state machine transitions, Celery task orchestration, rate limiting between applications, or the session shutdown/reporting protocol. Triggers on: "session başlat", "state machine", "IDLE → DISCOVERY", "günlük kapanış", "cooldown", "daily cap", "session end", "Celery task sırası", "SESSION_START", "özet raporu", "rate limiting platformlar arası".
---

# Session Lifecycle Skill

## Use this skill when
- Implementing the daily session start/stop orchestrator
- Adding or modifying state transitions in the application state machine
- Configuring platform-specific rate limits and daily caps
- Building the session-end summary report sent via Telegram
- Debugging a task stuck in an intermediate state

## Do not use this skill when
- HITL Telegram message flows (use `hitl-telegram`)
- Browser automation within a single application (use `ats-adapter` or `stealth-browser`)

## State Machine

### Session States
```
IDLE → DISCOVERY → FILTERING → SCORING → DECISION → EXECUTION → LOGGING → COOLDOWN → SESSION_END
                                                   ↘ SUSPENDED (waiting Telegram input)
                                                   ↘ DISCARDED
```

### Application States (per `application_status` ENUM)
```
scraped → scored → pending_approval → approved → applying → applied
                                                           → interview
                                                           → rejected
                                                           → ghosted
                                                           → withdrawn
                                                           → offer
```

### Confidence Routing (DECISION step)
```python
def route_by_confidence(score: int) -> str:
    if score >= 85:   return "EXECUTION"          # auto-apply
    if score >= 60:   return "AWAITING_APPROVAL"  # Telegram confirmation
    return "DISCARDED"
```

## Instructions

### Session Orchestrator (FastAPI + Celery)
```python
@celery.task
async def run_daily_session(profile_id: UUID):
    session = await create_session(profile_id)
    
    try:
        # 1. DISCOVERY
        await update_session_state(session.id, "DISCOVERY")
        jobs = await scrape_all_sources(profile)
        
        # 2. FILTERING (duplicate check + auto-reject rules)
        await update_session_state(session.id, "FILTERING")
        jobs = await run_duplicate_checks_batch(jobs)
        jobs = [j for j in jobs if not matches_blocklist(j, profile.preferences)]
        
        # 3. SCORING
        await update_session_state(session.id, "SCORING")
        scored = await score_jobs_batch(jobs)
        
        # 4. DECISION + DISPATCH
        for job in scored:
            route = route_by_confidence(job.relevance_score)
            if route == "EXECUTION":
                apply_task.delay(str(job.id))
            elif route == "AWAITING_APPROVAL":
                await send_approval_batch_telegram(job)
            # DISCARDED: no action
        
        # 5. COOLDOWN between applications handled in apply_task
        
    finally:
        await run_session_end_protocol(session.id, profile_id)

@celery.task
async def apply_task(application_id: str):
    """Single application execution with mandatory cooldown."""
    app = await get_application(application_id)
    
    await update_status(application_id, "applying")
    success = await run_browser_application(app)
    
    if success:
        await update_status(application_id, "applied")
    else:
        await update_status(application_id, "failed")
        await telegram_notify(f"❌ Başvuru başarısız: {app.job.company} — {app.job.title}")
    
    # MANDATORY COOLDOWN — read from platform_rate_limits table
    limits = await get_platform_limits(app.job.source)
    wait = random.uniform(limits.min_wait_seconds, limits.max_wait_seconds)
    await asyncio.sleep(wait)
```

### Platform Rate Limits (from DB)
| Platform | Min Wait | Max Wait | Daily Cap | Notes |
|---|---|---|---|---|
| linkedin | 300s | 900s | 10 | Aggressive bot detection |
| greenhouse | 60s | 300s | 50 | Minimal bot detection |
| lever | 60s | 300s | 50 | |
| workday | 120s | 600s | 30 | Shadow DOM, slow |

### Session End Protocol
```python
async def run_session_end_protocol(session_id: UUID, profile_id: UUID):
    # 1. Parse Gmail for application confirmations
    await sync_application_confirmations_from_gmail(profile_id)
    
    # 2. Gather analytics
    stats = await db.fetchrow("""
        SELECT 
            COUNT(*) FILTER (WHERE status='applied') as applied,
            COUNT(*) FILTER (WHERE status='pending_approval') as pending,
            COUNT(*) FILTER (WHERE status='discarded') as rejected,
            COUNT(*) as total_scanned
        FROM applications WHERE session_id = $1
    """, session_id)
    
    efficiency = (stats.applied / stats.total_scanned * 100) if stats.total_scanned else 0
    
    # 3. Send Telegram final report
    await bot.send_message(TELEGRAM_CHAT_ID, f"""
🚀 Session Complete.
-------------------
✅ Applied: {stats.applied}
⏳ Pending Approval: {stats.pending}
❌ Rejected by Filter: {stats.rejected}
📈 Match Efficiency: {efficiency:.1f}%

Tüm işlemler tamamlandı.
    """)
    
    # 4. Cleanup temp browser profiles
    await cleanup_temp_profiles()
    
    await update_session_state(session_id, "SESSION_END")
```

## Safety
- Always check daily cap before dispatching `apply_task` — query `platform_rate_limits.daily_cap`
- If `SESSION_END` is not reached cleanly (crash), run cleanup on next startup via `check_orphaned_sessions()`
