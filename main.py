import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from io import BytesIO

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
TITLE, DESCRIPTION, QUESTIONS = range(3)

# Store quizzes in memory
quizzes = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /newquiz to create a quiz.")

# /newquiz starts conversation
async def newquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the title of your quiz:")
    return TITLE

# Get quiz title
async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Enter the description of your quiz:")
    return DESCRIPTION

# Get quiz description
async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    context.user_data['questions'] = []
    await update.message.reply_text(
        "Send your questions one by one in this format:\n"
        "Question?/प्रश्न?\n"
        "️ Option1 ✅\n"
        "️ Option2\n"
        "Once done, type /done"
    )
    return QUESTIONS

# Collect questions
async def get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['questions'].append(update.message.text)
    await update.message.reply_text("Question added! Send next or /done if finished.")
    return QUESTIONS

# Finish quiz
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data.get('title')
    description = context.user_data.get('description')
    questions = context.user_data.get('questions', [])

    if not questions:
        await update.message.reply_text("No questions added. Quiz cancelled.")
        return ConversationHandler.END

    # Store quiz
    quiz_id = len(quizzes) + 1
    quizzes[quiz_id] = {
        'title': title,
        'description': description,
        'questions': questions,
    }

    # Generate HTML
    html_content = f"<html><head><meta charset='UTF-8'><title>{title}</title></head><body>"
    html_content += f"<h1>{title}</h1><p>{description}</p><ol>"
    for q in questions:
        html_content += f"<li><pre>{q}</pre></li>"
    html_content += "</ol></body></html>"

    # Send HTML file
    bio = BytesIO()
    bio.name = f"{title}.html"
    bio.write(html_content.encode('utf-8'))
    bio.seek(0)
    await update.message.reply_document(document=bio, filename=f"{title}.html")

    # Create inline buttons
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data=f"start_{quiz_id}")],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=title)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Quiz '{title}' created with {len(questions)} questions!",
        reply_markup=reply_markup
    )

    context.user_data.clear()
    return ConversationHandler.END

# Handle inline button presses
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("start_"):
        quiz_id = int(data.split("_")[1])
        quiz = quizzes.get(quiz_id)
        if quiz:
            msg = f"Starting Quiz: {quiz['title']}\n\n"
            for q in quiz['questions']:
                msg += f"{q}\n\n"
            await query.message.reply_text(msg)

# Cancel creation
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz creation cancelled.")
    context.user_data.clear()
    return ConversationHandler.END

if __name__ == "__main__":
    TOKEN = "8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU"
    app = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("newquiz", newquiz)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            QUESTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("done", done)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot started...")
    app.run_polling()
