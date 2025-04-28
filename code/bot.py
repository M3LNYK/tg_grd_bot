import os
import asyncio  # Import asyncio for proper async execution if needed later
from dotenv import load_dotenv, dotenv_values
from telegram.error import BadRequest
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)  # Add button imports
from telegram.constants import ParseMode  # Import ParseMode for formatting
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

# Import the Database class from your new file
from database import Database


# Load environment variables from .env file
load_dotenv()

# Get the bot token from environment variables
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Ensure token is loaded
if not BOT_TOKEN:
    raise ValueError("TELEGRAM_TOKEN not found in environment variables.")


# --- Constants ---
DEFAULT_SORT_ORDER = "student_number"


# --- Bot Handlers ---

# States for conversations
(
    WAITING_FOR_NUMBER,
    WAITING_FOR_NAME,
    WAITING_FOR_EDIT_CHOICE,
    WAITING_FOR_EDIT_VALUE,
    WAITING_FOR_DELETE_IDENTIFIER,
    WAITING_FOR_DELETE_CONFIRMATION_NUMBER,
) = range(6)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a welcome message when the /start command is issued."""
    await update.message.reply_text(
        f"Welcome {update.effective_user.first_name}!\n\n"
        "I can help you manage student IDs.\n"
        "Type /help to see the list of available commands."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends explanation on how to use the bot."""
    await update.message.reply_text(
        "Available commands:\n"
        "/add - Add new student (Number then Name)\n"
        "/list - Show all students\n"
        "/find <query> - Find student by number or name\n"
        # "/edit - Edit student information (TODO)\n" # Keep TODOs commented out for help
        # "/delete - Delete student (TODO)\n"
        "/cancel - Cancel current operation (like adding)\n"
        "/help - Show this help message"
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

    # Access the database instance from bot_data
    db = context.bot_data["db"]
    db.add_student(update.effective_user.id, number, name)

    await update.message.reply_text(
        f"Student added successfully!\nNumber: {number}\nName: {name}"
    )
    return ConversationHandler.END


async def list_students(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists students with sorting options."""
    db = context.bot_data["db"]
    user_id = update.effective_user.id

    # Get current sort order from user_data, default if not set
    sort_order = context.user_data.get("list_sort_order", DEFAULT_SORT_ORDER)

    students = db.get_students(user_id, order_by=sort_order)

    message_text, reply_markup = format_student_list(students, sort_order)

    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.MARKDOWN_V2,  # Use MarkdownV2 for formatting
    )


async def find_student(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args)
    if not query:
        await update.message.reply_text(
            "Please provide a number or name to search.\n"
            "Example: /find John or /find 12345"
        )
        return

    # Access the database instance from bot_data
    db = context.bot_data["db"]
    results = db.find_students(update.effective_user.id, query)

    if results:
        message = "Found matches:\n\n"
        for student in results:
            message += f"Number: {student['student_number']}\nName: {student['student_name']}\n\n"
        await update.message.reply_text(message)
    else:
        await update.message.reply_text("No matching students found.")


async def list_button_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handles button presses for the student list (sorting)."""
    query = update.callback_query
    await query.answer()  # Answer the callback query first

    callback_data = query.data
    user_id = query.from_user.id
    db = context.bot_data["db"]

    # Get the *current* sort order before changing it
    current_sort_order = context.user_data.get("list_sort_order", DEFAULT_SORT_ORDER)
    new_sort_order = current_sort_order

    # Determine potential new sort order based on button pressed
    if callback_data == "list_sort_student_number":
        new_sort_order = "student_number"
    elif callback_data == "list_sort_student_name":
        new_sort_order = "student_name"

    # --- Check if sort order actually changed ---
    if new_sort_order == current_sort_order:
        # If not changed, do nothing (or maybe send a subtle notification)
        # await query.answer("List is already sorted this way.") # Optional feedback
        return

    # --- If sort order changed, proceed ---
    # Store the new sort order
    context.user_data["list_sort_order"] = new_sort_order

    # Fetch sorted students
    students = db.get_students(user_id, order_by=new_sort_order)

    # Format the message and keyboard again
    message_text, reply_markup = format_student_list(students, new_sort_order)

    # Edit the original message
    try:
        await query.edit_message_text(
            text=message_text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    except BadRequest as e:
        # Handle potential error if the message content hasn't changed
        if "Message is not modified" in str(e):
            print("Message not modified (already sorted).")  # Log less critically
        else:
            print(f"Error editing message: {e}")  # Log other BadRequests
            # Optionally notify the user
            # await query.message.reply_text("Sorry, couldn't update the list.")
    except Exception as e:
        print(f"Unexpected error editing message: {e}")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    # Clear any temporary data stored in user_data for any conversation
    keys_to_clear = [
        "temp_number",
        "delete_candidates",
    ]
    for key in keys_to_clear:
        if key in context.user_data:
            del context.user_data[key]

    await update.message.reply_text("Operation cancelled.")
    return ConversationHandler.END


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(f"Hello {update.effective_user.first_name}")


# Helper function to escape MarkdownV2 characters
def escape_markdown(text: str) -> str:
    """Helper function to escape telegram MarkdownV2 characters."""
    text = str(text)
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return "".join(f"\\{char}" if char in escape_chars else char for char in text)


# Helper function to format the student list and create keyboard
def format_student_list(
    students: list, sort_order: str
) -> tuple[str, InlineKeyboardMarkup]:
    """Formats the student list as a Markdown table and creates sorting buttons."""
    if not students:
        # Escape the message in case it contains special characters
        return escape_markdown("No students in the database."), None

    # --- Create Table Header ---
    header = f"`{'#':<4}{'ID':<15}{'Name':<20}`\n"  # Adjust widths as needed
    separator = f"`{'-' * 4}{'-' * 15}{'-' * 20}`\n"  # Separator line

    # --- Create Table Rows ---
    rows = []
    for i, student in enumerate(students, 1):
        # Escape each part *before* formatting
        num_str = escape_markdown(i)
        id_str = escape_markdown(student["student_number"])
        name_str = escape_markdown(student["student_name"])
        id_str = id_str[:15]
        name_str = name_str[:20]
        rows.append(f"`{num_str:<4}{id_str:<15}{name_str:<20}`")

    # --- Create Title ---
    # Escape the sort_order part before including it in the f-string
    escaped_sort_order = escape_markdown(sort_order.replace("_", " "))
    title = "*Students List* \\(Sorted by " + escaped_sort_order + "\\)\n\n"

    message_text = title + header + separator + "\n".join(rows)

    # --- Create Inline Keyboard for Sorting ---
    keyboard = [
        [
            InlineKeyboardButton(
                f"Sort by ID {'✅' if sort_order == 'student_number' else ''}",
                callback_data="list_sort_student_number",
            ),
            InlineKeyboardButton(
                f"Sort by Name {'✅' if sort_order == 'student_name' else ''}",
                callback_data="list_sort_student_name",
            ),
        ],
        # Add pagination buttons here later if needed
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    return message_text, reply_markup


async def delete_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the delete conversation."""
    await update.message.reply_text(
        "Please enter the number or name of the student you want to delete."
    )
    return WAITING_FOR_DELETE_IDENTIFIER


async def handle_delete_identifier(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles receiving the student identifier (name or number) for deletion."""
    identifier = update.message.text
    user_id = update.effective_user.id
    db = context.bot_data["db"]

    # Find potential matches
    results = db.find_students(user_id, identifier)

    if not results:
        await update.message.reply_text(
            f"No student found matching '{escape_markdown(identifier)}'. Operation cancelled.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return ConversationHandler.END

    elif len(results) == 1:
        # Exactly one match found
        student_to_delete = results[0]
        student_number = student_to_delete["student_number"]
        student_name = student_to_delete["student_name"]

        if db.delete_student(user_id, student_number):
            await update.message.reply_text(
                f"Student deleted successfully:\n"
                f"Number: {escape_markdown(student_number)}\n"
                f"Name: {escape_markdown(student_name)}",
                parse_mode=ParseMode.MARKDOWN_V2,
            )
        else:
            # Should not happen if find_students found it, but good to handle
            await update.message.reply_text(
                "Could not delete the student. They might have been deleted already. Operation cancelled."
            )
        return ConversationHandler.END

    else:
        # Multiple matches found (must be by name)
        context.user_data["delete_candidates"] = {
            student["student_number"]: student["student_name"] for student in results
        }
        message = "Multiple students found matching that name\. Please reply with the exact student number you want to delete:\n\n"
        for number, name in context.user_data["delete_candidates"].items():
            message += (
                f"Number: `{escape_markdown(number)}`, Name: {escape_markdown(name)}\n"
            )

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN_V2)
        return WAITING_FOR_DELETE_CONFIRMATION_NUMBER


async def handle_delete_confirmation_number(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Handles receiving the specific student number after multiple matches were found."""
    number_to_delete = update.message.text
    user_id = update.effective_user.id
    db = context.bot_data["db"]
    delete_candidates = context.user_data.get("delete_candidates", {})

    if not number_to_delete.isdigit():
        await update.message.reply_text(
            "That's not a valid number. Please enter the number of the student to delete."
        )
        return WAITING_FOR_DELETE_CONFIRMATION_NUMBER  # Stay in this state

    if number_to_delete not in delete_candidates:
        await update.message.reply_text(
            "That number wasn't in the list of matches. Please enter a valid number from the list above, or /cancel."
        )
        return WAITING_FOR_DELETE_CONFIRMATION_NUMBER  # Stay in this state

    # Valid number confirmed
    student_name = delete_candidates.get(
        number_to_delete, "Unknown"
    )  # Get name for confirmation message

    if db.delete_student(user_id, number_to_delete):
        await update.message.reply_text(
            f"Student deleted successfully:\n"
            f"Number: {escape_markdown(number_to_delete)}\n"
            f"Name: {escape_markdown(student_name)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            "Could not delete the student. They might have been deleted already. Operation cancelled."
        )

    # Clean up temporary data
    if "delete_candidates" in context.user_data:
        del context.user_data["delete_candidates"]

    return ConversationHandler.END


# --- Main Function ---
def main():
    # Initialize the database instance
    # Ensure load_dotenv() is called *before* this line
    db = Database()

    # Build the Application
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Store the database instance in bot_data to access it in handlers
    app.bot_data["db"] = db

    # Add conversation handler for adding students
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

    delete_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("delete", delete_start)],
        states={
            WAITING_FOR_DELETE_IDENTIFIER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_delete_identifier
                )
            ],
            WAITING_FOR_DELETE_CONFIRMATION_NUMBER: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, handle_delete_confirmation_number
                )
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        # Optional: Add conversation timeout
        # conversation_timeout=300 # e.g., 5 minutes
    )

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(add_conv_handler)
    app.add_handler(delete_conv_handler)
    app.add_handler(CommandHandler("list", list_students))
    app.add_handler(CommandHandler("find", find_student))
    app.add_handler(CommandHandler("hello", hello))

    app.add_handler(CallbackQueryHandler(list_button_callback, pattern="^list_sort_"))

    # Start the bot (using polling)
    print("Bot is running...")
    app.run_polling()

    # Close the database connection when the bot stops
    db.close()


if __name__ == "__main__":
    load_dotenv()

    # try:
    #     asyncio.run(main())
    # except KeyboardInterrupt: # Handle Ctrl+C gracefully
    #     print("Bot stopped manually.")
    main()
