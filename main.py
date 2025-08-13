import os
import logging
from uuid import uuid4
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Storage for quizzes
quizzes = {}
user_states = {}

# ------------------- Handlers ------------------- #

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /newquiz to create a new quiz."
    )

async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_states[user_id] = {"state": "title", "quiz": {"questions": []}}
    await update.message.reply_text("Please enter the title of your quiz:")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_states:
        await update.message.reply_text("Use /newquiz to start creating a quiz.")
        return

    state = user_states[user_id]["state"]
    quiz = user_states[user_id]["quiz"]

    if state == "title":
        quiz["title"] = update.message.text
        user_states[user_id]["state"] = "description"
        await update.message.reply_text("Enter the description for your quiz:")
    elif state == "description":
        quiz["description"] = update.message.text
        user_states[user_id]["state"] = "question"
        await update.message.reply_text(
            "Send your first question in this format:\n\n"
            "Question?/प्रश्न?\n"
            "✅ Option1/विकल्प1\n"
            "Option2/विकल्प2\n"
            "Option3/विकल्प3\n"
            "Option4/विकल्प4\n"
            "✅ mark correct option(s)"
        )
    elif state == "question":
        quiz["questions"].append(update.message.text)
        await update.message.reply_text(
            "Question added! Send another question or type /done if finished."
        )

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_states:
        await update.message.reply_text("You have no quiz in progress. Use /newquiz.")
        return

    quiz = user_states[user_id]["quiz"]
    quiz_id = str(uuid4())
    quizzes[quiz_id] = quiz

    # Generate HTML
    html_content = f"<html><head><title>{quiz['title']}</title></head><body>"
    html_content += f"<h1>{quiz['title']}</h1><p>{quiz['description']}</p><ol>"
    for q in quiz["questions"]:
        html_content += f"<li>{q.replace(chr(10), '<br>')}</li>"
    html_content += "</ol></body></html>"

    file_path = f"{quiz_id}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    # Inline buttons
    keyboard = [
        [
            InlineKeyboardButton("Start Quiz (Private)", url=f"https://t.me/{context.bot.username}?start={quiz_id}"),
            InlineKeyboardButton("Start in Group", url=f"https://t.me/{context.bot.username}?startgroup={quiz_id}")
        ],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=quiz_id)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_document(document=InputFile(file_path), reply_markup=reply_markup)
    await update.message.reply_text("Quiz ready! Use buttons below to start or share.")
    
    # Cleanup
    del user_states[user_id]

# ------------------- Main ------------------- #
def main():
    token = os.environ.get("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newquiz", new_quiz))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
