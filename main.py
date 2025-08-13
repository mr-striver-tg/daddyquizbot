from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
import html

# Define states
TITLE, DESCRIPTION, QUESTIONS = range(3)

# Start /newquiz
def new_quiz(update: Update, context: CallbackContext):
    update.message.reply_text("Enter the quiz title:")
    return TITLE

# Get title
def get_title(update: Update, context: CallbackContext):
    context.user_data['title'] = update.message.text
    update.message.reply_text("Enter the quiz description:")
    return DESCRIPTION

# Get description
def get_description(update: Update, context: CallbackContext):
    context.user_data['description'] = update.message.text
    context.user_data['questions'] = []
    update.message.reply_text(
        "Send questions in this format:\n"
        "Question?/Option1 ✅/Option2/Option3/Option4\n"
        "Send /done when finished."
    )
    return QUESTIONS

# Add questions
def add_question(update: Update, context: CallbackContext):
    context.user_data['questions'].append(update.message.text)
    update.message.reply_text("Question added! Send another or /done when finished.")
    return QUESTIONS

# Finish quiz
def done(update: Update, context: CallbackContext):
    title = html.escape(context.user_data['title'])
    description = html.escape(context.user_data['description'])
    questions = context.user_data['questions']

    # Generate simple HTML for the quiz
    html_content = f"<h1>{title}</h1><p>{description}</p><ol>"
    for q in questions:
        html_content += f"<li>{html.escape(q)}</li>"
    html_content += "</ol>"

    # Send HTML as a file
    update.message.reply_document(
        document=bytes(html_content, 'utf-8'),
        filename="quiz.html",
        caption="Your quiz is ready!"
    )

    # Provide inline buttons like start quiz/share
    keyboard = [
        [InlineKeyboardButton("Start Quiz", callback_data='start_quiz')],
        [InlineKeyboardButton("Share Quiz", switch_inline_query=title)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Choose an action:", reply_markup=reply_markup)

    return ConversationHandler.END

# Cancel handler
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text("Quiz creation canceled.")
    return ConversationHandler.END

def main():
    updater = Updater("8266633263:AAEm8u_rjrSRENi52vmUWtAjL4RxsU_HsZU", use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('newquiz', new_quiz)],
        states={
            TITLE: [MessageHandler(Filters.text & ~Filters.command, get_title)],
            DESCRIPTION: [MessageHandler(Filters.text & ~Filters.command, get_description)],
            QUESTIONS: [
                MessageHandler(Filters.text & ~Filters.command, add_question),
                CommandHandler('done', done)
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
