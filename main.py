import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Conversation states
TITLE, DESCRIPTION, QUESTION = range(3)

# Temporary storage for user quizzes
user_temp = {}
active_quiz = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /newquiz to create a new quiz."
    )

# Start new quiz
async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id] = {'questions': []}
    await update.message.reply_text("Send me the quiz title:")
    return TITLE

# Receive title
async def receive_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id]['title'] = update.message.text.strip()
    await update.message.reply_text("Send me the quiz description:")
    return DESCRIPTION

# Receive description
async def receive_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp[user_id]['description'] = update.message.text.strip()
    await update.message.reply_text(
        "Send questions in this format:\n"
        "Question text\n"
        "️ Option1\n"
        "️ Option2 ✅ (mark correct with ✅)\n"
        "️ Option3\n"
        "Send /done when finished adding questions."
    )
    return QUESTION

# Receive questions
async def receive_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    if text.lower() == "/done":
        return await finish_quiz(update, context)

    lines = text.split("\n")
    if len(lines) < 2:
        await update.message.reply_text("Please follow the correct format for questions.")
        return QUESTION

    question_text = lines[0]
    options = []
    correct_option = None

    for line in lines[1:]:
        if line.startswith("️ "):
            opt = line[2:].replace(" ✅", "").strip()
            options.append(opt)
            if "✅" in line:
                correct_option = opt

    if not correct_option:
        await update.message.reply_text("Please mark one correct option with ✅")
        return QUESTION

    user_temp[user_id]['questions'].append({
        'question': question_text,
        'options': options,
        'answer': correct_option
    })

    await update.message.reply_text("Question added! Send next question or /done if finished.")
    return QUESTION

# Finish quiz
async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    quiz = user_temp.get(user_id)
    if not quiz or not quiz.get('questions'):
        await update.message.reply_text("No questions found. Add at least one question.")
        return QUESTION

    # Generate HTML file
    html_content = f"<h1>{quiz['title']}</h1>\n<p>{quiz['description']}</p>\n<ol>"
    for q in quiz['questions']:
        html_content += f"<li>{q['question']}<ul>"
        for opt in q['options']:
            mark = "✅" if opt == q['answer'] else ""
            html_content += f"<li>{opt} {mark}</li>"
        html_content += "</ul></li>"
    html_content += "</ol>"

    file_io = io.BytesIO(html_content.encode("utf-8"))
    file_io.seek(0)
    await update.message.reply_document(document=InputFile(file_io, filename="quiz.html"))

    # Inline buttons
    active_quiz[user_id] = quiz
    buttons = [
        [InlineKeyboardButton("Start Quiz", callback_data=f"start_quiz:{user_id}")],
        [InlineKeyboardButton("Start in Group", callback_data=f"start_group:{user_id}")],
        [InlineKeyboardButton("Share Quiz", callback_data=f"share_quiz:{user_id}")]
    ]
    await update.message.reply_text("Quiz ready!", reply_markup=InlineKeyboardMarkup(buttons))

    # Clear temporary storage
    user_temp.pop(user_id, None)
    return ConversationHandler.END

# Handle inline button callbacks
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = int(data.split(":")[1])
    quiz = active_quiz.get(user_id)

    if not quiz:
        await query.edit_message_text("Quiz not found or expired.")
        return

    if data.startswith("start_quiz"):
        await query.edit_message_text(f"Starting quiz: {quiz['title']}")
    elif data.startswith("start_group"):
        await query.edit_message_text(f"Start this quiz in a group: {quiz['title']}")
    elif data.startswith("share_quiz"):
        await query.edit_message_text(f"Share this quiz with others!")

# Cancel handler
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_temp.pop(user_id, None)
    await update.message.reply_text("Quiz creation cancelled.")
    return ConversationHandler.END

# Main
app = ApplicationBuilder().token("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU").build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler("newquiz", new_quiz)],
    states={
        TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_title)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_description)],
        QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_question)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(conv_handler)
app.add_handler(CallbackQueryHandler(button_handler))

app.run_polling()
