# **Job Application Agent - Prompt Contract Library**

This document is designed to standardize LLM interactions across different layers of the system and reduce the margin of error to zero.

## **0. Model Selection Matrix**

## | Task                   | Model                        | Rationale                            |

## |------------------------|------------------------------|--------------------------------------|

## | Relevance Scoring      | Groq Llama-3-70b / Cerebras  | Speed is critical, structured JSON is sufficient |

## | CV Tailoring           | Claude Sonnet / GPT-4o       | Requires reasoning and tone quality  |

## | DOM Vision Fallback    | GPT-4o / Gemini 1.5 Pro      | Vision capability is mandatory       |

## | Rejection Categorize   | Groq Llama-3-70b             | Short input, simple classification   |

## | Interview Prep Research| Claude Sonnet                | Long context, requires synthesis     |

## 

## **1. Relevance Scoring**

**Goal:** To quickly verify the suitability of the job posting for the user profile.

**Model:** Groq (Llama-3-70b) or Cerebras.

### **System Prompt**

You are a professional technical recruiter. Your task is to compare the provided candidate profile with the job description (JD) and return an analysis strictly in JSON format.

Analysis rules:  
1. Scoring (0-100): Based on technical skill match, years of experience, and location fit.  
2. Flags: Mark critical obstacles such as visa sponsorship required, German language mandatory, or "Senior" expectation.  
3. Decision: If 85+ 'auto_apply', between 60-85 'ask_user', below 60 'reject'.

Do not add any explanations or text outside of the JSON whatsoever.

### **JSON Schema (Output Contract)**

{  
  "score": 87,  
  "reasoning": [  
    "FastAPI and PostgreSQL experience match exactly.",  
    "Candidate's AI Agent experience is a 'bonus' for the posting.",  
    "Years of experience (3) is right in the middle of the posting's expectation (2-4)."  
  ],  
  "critical_flags": ["Visa Sponsorship Required", "Hybrid (Berlin)"],  
  "decision": "ask_user"  
}

## **2. CV Tailoring**

**Goal:** To rearrange existing CV blocks according to the job posting (without adding fabricated information).

**Strategy:** "Immutable Block Selection".

### **System Prompt**

Your task is to select and order the most suitable ones for the job posting from the candidate's raw dataset (Master Data).   
RULE: Do not generate new data, do not change existing sentences. Order using only the provided IDs.

Input:  
- Master_Skills: [ID, Name, Category]  
- Master_Projects: [ID, Title, Description, Tech_Stack]  
- Job_Description: [Text]

Output:  
Return a JSON object containing only the selected IDs.

### **Prompt Strategy & Schema**

The LLM is only granted permission to rewrite headings (for the Summary section), work experiences and projects only operate on the "Select/Order" logic.

{  
  "tailored_summary": "Backend engineer with 3 years of experience focused on FastAPI and LLM integration. Developed agentic workflows reaching 1000+ users with the OpenReef project.",  
  "selected_project_ids": [1, 4, 2],  
  "top_skill_ids": [10, 15, 2, 8, 22],  
  "keyword_injections": ["Distributed Systems", "RAG Pipeline"]  
}

## **3. HITL (Web GUI & Telegram) "Action Required" Contracts**

**Goal:** To ensure that the questions the bot asks the user turn into buttons or clear options in the UI.

### **Scenario: Salary Expectation**

**System Message Generation:**

{  
  "type": "USER_INPUT_REQUIRED",  
  "topic": "salary_expectation",  
  "job_context": {  
    "company": "TechCorp",  
    "role": "Senior AI Engineer",  
    "location": "Berlin"  
  },  
  "question_text": "You didn't specify a salary expectation for this posting. The Berlin average is 75k-90k Euros. What should we write?",  
  "options": [  
    {"label": "75,000 €", "value": 75000},  
    {"label": "85,000 €", "value": 85000},  
    {"label": "Custom", "value": "manual_input"}  
  ]  
}

### **Scenario: Visa Status**

{  
  "type": "USER_INPUT_REQUIRED",  
  "topic": "visa_sponsorship",  
  "question_text": "The posting specifies an 'EU Work Permit' requirement. What is your status?",  
  "options": [  
    {"label": "Visa sponsorship is required", "value": "needs_sponsorship"},  
    {"label": "I have a Blue Card/EU Citizenship", "value": "has_permit"}  
  ]  
}

### **4. Rate-Limit & Fallback Management**

**Contract:** A smart fallback protocol that distinguishes API errors by type and operates over a sequential model chain.

#### **Error Type Detection**

When a 429 error occurs, information in the response header or body is parsed:

def parse_rate_limit_error(error_response: dict) -> dict:

    """

    Extracts the limit type and wait time from the Groq/Cerebras 429 response.

    Returned structure:

      {

        "limit_type": "per_minute" | "per_day",

        "retry_after_seconds": int | None

      }

    """

    headers = error_response.get("headers", {})

    body    = error_response.get("body", {})

    # retry-after header: usually populated for per-minute limits

    retry_after = headers.get("retry-after") or headers.get("x-ratelimit-reset-requests")

    # Daily limit signals: "day" / "daily" appears in the body message

    error_msg = str(body.get("error", {}).get("message", "")).lower()

    is_daily  = any(kw in error_msg for kw in ["daily", "per day", "quota", "24-hour"])

    return {

        "limit_type": "per_day" if is_daily else "per_minute",

        "retry_after_seconds": int(retry_after) if retry_after else None,

    }

#### **Fallback Chain**

Two different behaviors are applied depending on the limit type:

**If Hit by Minute Limit → Wait & Continue with the Same Model**

async def handle_minute_limit(retry_after_seconds: int | None, call_fn):

    wait = (retry_after_seconds or 60) + 1   # Margin of 1s + time told by API

    logger.info(f"Minute rate-limit. Waiting for {wait}s...")

    await asyncio.sleep(wait)

    return await call_fn()   # same model, same request

**If Hit by Daily Limit → Move to the Next One in the Model Chain**

# Task-based model chains (order matters)

MODEL_CHAINS = {

    "relevance_scoring": [

        {"provider": "groq",     "model": "llama-3-70b-8192"},

        {"provider": "groq",     "model": "mixtral-8x7b-32768"},

        {"provider": "groq",     "model": "gemma2-9b-it"},

        {"provider": "cerebras", "model": "llama3.1-70b"},

        {"provider": "cerebras", "model": "llama3.1-8b"},

        {"provider": "ollama",   "model": "llama3:8b"},        # local fallback

    ],

    "cv_tailoring": [

        {"provider": "anthropic", "model": "claude-sonnet-4"},

        {"provider": "openai",    "model": "gpt-4o-mini"},

        {"provider": "groq",      "model": "llama-3-70b-8192"},

        {"provider": "ollama",    "model": "llama3:8b"},

    ],

    # other tasks...

}

#### **Main Dispatcher**

async def call_with_fallback(task: str, payload: dict) -> dict:

    chain = MODEL_CHAINS[task]

    for i, model_cfg in enumerate(chain):

        try:

            response = await call_model(model_cfg, payload)

            return parse_json_response(response)

        except RateLimitError as e:

            parsed = parse_rate_limit_error(e.response)

            if parsed["limit_type"] == "per_minute":

                # Wait and retry on the same model (progression in the chain)

                await handle_minute_limit(parsed["retry_after_seconds"],

                                          lambda: call_model(model_cfg, payload))

                continue

            elif parsed["limit_type"] == "per_day":

                logger.warning(f"[{model_cfg['provider']}/{model_cfg['model']}] "

                               f"daily limit reached. Moving to the next model...")

                continue   # fall back to the next model in the chain

        except InvalidJSONError:

            # If JSON is broken, try 1 more time on the same model, then move on

            if i < len(chain) - 1:

                logger.warning("Invalid JSON. Moving to the next model.")

                continue

    # If the entire chain is exhausted

    await telegram_notify("🔴 All models failed. Manual check required.")

    raise AllModelsExhaustedError(task=task, payload=payload)

#### **Summary Flow**

429 received

  ├── per_minute → wait retry_after + 1s → retry on the same model

  └── per_day   → move to the next model in the chain

                   ├── Groq models (multiple, sequentially)

                   ├── Cerebras models

                   └── Ollama (local, last resort)

                         └── if all exhausted → Web GUI/Telegram alert + freeze task

