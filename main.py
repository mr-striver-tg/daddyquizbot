import logging
import uuid
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# In-memory storage
quizzes = {}
user_sessions = {}

# Start command with optional quiz_id argument
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if args:
        quiz_id = args[0]
        if quiz_id in quizzes:
            quiz = quizzes[quiz_id]
            keyboard = [
                [InlineKeyboardButton("Start Quiz (Private)", url=f"https://t.me/{context.bot.username}?start={quiz_id}")],
                [InlineKeyboardButton("Start in Group", switch_inline_query=quiz_id)],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"🎉 Quiz: {quiz['title']}\n\n{quiz['description']}",
                reply_markup=reply_markup
            )
            return
    await update.message.reply_text("Welcome! Use /newquiz to create a new quiz.")

# Begin new quiz
async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_sessions[user_id] = {"step": "title", "quiz": {"questions": []}}
    await update.message.reply_text("Enter the title of your quiz:")

# Handle text messages during quiz creation
async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    if user_id not in user_sessions:
        return

    session = user_sessions[user_id]
    quiz = session["quiz"]

    if session["step"] == "title":
        quiz["title"] = text
        session["step"] = "description"
        await update.message.reply_text("Enter the description of your quiz:")
    elif session["step"] == "description":
        quiz["description"] = text
        session["step"] = "question"
        await update.message.reply_text("Enter question in the format:\nQuestion? \nOption1 ✅\nOption2\nOption3\nOption4\nSend /done when finished.")
    elif session["step"] == "question":
        if text != "/done":
            quiz["questions"].append(text)
            await update.message.reply_text("Question added! Send next question or /done to finish.")
        else:
            # Finish quiz
            quiz_id = str(uuid.uuid4())
            quizzes[quiz_id] = quiz
            del user_sessions[user_id]

            # Save HTML
            html_file = f"/tmp/{quiz_id}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(f"<html><head><title>{quiz['title']}</title></head><body>")
                f.write(f"<h1>{quiz['title']}</h1><p>{quiz['description']}</p><ol>")
                for q in quiz["questions"]:
                    f.write(f"<li>{q}</li>")
                f.write("</ol></body></html>")

            keyboard = [
                [InlineKeyboardButton("Start Quiz (Private)", url=f"https://t.me/{context.bot.username}?start={quiz_id}")],
                [InlineKeyboardButton("Start in Group", switch_inline_query=quiz_id)],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_document(
                document=InputFile(html_file),
                filename=f"{quiz['title']}.html",
                caption="Your quiz is ready! You can start or share it using the buttons below.",
                reply_markup=reply_markup
            )

# Optional: Inline query handler for sharing in group
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    results = []
    if query in quizzes:
        quiz = quizzes[query]
        results.append(
            InlineQueryResultArticle(
                id=query,
                title=quiz["title"],
                input_message_content=InputTextMessageContent(f"Quiz: {quiz['title']}\n\n{quiz['description']}")
            )
        )
    await update.inline_query.answer(results)

# Main function
if __name__ == "__main__":
    app = ApplicationBuilder().token("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU").build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newquiz", new_quiz))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_handler(CallbackQueryHandler(lambda update, context: None))  # Placeholder if needed

    app.run_polling()
