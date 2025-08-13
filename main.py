from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler, CallbackQueryHandler
import io

# Conversation states
TITLE, DESCRIPTION, QUESTION = range(3)

# Temporary storage
user_temp = {}
active_quiz = {}

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Welcome! Use /newquiz to create a quiz.")

# /newquiz command
async def newquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id] = {'questions': []}
    await update.message.reply_text("Send me the quiz title:")
    return TITLE

# Receive quiz title
async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id]['title'] = update.message.text
    await update.message.reply_text("Send me the quiz description:")
    return DESCRIPTION

# Receive quiz description
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id]['description'] = update.message.text
    await update.message.reply_text(
        "Now send the first question in this format:\n\n"
        "Question?/प्रश्न?\n"
        "️ Option1 ✅\n"
        "️ Option2\n"
        "️ Option3\n"
        "️ Option4\n"
        "Ex: provided by @apna_quiz & @apna_pdf\n\n"
        "Send /done when all questions are added."
    )
    return QUESTION

# Receive questions
async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text.strip() == "/done":
        return await finish_quiz(update, context)

    # Parse question
    lines = text.split("\n")
    question_text = lines[0]
    options = []
    correct_option = None
    for line in lines[1:]:
        if line.startswith("️ "):
            opt = line[2:].replace(" ✅", "")
            options.append(opt)
            if "✅" in line:
                correct_option = opt

    user_temp[user_id]['questions'].append({
        'question': question_text,
        'options': options,
        'answer': correct_option
    })

    await update.message.reply_text(f"Question added! Send next question or /done if finished.")
    return QUESTION

# Finish quiz, send HTML, and show buttons
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    quiz = user_temp[user_id]

    html_content = f"<h1>{quiz['title']}</h1>\n<p>{quiz['description']}</p>\n<ol>"
    for q in quiz['questions']:
        html_content += f"<li>{q['question']}<ul>"
        for opt in q['options']:
            mark = "✅" if opt == q['answer'] else ""
            html_content += f"<li>{opt} {mark}</li>"
        html_content += "</ul></li>"
    html_content += "</ol>"

    file_io = io.BytesIO()
    file_io.write(html_content.encode("utf-8"))
    file_io.seek(0)
    await update.message.reply_document(document=InputFile(file_io, filename="quiz.html"))

    # Save active quiz for buttons
    active_quiz[user_id] = quiz
    buttons = [
        [InlineKeyboardButton("Start Quiz", callback_data=f"start_quiz:{user_id}")],
        [InlineKeyboardButton("Start in Group", callback_data=f"start_group:{user_id}")],
        [InlineKeyboardButton("Share Quiz", callback_data=f"share_quiz:{user_id}")]
    ]
    await update.message.reply_text("Quiz ready!", reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END

# Handle buttons
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split(":")[1])
    quiz = active_quiz.get(user_id)
    if not quiz:
        await query.edit_message_text("Quiz expired or not found.")
        return

    if data.startswith("start_quiz"):
        # Send questions one by one
        for q in quiz['questions']:
            text = f"{q['question']}\n"
            for i, opt in enumerate(q['options'], start=1):
                text += f"️ {i}. {opt}\n"
            await query.message.reply_text(text)
        await query.message.reply_text("Quiz completed!")

    elif data.startswith("start_group"):
        await query.message.reply_text("Forward this message to a group to start the quiz there.")

    elif data.startswith("share_quiz"):
        await query.message.reply_text(f"Share this quiz link: https://t.me/yourbotusername?start={user_id}")

# Cancel command
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz creation canceled.")
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN_HERE").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newquiz', newquiz)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
            QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()
