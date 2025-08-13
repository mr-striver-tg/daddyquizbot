import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, filters,
    ContextTypes, CallbackQueryHandler
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# In-memory storage
quiz_storage = {}  # {quiz_id: {'title':..., 'description':..., 'questions':[...]} }
user_quiz_data = {}  # {user_id: {'state':..., 'current_quiz': {...}}}

# Bot token
BOT_TOKEN = "8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU"

# States
STATE_TITLE = 1
STATE_DESC = 2
STATE_QUESTION = 3

# Start new quiz
async def newquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_quiz_data[user_id] = {'state': STATE_TITLE, 'current_quiz': {'questions': []}}
    await update.message.reply_text("Please send the quiz title:")

# Handle messages based on state
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_quiz_data:
        await update.message.reply_text("Send /newquiz to start creating a quiz.")
        return

    user_data = user_quiz_data[user_id]
    state = user_data['state']
    text = update.message.text.strip()

    if state == STATE_TITLE:
        user_data['current_quiz']['title'] = text
        user_data['state'] = STATE_DESC
        await update.message.reply_text("Send the quiz description:")
    elif state == STATE_DESC:
        user_data['current_quiz']['description'] = text
        user_data['state'] = STATE_QUESTION
        await update.message.reply_text(
            "Send each question in this format:\n"
            "Question?/प्रश्न?\n"
            "️ Option1 ✅\n"
            "️ Option2\n"
            "️ Option3\n"
            "️ Option4\n"
            "Send /done when all questions are added."
        )
    elif state == STATE_QUESTION:
        if text.lower() == "/done":
            await send_quiz(update, context)
            del user_quiz_data[user_id]  # clear temp data
            return
        else:
            user_data['current_quiz']['questions'].append(text)
            await update.message.reply_text("Question added. Send next question or /done when finished.")

# Send quiz HTML and buttons
async def send_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    quiz_data = user_quiz_data[user_id]['current_quiz']
    quiz_id = str(uuid.uuid4())
    quiz_storage[quiz_id] = quiz_data

    # Generate HTML
    html_content = f"<html><head><title>{quiz_data['title']}</title></head><body>"
    html_content += f"<h1>{quiz_data['title']}</h1><p>{quiz_data['description']}</p>"
    for q in quiz_data['questions']:
        html_content += f"<p>{q}</p>"
    html_content += "</body></html>"

    file_name = f"{quiz_id}.html"
    with open(file_name, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Send HTML file
    await update.message.reply_document(open(file_name, "rb"))

    # Send inline buttons
    bot_username = context.bot.username
    buttons = [
        [InlineKeyboardButton("Start Quiz", url=f"https://t.me/{bot_username}?start={quiz_id}")],
        [InlineKeyboardButton("Start in Group", switch_inline_query=quiz_id)],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=quiz_id)]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Your quiz is ready! Use these options:", reply_markup=markup)

# Handle /start <quiz_id>
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        quiz_id = args[0]
        quiz = quiz_storage.get(quiz_id)
        if not quiz:
            await update.message.reply_text("Quiz not found.")
            return
        # Send quiz questions
        await update.message.reply_text(f"Starting Quiz: {quiz['title']}")
        for q in quiz['questions']:
            await update.message.reply_text(q)
    else:
        await update.message.reply_text("Welcome! Send /newquiz to create a quiz.")

# Main function
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("newquiz", newquiz))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot started...")
    app.run_polling()
