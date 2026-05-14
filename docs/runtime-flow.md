# Final Runtime Boot Sequence

Here are the exact runnable commands to boot the complete execution pipeline.

## 1. Setup Data Paths
Ensure local persistence directories exist:
```bash
mkdir -p storage/traces/videos
mkdir -p data/resumes/master
mkdir -p data/resumes/fallback
mkdir -p data/resumes/generated
mkdir -p playwright_data
```

## 2. Boot Infrastructure (Database & Message Queues)
```bash
docker-compose up -d
```

## 3. Database Migration
```bash
alembic upgrade head
```

## 4. Playwright Setup
Ensure headless automation dependencies are present:
```bash
playwright install chromium
playwright install-deps
```

## 5. Startup the System
You need **three** concurrent terminal sessions:

**Terminal A (The API & WebSockets):**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal B (The Application Dispatcher / Celery):**
```bash
celery -A app.celery_app worker --loglevel=info -P solo
```

**Terminal C (The Operational Console / Next.js):**
```bash
cd frontend
npm run dev
```

## 6. Triggering Jobs
To manually push a discovery session to the queue:
```bash
# Triggers the run_daily_session Celery task
curl -X POST http://localhost:8000/system/trigger-session
```
