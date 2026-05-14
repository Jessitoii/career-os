import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from app.core.config import settings

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    await update.message.reply_text("🤖 Career OS Bot is running.\nWaiting for tasks...")

async def send_approval_request(bot_app: Application, application_id: str, title: str, company: str, score: int) -> None:
    """Send a message to the user asking for application approval."""
    if not settings.TELEGRAM_CHAT_ID:
        logger.warning("Telegram Chat ID not set. Skipping notification.")
        return
        
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"approve_{application_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"reject_{application_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"🔔 **Action Required**\n\n" \
           f"Job: {title} at {company}\n" \
           f"Score: {score}/100\n\n" \
           f"Do you want to apply?"

    await bot_app.bot.send_message(chat_id=settings.TELEGRAM_CHAT_ID, text=text, reply_markup=reply_markup, parse_mode="Markdown")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates message text."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("approve_"):
        app_id = data.split("_")[1]
        # TODO: Trigger Celery task or State Machine update for 'approved'
        await query.edit_message_text(text=f"✅ Approved application: {app_id}")
    elif data.startswith("reject_"):
        app_id = data.split("_")[1]
        # TODO: Trigger State Machine update for 'rejected'
        await query.edit_message_text(text=f"❌ Rejected application: {app_id}")

def get_telegram_app() -> Application | None:
    """Initialize and return the Telegram application."""
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Telegram Bot Token not set. Bot disabled.")
        return None
        
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    return application
