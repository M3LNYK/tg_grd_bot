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


# Simple storage functions
def load_students(user_id: int) -> dict:
    file_path = Path(f"data/{user_id}_students.json")
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_students(user_id: int, students: dict) -> None:
    file_path = Path(f"data/{user_id}_students.json")
    file_path.parent.mkdir(exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(students, f, ensure_ascii=False, indent=2)


# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Welcome to Student Manager Bot!\n\n"
        "Available commands:\n"
        "/add - Add new student\n"
        "/list - Show all students\n"
        "/find - Find student by number or name\n"
        "/edit - Edit student information\n"
        "/delete - Delete student\n"
        "/cancel - Cancel current operation"
    )


async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Please enter student number:")
    return WAITING_FOR_NUMBER


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    number = update.message.text
    if not number.isdigit():
        await update.message.reply_text("Please enter a valid number!")
        return WAITING_FOR_NUMBER

    context.user_data["temp_number"] = number
    await update.message.reply_text("Now enter student name:")
    return WAITING_FOR_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = update.message.text
    number = context.user_data.pop("temp_number")

    students = load_students(update.effective_user.id)
    students[number] = name
    save_students(update.effective_user.id, students)

    await update.message.reply_text(
        f"Student added successfully!\nNumber: {number}\nName: {name}"
    )
    return ConversationHandler.END


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    students = load_students(update.effective_user.id)
    if not students:
        await update.message.reply_text("No students in the database.")
        return

    message = "Students list:\n\n"
    for number, name in students.items():
        message += f"Number: {number}\nName: {name}\n\n"
    await update.message.reply_text(message)


async def find_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "Please provide a number or name to search.\n"
            "Example: /find John or /find 12345"
        )
        return

    students = load_students(update.effective_user.id)
    results = []

    # Search by number (exact match) or name (case-insensitive partial match)
    for number, name in students.items():
        if query == number or query.lower() in name.lower():
            results.append(f"Number: {number}\nName: {name}")

    if results:
        await update.message.reply_text("Found matches:\n\n" + "\n\n".join(results))
    else:
        await update.message.reply_text("No matching students found.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Add conversation handler
    add_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={
            WAITING_FOR_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number)
            ],
            WAITING_FOR_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(add_conv_handler)
    app.add_handler(CommandHandler("list", list_students))
    app.add_handler(CommandHandler("find", find_student))
    app.add_handler(CommandHandler("hello", hello))

    # Start the bot
    print("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
