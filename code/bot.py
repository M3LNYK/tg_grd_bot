from dotenv import dotenv_values
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load config directly
config = dotenv_values(".env")
BOT_TOKEN = config.get("TELEGRAM_TOKEN")

# print(f"Loaded token: {BOT_TOKEN}")  # Debug print
# print(f"Token type: {type(BOT_TOKEN)}")


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


app = ApplicationBuilder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("hello", hello))

app.run_polling()
