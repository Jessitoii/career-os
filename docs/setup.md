# Setup Guide (Target Environment)

This document provides the exact verified steps to deploy the Career OS system on your high-performance development machine.

## Prerequisites
- Docker & Docker Compose
- Node.js (v18+)
- Python (3.11+)

## 1. Environment Configuration
Create a `.env` file in the root directory and populate it with your keys. **Do not use Anthropic.**
```env
ENVIRONMENT=dev
GROQ_API_KEY="gsk_..."
CEREBRAS_API_KEY="csk_..."
TELEGRAM_BOT_TOKEN="1234:..."
TELEGRAM_CHAT_ID="98765"
```

## 2. Start Infrastructure Services
```bash
docker-compose up -d
```
This boots:
1. PostgreSQL (with `pgvector` enabled)
2. Redis (for Celery and WebSockets)
3. Ollama (running `nomic-embed-text`)

Ensure Ollama has the model pulled:
```bash
docker exec -it careeros_ollama ollama pull nomic-embed-text
```

## 3. Backend Setup
Install the verified dependencies:
```bash
pip install -r requirements.txt
```

Run database migrations to generate the tables:
```bash
alembic upgrade head
```

Install Playwright browsers for automation:
```bash
playwright install chromium
```

Start the FastAPI backend and Celery workers:
```bash
uvicorn app.main:app --reload
celery -A app.celery_app worker --loglevel=info
```

## 4. Frontend Setup
Navigate to the frontend directory:
```bash
cd frontend
npm install
npm run dev
```

Navigate to `http://localhost:3000` to view the Career OS Command Center.
