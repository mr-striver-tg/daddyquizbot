from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler
import os

# Stages
TITLE, DESCRIPTION, QUESTIONS = range(3)

# In-memory storage
user_quizzes = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /newquiz to create a quiz."
    )

async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the quiz title:")
    user_quizzes[update.effective_user.id] = {"questions": []}
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_quizzes[update.effective_user.id]["title"] = update.message.text
    await update.message.reply_text("Enter the quiz description:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_quizzes[update.effective_user.id]["description"] = update.message.text
    await update.message.reply_text(
        "Now send each question in this format:\n"
        "Question?/प्रश्न?\n"
        "️ Option1 ✅\n"
        "️ Option2\n"
        "️ Option3\n"
        "Send /done when finished adding questions."
    )
    return QUESTIONS

async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_quizzes[update.effective_user.id]["questions"].append(text)
    await update.message.reply_text("Question added! Add another or send /done.")
    return QUESTIONS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = user_quizzes.get(update.effective_user.id)
    if not user_data or not user_data.get("questions"):
        await update.message.reply_text("No questions were added. Use /newquiz to start.")
        return ConversationHandler.END

    # Create HTML file
    html_content = f"<h1>{user_data['title']}</h1>\n<p>{user_data['description']}</p>\n<ol>\n"
    for q in user_data["questions"]:
        html_content += f"<li>{q.replace('️', '').replace('✅', '(Correct)')}</li>\n"
    html_content += "</ol>"

    html_file_path = f"{update.effective_user.id}_quiz.html"
    with open(html_file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Send HTML file
    await update.message.reply_document(document=InputFile(html_file_path))

    # Add Start/Share buttons
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data="start_quiz")],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=user_data["title"])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Quiz ready!", reply_markup=reply_markup)

    # Clean up memory
    user_quizzes.pop(update.effective_user.id, None)
    os.remove(html_file_path)
    return ConversationHandler.END

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "start_quiz":
        await query.edit_message_text("Starting quiz... (poll sending not implemented yet)")

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz creation canceled.")
    user_quizzes.pop(update.effective_user.id, None)
    return ConversationHandler.END

app = ApplicationBuilder().token("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("newquiz", new_quiz)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
        QUESTIONS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, add_question),
            CommandHandler("done", done)
        ],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(MessageHandler(filters.COMMAND, lambda u, c: u.message.reply_text("Unknown command.")))
app.add_handler(MessageHandler(filters.TEXT, lambda u, c: u.message.reply_text("Send /newquiz to start a quiz.")))
app.add_handler(CommandHandler("done", done))
app.add_handler(app.builder.callback_query_handler(button_handler))

app.run_polling()
