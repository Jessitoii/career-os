# 🤖 Career OS — Autonomous Job Application Agent

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7.2-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![Playwright](https://img.shields.io/badge/Playwright-1.44-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.4-37814A?style=for-the-badge&logo=celery&logoColor=white)

![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Active%20Development-orange?style=for-the-badge)
![Human In The Loop](https://img.shields.io/badge/Human--in--the--Loop-Web_GUI_&_Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)

</div>

---

## 📋 Table of Contents

- [What Is This?](#-what-is-this)
- [Architecture](#-architecture)
- [Core Features](#-core-features)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Daily Workflow](#-daily-workflow)
- [ATS Support](#-ats-support)
- [LLM Prompt Contracts](#-llm-prompt-contracts)
- [Data Model](#-data-model)
- [Contributing](#-contributing)

---

## 🎯 What Is This?

**Career OS** is an AI-powered autonomous application orchestration system designed for job seekers. It collects job listings from LinkedIn and Indeed, scores relevance with LLMs, waits for your approval via Telegram, then fills and submits forms using Playwright.

> "It's not just about applying, it's about making the *right* application at the *right* time."

This is not an always-on bot. It starts on a scheduled basis every morning, fills the daily quota, sends a summary report to Telegram, and shuts down.

---

## 🏗 Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                        Career OS                            │
│                                                             │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ Job Collector│───▶│  Hybrid AI   │───▶│ State Machine │  │
│  │  (Scraper)  │    │   Engine     │    │  (Celery)     │  │
│  └─────────────┘    └──────────────┘    └───────┬───────┘  │
│                      Embedding +                │           │
│                      LLM Scoring          ┌─────▼──────┐   │
│                                           │ Web GUI &  │   │
│  ┌─────────────────────────────────┐      │  Telegram  │   │
│  │       Apply Engine              │      └─────┬──────┘   │
│  │  Greenhouse · Lever · Workday   │◀────────────┘          │
│  │  + LLM Vision Fallback          │                        │
│  └─────────────────────────────────┘                        │
│                                                             │
│  PostgreSQL · PGVector · ChromaDB · Redis                   │
└─────────────────────────────────────────────────────────────┘
```

### Core Stack

| Layer | Technology |
|--------|-----------|
| API / Orchestrator | FastAPI |
| Task Queue | Celery + Redis |
| Database | PostgreSQL + PGVector |
| Browser Automation | Playwright + Stealth |
| Local Embedding | Ollama (nomic-embed-text / bge-small) |
| Remote LLM | Groq · Cerebras · Claude · GPT-4o |
| HITL Gateway | Web GUI (React/Vue) & Telegram Bot API |
| Document Gen | reportlab / fpdf |

---

## ✨ Core Features

### 🔍 Smart Job Collection & Filtering
- Collect job listings from LinkedIn, Indeed, Greenhouse, Lever, and RSS sources
- **3-layer duplicate prevention:** URL hash → Email parsing → Semantic similarity
- Auto-reject rules (visa requirements, seniority mismatch, blocked companies)

### 🧠 Hybrid Scoring Engine
- **Local (fast):** Embedding-based cosine similarity pre-filtering
- **Remote (deep):** LLM-based visa, salary, stack, and seniority analysis
- Automatic decision-making based on score: `auto_apply` / `ask_user` / `reject`

### 🤖 Anti-Bot Stealth System
- Fingerprint rotation (User-Agent, WebGL, Canvas, Hardware Concurrency)
- Human-like typing speed and wait times with Gaussian jitter
- Non-linear scrolling and pixel-perfect clicking

### 📱 Web GUI & Telegram Human-in-the-Loop
- Freezes the application in uncertain situations and requests input via Web GUI and Telegram
- Inline buttons: `[3500€] [4000€] [Enter Manually]`
- User responses are stored as "learned behavior"
- Marks as `PENDING_LATER` if no response arrives within 30 minutes

### 🎯 CV Optimization
- Selects the most suitable CV from 3 different versions based on the job description
- **Immutable Block Selection:** Never fabricates information, only rearranges existing blocks
- Automatic generation of job-specific Cover Letters (PDF)

### 📊 Adaptive Strategy Engine
- Updates filters using `interview_rate` data after every session
- Country/stack-based scanning frequency and confidence threshold adjustment
- "Prime-Time Apply": Applies during the hours with the highest response rates

---

## 🚀 Installation

### Requirements

- Python 3.11+
- Docker & Docker Compose
- Ollama (for local embeddings)
- Telegram Bot Token

### 1. Clone the Repository

```bash
git clone https://github.com/kullaniciadi/career-os.git
cd career-os
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

```env
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/careeros
REDIS_URL=redis://localhost:6379/0

# LLM Providers
GROQ_API_KEY=your_groq_key
ANTHROPIC_API_KEY=your_anthropic_key
OPENAI_API_KEY=your_openai_key        # Optional

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Embedding
OLLAMA_BASE_URL=http://localhost:11434

# Storage
CV_STORAGE_PATH=./storage/cvs
```

### 3. Start with Docker

```bash
docker compose up -d postgres redis ollama
```

### 4. Prepare the Database

```bash
pip install -r requirements.txt
alembic upgrade head
```

### 5. Install Playwright

```bash
playwright install chromium
```

---

## ⚙️ Configuration

Specify your target role and preferences in the `config/user_profile.yaml` file:

```yaml
profile:
  name: "Full Name"
  email: "email@example.com"
  
job_preferences:
  target_roles:
    - "Senior Backend Engineer"
    - "AI/ML Engineer"
    - "Staff Software Engineer"
  locations: ["Berlin", "Amsterdam", "Remote"]
  min_salary: 70000
  remote_preference: "hybrid"
  blocked_companies: ["CompanyX", "CompanyY"]

cv_versions:
  - id: "backend_ai_v2"
    path: "./storage/cvs/backend_ai_v2.pdf"
    focus: ["FastAPI", "LLM", "Python"]
  - id: "mobile_focused"
    path: "./storage/cvs/mobile_focused.pdf"
    focus: ["React Native", "Flutter", "iOS"]

scoring:
  auto_apply_threshold: 85
  ask_user_threshold: 60
  daily_cap: 15
```

---

## 📖 Usage

### Manual Start

```bash
python -m app.main start --session-mode scheduled
```

### Scheduled Execution (Cron)

```bash
# Start every morning at 08:00
0 8 * * 1-5 cd /path/to/career-os && python -m app.main start
```

### Scoring Only (Without Applying)

```bash
python -m app.main score --dry-run
```

### Run Pending Applications Manually

```bash
python -m app.main apply --pending-only
```

---

## 🔄 Daily Workflow

```text
IDLE ──▶ DISCOVERY ──▶ FILTERING ──▶ SCORING
                                         │
                              ┌──────────┴──────────┐
                              │                     │
                         conf > 0.90           0.70 < conf < 0.90
                              │                     │
                         EXECUTION           AWAITING_APPROVAL
                              │               (GUI & Telegram)
                              │                     │
                              └──────────┬──────────┘
                                         │
                                      LOGGING
                                         │
                                      COOLDOWN
                                         │
                                    SESSION_END
```

**End-of-day Telegram / GUI report:**

```text
🚀 Session Complete.
-------------------
✅ Applied: 12
⏳ Pending Approval: 3
❌ Rejected by Filter: 145
📈 Match Efficiency: 14%

All operations completed. You can safely shut down the system.
```

---

## 🏢 ATS Support

| Platform | Adapter | Difficulty | Notes |
|----------|---------|--------|--------|
| Greenhouse | `GreenhouseAdapter` | ⭐ Easy | Minimal bot detection |
| Lever | `LeverAdapter` | ⭐ Easy | Minimal bot detection |
| Workday | `WorkdayAdapter` | ⭐⭐⭐ Hard | Shadow DOM, dynamic loading |
| LinkedIn | `LinkedInAdapter` | ⭐⭐⭐⭐ Very Hard | Aggressive bot detection |
| Custom Portal | `LLMVisionFallback` | ⭐⭐ Medium | Fallback with GPT-4o Vision |

**Unknown portal fallback hierarchy:**

1. **Heuristic Mapping** — dictionary-based label matching
2. **LLM Vision** — CSS selector detection with screenshots + accessibility tree  
3. **Human-in-the-Loop** — manual approval and "learned behavior" recording via GUI & Telegram

---

## 📜 LLM Prompt Contracts

The system uses contracts in every LLM task with a **strict requirement to return JSON**.

### Model Selection Matrix

| Task | Model | Reason |
|-------|-------|---------|
| Relevance Scoring | Groq Llama-3-70b | Speed-critical, structured JSON is enough |
| CV Tailoring | Claude Sonnet | Reasoning and tone quality |
| DOM Vision Fallback | GPT-4o / Gemini 1.5 Pro | Vision capability required |
| Rejection Categorize | Groq Llama-3-70b | Short input, simple classification |
| Interview Prep | Claude Sonnet | Long context, synthesis required |

### Rate-Limit Fallback Chain

```text
429 received
  ├── per_minute → wait retry_after + 1 sec → retry with same model
  └── per_day   → switch to next model in chain
                   ├── Groq models (in order)
                   ├── Cerebras models
                   └── Ollama (local, last resort)
                         └── if all exhausted → GUI/Telegram alert + freeze task
```

---

## 🗄 Data Model

Main tables:

```text
user_profiles      → User preferences (JSONB)
cv_documents       → CV versions and metadata
job_listings       → Listings, AI score, embedding vector (vector(384))
applications       → Applications, state machine data
interaction_logs   → Audit trail (GUI, Telegram, form, email)
platform_rate_limits → Daily caps and wait durations for each ATS
user_sessions      → Encrypted browser session paths
```

**Analytics View:**

```sql
-- Which CV version gets more interviews?
SELECT * FROM cv_performance_stats;
```

---

## 📁 Project Structure

```text
career-os/
|── docs/                  # Documents
├── app/
│   ├── adapters/          # ATS Adapters (Greenhouse, Lever, Workday)
│   ├── agents/            # Scraper, Scorer, Applier, ResearchAgent
│   ├── core/              # State machine, Celery tasks
│   ├── hitl/              # Web GUI & Telegram gateways
│   ├── intelligence/      # Embedding + LLM scoring
│   ├── prompts/           # Prompt contract library
│   └── stealth/           # Anti-bot utils (human_type, natural_scroll)
├── config/
│   └── user_profile.yaml
├── migrations/            # Alembic
├── storage/
│   └── cvs/
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🔒 Security and Ethical Usage

- Browser sessions are stored encrypted (`encrypted_session_path`)
- Rate limiting is mandatory; a **minimum 2-minute** delay is enforced between each application
- The system **never fabricates information** — CV tailoring only rearranges existing data
- LinkedIn daily cap: maximum **10 applications** (ban prevention)

> ⚠️ This tool is designed for personal job search workflows. In bulk or commercial usage, compliance with the relevant platform Terms of Service is the user's responsibility.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/workday-adapter-v2`)
3. Commit your changes (`git commit -m 'feat: WorkdayAdapter shadow DOM support'`)
4. Push the branch (`git push origin feature/workday-adapter-v2`)
5. Open a Pull Request

---

## 📄 License

MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Career OS** — *Because job hunting is also an engineering problem.*

[![GitHub Stars](https://img.shields.io/github/stars/kullaniciadi/career-os?style=social)](https://github.com/kullaniciadi/career-os)

</div>