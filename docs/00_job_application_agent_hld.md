# **High-Level Design: Job Application Agent**

## **1. Architecture Overview**

The system is designed as an event-driven and human-in-the-loop job application orchestration engine that triggers during specific time windows (scheduled sessions), rather than a continuously running bot.

### **Core Stack**

* **Backend:** FastAPI (Orchestrator & API)  
* **Task Queue:** Redis + Celery (Distributed execution & retries)  
* **Database:** PostgreSQL (State management, Logs, Job Data)  
* **Vector Store:** ChromaDB or PGVector (Local embedding storage)  
* **Automation:** Playwright + Stealth Plugin (Browser automation)  
* **HITL Gateway:** Web GUI & Telegram Bot API (Asynchronous approval/input)

## **2. System Components**

### **A. Job Collector Service (Scraper)**

* **Input:** Target platforms (LinkedIn, Indeed, etc.), search filters.  
* **Technology:** Playwright (Headless/Headed switch), RSS parsers.  
* **Function:** Collects raw job data, normalizes it (converts to JSON format), and writes it to the database after deduplication (duplicate check).

### **B. Hybrid Intelligence Engine**

Applies two-stage filtering to optimize processing cost and speed:

1. **Local Filtering (Embedding-based):**  
   * Uses nomic-embed-text or bge-small models via Ollama.  
   * Calculates cosine similarity between the user's profile summary and the job description.  
   * Eliminates jobs below the threshold value.  
2. **Remote Reasoning (LLM-based):**  
   * Jobs in the top 10-20% percentile are sent to Groq/Cerebras (Llama-3-70B) or GPT-4o-mini.  
   * **Task:** Visa requirement, salary estimation, seniority match, and "hard-skill" analysis.  
   * **Output:** Structured JSON (Score, Match Reasoning, Potential Red Flags).

### **C. Workflow & State Machine**

This is the center of the system. Each application process is managed by a state machine:

* PENDING: Job found, not yet scored.  
* SCORING: AI analysis is in progress.  
* AWAITING_APPROVAL: Waiting for user approval or additional info (salary expectation, etc.) via Web GUI or Telegram.  
* READY_TO_APPLY: Approval received, entered the application queue.  
* APPLYING: Browser automation is active.  
* SUCCESS / FAILED: Final status and logs.

## **3. Human-In-The-Loop (HITL) Integration**

### **Web GUI & Telegram Gateway**

The system pauses in moments of uncertainty (low confidence) or at critical actions (submit) and requests input via Web GUI and Telegram.

* **Workflow Pausing:** The Celery task transitions to the WAITING state and the state is stored in Redis.  
* **Interactions:** Inline buttons (Approve / Reject / Edit Salary).  
* **Callback:** When the user clicks the button, the FastAPI endpoint is triggered, the relevant state is updated to READY_TO_APPLY, and the task continues from where it left off.

## **4. Automation & Apply Engine**

### **ATS Adapters**

The system uses a separate "Adapter" for each portal:

* GreenhouseAdapter, LeverAdapter, WorkdayAdapter.  
* For unknown structures, the **LLM Vision/Navigation** fallback mechanism kicks in.

### **Document Management**

* **CV Selection:** AI selects the most suitable from 3 different CV versions based on the job description.  
* **Dynamic PDF Generation:** Creates a job-specific Cover Letter / Brief using reportlab or fpdf and archives it on local disk/S3.

## **5. Data Model and Memory**

### **PostgreSQL Schema**

* Jobs: Posting details, source URL, raw data.  
* Applications: Application status, CV version used, platform logs.  
* UserMemory: Salary history, rejected companies, recruiter interactions.

### **Long-term Memory (Vector)**

Descriptions of postings that returned positively in the past are stored in the vector base. New postings are compared with this "success history" to update the Match Score weight.

## **6. Operational Flow (Scheduled Sessions)**

1. **Start:** The user starts the application manually or scheduled in the morning.  
2. **Scrape & Score:** The system scans the market and scores for 1 hour.  
3. **Batch Notification:** High-scoring jobs are presented as a list on the Web GUI and Telegram.  
4. **Async Execution:** As the user gives approval during the day, the system completes applications in the background.  
5. **Shutdown:** When the "Daily cap" is reached or there are no postings left to scan, the system sends a summary report and shuts down.

## **7. Security and Anti-Bot Measures**

* **Rate Limiting:** Random (random jitter) wait times between each application.  
* **Stealth:** Fingerprint rotation and Playwright solutions equivalent to puppeteer-extra-plugin-stealth.  
* **Auth:** Keeping LinkedIn/Google sessions persistent via user_data_dir.
