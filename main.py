from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# Dictionary to store user quiz data temporarily
user_quiz_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /newquiz to create a quiz.")

# Step 1: New quiz
async def newquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_quiz_data[user_id] = {"step": "title", "quiz": {"title": "", "description": "", "questions": []}}
    await update.message.reply_text("Enter the quiz title:")

# Step 2+: Handle messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in user_quiz_data:
        await update.message.reply_text("Use /newquiz to start a quiz first.")
        return

    step = user_quiz_data[user_id]["step"]
    text = update.message.text

    if step == "title":
        user_quiz_data[user_id]["quiz"]["title"] = text
        user_quiz_data[user_id]["step"] = "description"
        await update.message.reply_text("Enter the quiz description:")
    elif step == "description":
        user_quiz_data[user_id]["quiz"]["description"] = text
        user_quiz_data[user_id]["step"] = "questions"
        await update.message.reply_text(
            "Now send questions in this format:\nQuestion?/प्रश्न?\n️ Option1 ✅\n️ Option2\nSend /done when finished."
        )
    elif step == "questions":
        if text == "/done":
            user_quiz_data[user_id]["step"] = "done"
            quiz = user_quiz_data[user_id]["quiz"]
            await send_quiz_summary(update, quiz)
        else:
            user_quiz_data[user_id]["quiz"]["questions"].append(text)
            await update.message.reply_text("Question added. Send next question or /done if finished.")

async def send_quiz_summary(update: Update, quiz):
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data='start_quiz')],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=quiz["title"])]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    summary = f"Quiz '{quiz['title']}' ready with {len(quiz['questions'])} questions!"
    await update.message.reply_text(summary, reply_markup=reply_markup)

# Handle button presses
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "start_quiz":
        quiz = user_quiz_data.get(user_id, {}).get("quiz")
        if not quiz:
            await query.message.reply_text("No quiz found. Use /newquiz first.")
            return

        # Send questions one by one
        for i, q in enumerate(quiz["questions"], start=1):
            await query.message.reply_text(f"Q{i}: {q}")

# Build the application
app = ApplicationBuilder().token("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("newquiz", newquiz))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(button_callback))

app.run_polling()
