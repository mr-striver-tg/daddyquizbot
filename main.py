#!/usr/bin/env python3
"""
Merged Quiz Bot (HTML Export + Telegram Polls)
Adapted for deployment on Koyeb (uses BOT_TOKEN from environment)
"""
import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any

from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ConversationHandler, CallbackQueryHandler, ContextTypes, filters
)

# =========================
# CONFIGURATION
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")

# ---------------- Logging ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- Paths ----------------
BASE_DIR = Path("/tmp")  # Koyeb container writable directory
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"
TEMPLATE_PATH = Path("./quiz_template.html")  # should be included in repo
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ---------------- Models ----------------
@dataclass
class Question:
    q: str
    options: List[str]
    correctIndex: int

@dataclass
class Quiz:
    title: str = "Untitled Quiz"
    questions: List[Question] = field(default_factory=list)

# ---------------- Storage ----------------
def user_store_path(user_id: int) -> Path:
    return DATA_DIR / f"{user_id}.json"

def load_quiz(user_id: int) -> Quiz:
    p = user_store_path(user_id)
    if p.exists():
        raw = json.loads(p.read_text(encoding="utf-8"))
        qs = [Question(**qq) for qq in raw.get("questions", [])]
        return Quiz(title=raw.get("title", "Untitled Quiz"), questions=qs)
    return Quiz()

def save_quiz(user_id: int, quiz: Quiz) -> None:
    p = user_store_path(user_id)
    payload = {
        "title": quiz.title,
        "questions": [q.__dict__ for q in quiz.questions]
    }
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- HTML rendering ----------------
def sanitize_filename(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip()
    s = re.sub(r"[\s-]+", "_", s)
    return s or "quiz"

def render_html(quiz: Quiz, out_dir: Path) -> Path:
    if not TEMPLATE_PATH.exists():
        raise FileNotFoundError("quiz_template.html is missing.")
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    title = quiz.title
    questions_json = json.dumps([q.__dict__ for q in quiz.questions], ensure_ascii=False)
    html_str = template.replace("__QUIZ_TITLE__", title).replace("__QUESTIONS_JSON__", questions_json)
    fname = sanitize_filename(f"{title}.html")
    out_path = out_dir / fname
    out_path.write_text(html_str, encoding="utf-8")
    return out_path

# ---------------- Conversation states ----------------
ASK_TITLE, ASK_Q, ASK_O1, ASK_O2, ASK_O3, ASK_O4, ASK_CORRECT = range(7)
user_temp: Dict[int, Dict[str, Any]] = {}
user_mode: Dict[int, bool] = {}

# ---------------- Handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Standard Quiz", callback_data='standard')],
        [InlineKeyboardButton("Anonymous Quiz", callback_data='anonymous')],
    ]
    text = (
        "👋 Welcome to the Quiz Bot!\n\n"
        "Pick how Telegram polls should be posted (does not affect HTML export):\n"
        "• Standard Quiz → shows participants' names\n"
        "• Anonymous Quiz → hides names\n\n"
        "You can also build an offline HTML quiz with these commands:\n"
        "  /newquiz — set quiz title\n"
        "  /addq — add a question (4 options)\n"
        "  /list — preview\n"
        "  /export — get HTML file\n"
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.effective_chat.send_message(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_mode[user_id] = (query.data == "anonymous")
    mode_text = "🟢 Anonymous mode ON." if user_mode[user_id] else "🔵 Standard mode ON."
    await query.edit_message_text(f"{mode_text}\nNow send your question(s) or use /addq to build HTML.")

def parse_quiz_blocks(text: str):
    if not text or '✅' not in text or 'Ex:' not in text:
        return []
    quiz_blocks = re.findall(
        r"(.*?(?:\n.*?){4,5})\s*Ex:\s*(.+?)(?=\n(?:\n|.*?Ex:)|$)",
        text.strip(),
        re.DOTALL
    )
    parsed_quizzes = []
    for block, explanation in quiz_blocks:
        lines = [line.strip("️ ").strip() for line in block.strip().split("\n") if line.strip()]
        if len(lines) < 5: continue
        question = lines[0]
        options, correct_option_id = [], None
        for idx, option in enumerate(lines[1:]):
            if "✅" in option:
                correct_option_id = idx
                option = option.replace("✅", "").strip()
            options.append(option)
        if correct_option_id is not None:
            parsed_quizzes.append({
                "question": question,
                "options": options,
                "correct_option_id": correct_option_id,
                "explanation": explanation.strip()
            })
    return parsed_quizzes

async def handle_quick_quiz_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text or update.message.text.startswith('/'):
        return
    user_id = update.message.from_user.id
    is_anonymous = user_mode.get(user_id, False)
    quizzes = parse_quiz_blocks(update.message.text)
    for quiz in quizzes:
        try:
            await context.bot.send_poll(
                chat_id=update.effective_chat.id,
                question=quiz["question"],
                options=quiz["options"],
                type="quiz",
                correct_option_id=quiz["correct_option_id"],
                explanation=quiz["explanation"],
                is_anonymous=is_anonymous
            )
        except Exception as e:
            logger.exception("Failed to send poll: %s", e)

# ---------------- HTML quiz builder handlers ----------------
async def cmd_newquiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Send me the *title*.", parse_mode="HTML")
    return ASK_TITLE

async def got_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    quiz = Quiz(title=update.message.text.strip(), questions=[])
    save_quiz(user_id, quiz)
    await update.message.reply_text(f"📚 Title set to: <b>{quiz.title}</b>", parse_mode="HTML")
    return ConversationHandler.END

async def cmd_addq(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not user_store_path(user_id).exists():
        save_quiz(user_id, Quiz())
    user_temp[user_id] = {"q": None, "opts": [], "correct": None}
    await update.message.reply_text("📝 Send the *question text*.", parse_mode="HTML")
    return ASK_Q

async def got_q(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_temp[uid]["q"] = update.message.text.strip()
    await update.message.reply_text("Option 1:")
    return ASK_O1

async def got_o1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_temp[uid]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Option 2:")
    return ASK_O2

async def got_o2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_temp[uid]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Option 3:")
    return ASK_O3

async def got_o3(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_temp[uid]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Option 4:")
    return ASK_O4

async def got_o4(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_temp[uid]["opts"].append(update.message.text.strip())
    await update.message.reply_text("Which option number is correct? (1-4)")
    return ASK_CORRECT

async def got_correct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    try:
        idx = int(update.message.text.strip()) - 1
        if idx not in (0,1,2,3):
            raise ValueError
    except Exception:
        await update.message.reply_text("Please send a number 1-4.")
        return ASK_CORRECT

    temp = user_temp.get(uid)
    if not temp or len(temp["opts"]) != 4 or not temp["q"]:
        await update.message.reply_text("Something went wrong. Try /addq again.")
        return ConversationHandler.END

    temp["correct"] = idx
    quiz = load_quiz(uid)
    quiz.questions.append(Question(q=temp["q"], options=temp["opts"], correctIndex=temp["correct"]))
    save_quiz(uid, quiz)
    user_temp.pop(uid, None)
    await update.message.reply_text("✅ Question added!\nUse /addq to add another or /export to download.")
    return ConversationHandler.END

async def cmd_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    quiz = load_quiz(uid)
    if not quiz.questions:
        await update.message.reply_text("No questions yet. Use /addq to add one.")
        return
    lines = [f"<b>{quiz.title}</b>"]
    for i, q in enumerate(quiz.questions,1):
        lines.append(f"\n{i}. {q.q}")
        for j,opt in enumerate(q.options,1):
            mark = "✅" if (j-1)==q.correctIndex else "•"
            lines.append(f"   {mark} {j}) {opt}")
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")

async def cmd_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    quiz = load_quiz(uid)
    if not quiz.questions:
        await update.message.reply_text("Add some questions first.")
        return
    out_path = render_html(quiz, EXPORTS_DIR)
    await update.message.reply_document(document=InputFile(str(out_path)))
    await update.message.reply_text(f"📝 Exported to HTML file: {out_path.name}")

# ---------------- MAIN ----------------
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("export", cmd_export))

    # HTML Quiz Builder
    quiz_conv = ConversationHandler(
        entry_points=[CommandHandler("newquiz", cmd_newquiz),
                      CommandHandler("addq", cmd_addq)],
        states={
            ASK_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_title)],
            ASK_Q: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_q)],
            ASK_O1: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_o1)],
            ASK_O2: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_o2)],
            ASK_O3: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_o3)],
            ASK_O4: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_o4)],
            ASK_CORRECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, got_correct)],
        },
        fallbacks=[]
    )
    app.add_handler(quiz_conv)

    # Buttons
    app.add_handler(CallbackQueryHandler(button_handler))

    # Quick quiz submission
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_quick_quiz_submission))

    logger.info("✅ Quiz Bot is running.")
    app.run_polling()

if __name__ == "__main__":
    main()
