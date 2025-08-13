from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# Define states
TITLE, DESCRIPTION, QUESTIONS = range(3)

async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter the quiz title:")
    return TITLE

async def get_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['title'] = update.message.text
    await update.message.reply_text("Enter the quiz description:")
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['description'] = update.message.text
    context.user_data['questions'] = []
    await update.message.reply_text(
        "Send questions in this format:\n"
        "Question?/Option1 ✅/Option2/Option3/Option4\n"
        "Send /done when finished."
    )
    return QUESTIONS

async def add_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['questions'].append(update.message.text)
    await update.message.reply_text("Question added! Send another or /done when finished.")
    return QUESTIONS

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = context.user_data['title']
    description = context.user_data['description']
    questions = context.user_data['questions']

    html_content = f"<h1>{title}</h1><p>{description}</p><ol>"
    for q in questions:
        html_content += f"<li>{q}</li>"
    html_content += "</ol>"

    await update.message.reply_document(
        document=bytes(html_content, 'utf-8'),
        filename="quiz.html",
        caption="Your quiz is ready!"
    )

    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data='start_quiz')],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=title)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose an action:", reply_markup=reply_markup)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz creation canceled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newquiz', new_quiz)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            QUESTIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_question),
                CommandHandler('done', done)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
