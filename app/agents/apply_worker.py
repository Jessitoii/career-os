import logging
import asyncio
from celery import shared_task
from app.core.db import SessionLocal
from app.models.application import Application, ApplicationStatus
from app.core.state_machine import transition_state
from app.core.kill_switch import is_paused
from app.automation.stealth import create_stealth_context
from app.automation.adapters import detect_adapter
from app.automation.resume import get_best_resume
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

# Max retries to prevent infinite loops
MAX_RETRIES = 3

@shared_task(bind=True, max_retries=MAX_RETRIES, acks_late=True, reject_on_worker_lost=True)
def apply_to_job(self, application_id: str):
    """
    Consumes approved jobs. Instantiates ATS adapter, executes playwright flow,
    handles errors and state transitions. Idempotent.
    """
    if is_paused():
        logger.warning(f"Kill switch active. Deferring {application_id}")
        self.retry(countdown=300)

    db = SessionLocal()
    try:
        app = db.query(Application).filter(Application.id == application_id).first()
        
        # Duplicate / State prevention
        if app.status not in [ApplicationStatus.approved, ApplicationStatus.retry_pending]:
            logger.warning(f"App {application_id} in {app.status}. Cannot apply.")
            return

        if app.retry_count >= MAX_RETRIES:
            logger.error(f"App {application_id} exceeded retries.")
            transition_state(db, application_id, ApplicationStatus.blocked, actor="system", payload={"reason": "max_retries"})
            return

        # Transition to applying
        transition_state(db, application_id, ApplicationStatus.applying, actor="celery")
        app.retry_count += 1
        db.commit()

        # Execute Async Playwright via asyncio wrapper
        result = asyncio.run(_execute_playwright_flow(app, db))
        
        if result["status"] == "success":
            transition_state(db, application_id, ApplicationStatus.applied, actor="system", payload=result)
        elif result["status"] == "requires_human":
            transition_state(db, application_id, ApplicationStatus.requires_human, actor="system", payload=result)
        else:
            transition_state(db, application_id, ApplicationStatus.failed_apply, actor="system", payload=result)
            # Trigger backoff retry
            backoff = 60 * (2 ** app.retry_count)
            self.retry(countdown=backoff)

    except Exception as exc:
        logger.exception(f"Fatal error in apply_to_job: {exc}")
        # Transition to failed
        try:
            transition_state(db, application_id, ApplicationStatus.failed_apply, actor="system", payload={"error": str(exc)})
            db.commit()
        except:
            pass
        self.retry(exc=exc, countdown=300)
    finally:
        db.close()


async def _execute_playwright_flow(app: Application, db) -> dict:
    # 1. Prepare Resume
    try:
        strat, r_path, r_hash = get_best_resume(db, job_category=None, user_id=app.profile_id)
        app.resume_strategy_used = strat
        app.resume_version = r_path
        app.resume_hash = r_hash
        db.commit()
    except Exception as e:
        return {"status": "error", "reason": f"Resume prep failed: {e}"}

    from app.core.config import settings
    # 2. Setup Playwright Context
    async with async_playwright() as p:
        context = await create_stealth_context(
            p, 
            user_data_dir="./playwright_data", 
            headless=settings.PLAYWRIGHT_HEADLESS,
            slow_mo=settings.PLAYWRIGHT_SLOW_MO,
            record_video_dir=settings.RECORD_VIDEO_DIR if not settings.DRY_RUN else None
        )
        
        # Start trace
        await context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = await context.new_page()

        try:
            logger.info(f"Navigating to {app.job.url}")
            await page.goto(app.job.url, timeout=30000)

            # Detect ATS Adapter
            adapter = await detect_adapter(page)
            if not adapter:
                # Need LLM vision or human
                trace_path = f"{settings.TRACE_DIR}/trace_{app.id}_no_adapter.zip"
                await context.tracing.stop(path=trace_path)
                return {"status": "requires_human", "reason": "No compatible ATS adapter found", "trace": trace_path}

            # Prepare data
            data = {
                "first_name": "John", # In real scenario, load from UserProfile
                "last_name": "Doe",
                "email": "john.doe@example.com",
                "cv_path": r_path,
                "approved": not settings.DRY_RUN,
                "application_id": str(app.id)
            }

            # Fill Form
            snapshot_path = await adapter.fill_application(data)
            
            trace_path = f"{settings.TRACE_DIR}/trace_{app.id}_success.zip"
            await context.tracing.stop(path=trace_path)
            
            app.browser_trace_path = trace_path
            db.commit()

            return {"status": "success", "snapshot": snapshot_path, "dry_run": settings.DRY_RUN}

        except Exception as e:
            # Capture error state
            err_shot = f"{settings.TRACE_DIR}/error_{app.id}.png"
            await page.screenshot(path=err_shot)
            trace_path = f"{settings.TRACE_DIR}/trace_{app.id}_error.zip"
            await context.tracing.stop(path=trace_path)
            
            app.error_screenshot_path = err_shot
            app.browser_trace_path = trace_path
            db.commit()
            
            return {"status": "error", "reason": str(e), "trace": trace_path, "screenshot": err_shot}
        finally:
            await context.close()
