---
name: hitl-telegram
description: Use when building or debugging the Human-in-the-Loop Telegram integration — pausing agent tasks for user approval, sending inline button messages, handling webhook callbacks, and resuming suspended Celery tasks. Triggers on: "Telegram bot", "kullanıcı onayı", "AWAITING_APPROVAL", "inline button", "webhook callback", "task dondur", "maaş beklentisi sor", "HITL", "async approval", "human-in-the-loop".
---

# Human-in-the-Loop (HITL) Telegram Skill

## Use this skill when
- Building Telegram Bot message flows (inline buttons, photo captions)
- Implementing the pause/resume mechanism for Celery tasks waiting on user input
- Adding a new "question type" to the approval flow (salary, visa status, custom field)
- Debugging a stuck `SUSPENDED` state that never resumes
- Wiring the Telegram webhook to the FastAPI callback endpoint

## Do not use this skill when
- General state machine changes (use `session-lifecycle`)
- Telegram used for final daily report only (that's a simple `bot.send_message`, no skill needed)

## Message Contract

All HITL messages must follow the JSON contract from `Prompt_Sözleşme_Kütüphanesi.md`:

```json
{
  "type": "USER_INPUT_REQUIRED",
  "topic": "salary_expectation | visa_sponsorship | unknown_field | submit_confirm",
  "job_context": { "company": "...", "role": "...", "location": "..." },
  "question_text": "...",
  "options": [
    {"label": "75,000 €", "value": 75000},
    {"label": "Custom", "value": "manual_input"}
  ]
}
```

## Instructions

### 1. Pausing a Task (SUSPENSION PROTOCOL)
```python
# In the Celery task, when input is needed:
async def suspend_task(task_id: str, application_id: UUID, question: dict):
    # 1. Freeze browser state
    await page.screenshot(path=f"/tmp/{application_id}_suspended.png")
    dom_snapshot = await page.content()
    
    # 2. Update DB
    await db.execute("""
        UPDATE applications SET status='pending_approval',
        application_data = application_data || $1
        WHERE id = $2
    """, [json.dumps({"suspended_question": question}), application_id])
    
    # 3. Log the interaction
    await log_interaction(application_id, actor='system', 
                          action_type='telegram_question', payload=question)
    
    # 4. Send Telegram message
    await send_approval_request(application_id, question, 
                                screenshot_path=f"/tmp/{application_id}_suspended.png")
    
    # 5. Revoke task (it will be re-queued on callback)
    raise Ignore()  # Celery: mark task as ignored, not failed
```

### 2. Sending the Telegram Message
```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

async def send_approval_request(application_id: UUID, question: dict, screenshot_path: str):
    keyboard = [
        [InlineKeyboardButton(opt['label'], 
         callback_data=f"answer:{application_id}:{opt['value']}")]
        for opt in question['options']
    ]
    
    with open(screenshot_path, 'rb') as photo:
        await bot.send_photo(
            chat_id=TELEGRAM_CHAT_ID,
            photo=photo,
            caption=f"⏸ *{question['job_context']['company']} — {question['job_context']['role']}*\n\n{question['question_text']}",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
```

### 3. FastAPI Webhook Callback (Resume)
```python
@app.post("/telegram/callback")
async def telegram_callback(update: TelegramUpdate):
    data = update.callback_query.data  # "answer:{application_id}:{value}"
    _, application_id, value = data.split(":", 2)
    
    # Store answer
    await db.execute("""
        UPDATE applications SET status='approved',
        application_data = application_data || $1
        WHERE id = $2
    """, [json.dumps({"user_answer": value}), application_id])
    
    # Log
    await log_interaction(application_id, actor='user', 
                          action_type='telegram_answer', content=value)
    
    # Re-queue the Celery task
    apply_task.delay(str(application_id))
    
    await update.callback_query.answer("✅ Cevap alındı, başvuru devam ediyor.")
```

### 4. Timeout Handling (30-minute rule)
```python
# Celery beat schedule: runs every 5 minutes
@celery.task
def check_suspended_timeouts():
    cutoff = datetime.utcnow() - timedelta(minutes=30)
    timed_out = db.query("""
        SELECT id FROM applications 
        WHERE status = 'pending_approval' 
        AND last_status_change < $1
    """, [cutoff])
    
    for app_id in timed_out:
        db.execute("UPDATE applications SET status='pending_later' WHERE id=$1", [app_id])
        bot.send_message(TELEGRAM_CHAT_ID, 
                         f"⏭ Zaman aşımı. Başvuru ertelendi: {app_id}")
```

## Safety
- `TELEGRAM_CHAT_ID` must be your personal chat ID — never a group. One human per agent.
- Validate `callback_data` application_id exists in DB before processing — prevent replay attacks.
- Never include salary values or personal data in Telegram message logs.
