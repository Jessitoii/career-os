---
name: interview-prep
description: Use when building or triggering the automated interview preparation pipeline — detecting interview invitations from email/calendar, running company research, LinkedIn analysis, and generating prep documents. Triggers on: "mülakat daveti", "interview detected", "ResearchAgent", "prep-doc", "şirket araştırma", "LinkedIn profil analizi", "takvim daveti", "ICS", "next steps email", "teknik soru tahmini", "interview prep".
---

# Interview Prep Skill

## Use this skill when
- Implementing the interview invitation detection logic
- Building or updating the ResearchAgent pipeline
- Generating the Prep-Doc sent via Telegram
- Debugging a missed interview invitation (false negative)

## Do not use this skill when
- General email processing (use Gmail MCP directly)
- Rejection email analysis (that's `Career_OS_Spesifikasyonu.md` → Rejection Analysis)

## Trigger Detection

An interview invitation is confirmed when ANY of these signals appear:

### Signal 1: Calendar Invite
- Email has ICS attachment
- Google Calendar invite received (via Calendar MCP)

### Signal 2: Keyword Detection in Email Body
```python
INTERVIEW_KEYWORDS = [
    "interview", "screening", "quick chat", "let's connect",
    "call with", "meet with", "speak with", "next steps",
    "would like to invite", "schedule a call", "chat with our team"
]
```

### Signal 3: LLM Classification (for ambiguous emails)
```python
async def classify_email_as_interview(email_body: str) -> bool:
    prompt = f"""
    Is this email an interview invitation or request to connect for a job opportunity?
    Respond ONLY with JSON: {{"is_interview_invite": true/false, "confidence": 0.0-1.0}}
    
    Email: {email_body[:2000]}
    """
    result = await call_with_fallback("rejection_categorize", {"prompt": prompt})
    if result["confidence"] < 0.8:
        # Send to human for confirmation via Telegram
        await request_human_classification(email_body)
        return False
    return result["is_interview_invite"]
```

## ResearchAgent Pipeline

Once an interview is confirmed, trigger `ResearchAgent`:

### Step 1: Company Research
```python
async def research_company(company_name: str) -> dict:
    # Web search: last 6 months news
    queries = [
        f"{company_name} news 2025",
        f"{company_name} product launch funding",
        f"{company_name} layoffs culture glassdoor",
    ]
    # Use browser agent or web_search MCP
    return {"recent_news": [...], "culture_signals": [...]}
```

### Step 2: Interviewer LinkedIn Analysis
```python
async def analyze_interviewer(linkedin_url: str) -> dict:
    # Scrape public LinkedIn profile (via browser agent)
    # Extract: current role, background, shared interests, recent posts
    return {"background": "...", "talking_points": [...]}
```

### Step 3: Technical Question Prediction
```python
async def predict_interview_questions(job_description: str, detected_stack: list[str]) -> list[str]:
    prompt = f"""
    Based on this job description and tech stack ({detected_stack}), 
    generate the 5 most likely technical interview questions.
    Return ONLY JSON: {{"questions": ["...", ...]}}
    
    JD: {job_description}
    """
    result = await call_with_fallback("interview_prep", {"prompt": prompt})
    return result["questions"]
```

### Step 4: Generate & Send Prep-Doc
```python
async def send_prep_doc(application_id: UUID, research: dict, questions: list[str]):
    # Generate markdown or PDF prep document
    # Save to /storage/prep_docs/{application_id}_prep.pdf
    # Update applications.application_data['prep_doc_path']
    # Send Telegram link
    
    await bot.send_message(TELEGRAM_CHAT_ID, f"""
📋 *Mülakat Hazırlık Dokümanı Hazır*

🏢 Şirket: {research['company_name']}
📅 Tarih: {interview_date}

✅ Doküman oluşturuldu. [Aç]({prep_doc_url})

🎯 Tahmini Sorular:
{chr(10).join(f"{i+1}. {q}" for i, q in enumerate(questions[:3]))}
    """, parse_mode='Markdown')
    
    # Update application status
    await update_status(application_id, "interview")
```

## Model
Use `claude-sonnet-4-20250514` — long context and synthesis quality are critical for research tasks.
