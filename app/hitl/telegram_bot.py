import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.core.config import settings

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("🤖 Career OS Bot is running.\nWaiting for tasks...")

async def send_approval_request(bot_app: Application, application_id: str, title: str, company: str, score: int, salary: str = "N/A", url: str = "", ats_type: str = "Unknown") -> None:
    """Send a rich message to the user asking for application approval."""
    if not settings.TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_CHAT_ID not set. Skipping approval request.")
        return

    text = (
        f"🚨 **Job Approval Required** 🚨\n\n"
        f"🏢 **Company**: {company}\n"
        f"💼 **Role**: {title}\n"
        f"🎯 **Score**: {score}/100\n"
        f"💰 **Salary**: {salary}\n"
        f"⚙️ **ATS**: {ats_type}\n"
        f"🔗 [View Job]({url})\n\n"
        f"How should I proceed?"
    )

    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{application_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{application_id}")
        ],
        [
            InlineKeyboardButton("⛔ Blacklist Company", callback_data=f"blacklist_{application_id}"),
            InlineKeyboardButton("⏸️ Pause Automation", callback_data=f"pause_all")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        await bot_app.bot.send_message(
            chat_id=settings.TELEGRAM_CHAT_ID,
            text=text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates message text."""
    query = update.callback_query
    await query.answer()

    action = query.data
    
    if action == "pause_all":
        from app.core.kill_switch import engage_kill_switch
        engage_kill_switch("Triggered via Telegram")
        await query.edit_message_text(text="⏸️ **Global Kill Switch Engaged.** All automation has been paused.", parse_mode="Markdown")
        return

    action_type, application_id = action.split("_", 1)
    
    db = SessionLocal()
    try:
        if action_type == "approve":
            from app.agents.apply_worker import apply_to_job
            transition_state(db, application_id, ApplicationStatus.approved, actor="telegram_hitl")
            db.commit()
            await query.edit_message_text(text=f"✅ Approved. Pushed to execution queue.")
            # Dispatch to celery immediately
            apply_to_job.delay(application_id)
            
        elif action_type == "reject":
            transition_state(db, application_id, ApplicationStatus.rejected, actor="telegram_hitl")
            db.commit()
            await query.edit_message_text(text=f"❌ Rejected.")
            
        elif action_type == "blacklist":
            from app.core.blacklist import add_to_blacklist
            app_record = db.query(Application).filter(Application.id == application_id).first()
            if app_record:
                add_to_blacklist(db, app_record.job.company_name, reason="Telegram blacklist button")
                await query.edit_message_text(text=f"⛔ Blacklisted {app_record.job.company_name}. All pending applications soft-rejected.")
    except Exception as e:
        logger.error(f"Error handling callback: {e}")
        await query.edit_message_text(text=f"⚠️ Error processing request.")
    finally:
        db.close()

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.core.kill_switch import engage_kill_switch
    engage_kill_switch("Telegram /pause command")
    await update.message.reply_text("⏸️ Automation paused. Run /resume to continue.")

async def resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.core.kill_switch import disengage_kill_switch
    disengage_kill_switch()
    await update.message.reply_text("▶️ Automation resumed.")

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    from app.core.kill_switch import is_paused
    status = "⏸️ PAUSED" if is_paused() else "▶️ ACTIVE"
    await update.message.reply_text(f"System Status: {status}")

def get_bot_application() -> Application:
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set. Bot will not start.")
        return None
        
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("pause", pause_command))
    application.add_handler(CommandHandler("resume", resume_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    return application
