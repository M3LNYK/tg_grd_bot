from dotenv import dotenv_values
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import json
from pathlib import Path

# States for conversations
(
    WAITING_FOR_NUMBER,
    WAITING_FOR_NAME,
    WAITING_FOR_EDIT_CHOICE,
    WAITING_FOR_EDIT_VALUE,
) = range(4)


# Load config directly
config = dotenv_values(".env")
BOT_TOKEN = config.get("TELEGRAM_TOKEN")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")

async def addUser(update: Update, )

app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))

app.run_polling()
