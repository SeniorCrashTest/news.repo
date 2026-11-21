"""Радар Європи: Telegram-бот для черновиков и ручного подтверждения публикаций."""
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

import telebot
from telebot import types
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "@UA_in_DE_news").strip()
OWNER_ID_RAW = os.getenv("OWNER_ID", "").strip()

if not BOT_TOKEN:
    raise SystemExit("Не указан BOT_TOKEN в файле .env")
if not CHANNEL_ID:
    raise SystemExit("Не указан CHANNEL_ID в файле .env")
if OWNER_ID_RAW and not OWNER_ID_RAW.isdecimal():
    raise SystemExit("OWNER_ID должен быть числом (узнай его командой /id)")

OWNER_ID = int(OWNER_ID_RAW) if OWNER_ID_RAW else None
MAX_POST_LENGTH = 3500
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("radar")

bot = telebot.TeleBot(BOT_TOKEN, threaded=True)
db_lock = threading.Lock()
db = sqlite3.connect(ROOT / "drafts.sqlite3", check_same_thread=False)
with db_lock:
    db.execute(
        """CREATE TABLE IF NOT EXISTS drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        )"""
    )
    db.commit()


def is_owner(message_or_call):
    sender = message_or_call.from_user
    return OWNER_ID is not None and sender is not None and sender.id == OWNER_ID


def require_owner(message):
    if message.chat.type != "private":
        return False
    if OWNER_ID is None:
        bot.reply_to(
            message,
            "Спочатку надішли /id, потім додай це число до OWNER_ID у .env "
            "та перезапусти бота."
        )
        return False
    if not is_owner(message):
        bot.reply_to(message, "Доступ заборонено.")
        return False
    return True


def create_draft(text):
    with db_lock:
        cursor = db.execute(
            "INSERT INTO drafts (text, status, created_at) VALUES (?, 'pending', ?)",
            (text, datetime.now(timezone.utc).isoformat()),
        )
        db.commit()
        return cursor.lastrowid


def load_draft(draft_id):
    with db_lock:
        row = db.execute(
            "SELECT text, status FROM drafts WHERE id = ?", (draft_id,)
        ).fetchone()
    return row


def set_status_if_pending(draft_id, new_status):
    with db_lock:
        result = db.execute(
            "UPDATE drafts SET status = ? WHERE id = ? AND status = 'pending'",
            (new_status, draft_id),
        )
        db.commit()
        return result.rowcount == 1


def restore_pending(draft_id):
    with db_lock:
        db.execute(
            "UPDATE drafts SET status = 'pending' WHERE id = ? AND status = 'sending'",
            (draft_id,),
        )
        db.commit()


def draft_keyboard(draft_id):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton(
            "✅ Опублікувати", callback_data=f"publish:{draft_id}"
        ),
        types.InlineKeyboardButton(
            "🗂 В архів (тихо)", callback_data=f"archive:{draft_id}"
        ),
        types.InlineKeyboardButton(
            "❌ Відхилити", callback_data=f"reject:{draft_id}"
        ),
    )
    return keyboard


def preview_draft(chat_id, text):
    text = text.strip()
    if not text:
        bot.send_message(chat_id, "Надішли текст майбутньої публікації.")
        return
    if len(text) > MAX_POST_LENGTH:
        bot.send_message(
            chat_id,
            f"Текст задовгий: {len(text)} символів. Максимум {MAX_POST_LENGTH}.",
        )
        return
    draft_id = create_draft(text)
    bot.send_message(
        chat_id,
        f"📝 Чернетка #{draft_id}\n\n{text}",
        reply_markup=draft_keyboard(draft_id),
        disable_web_page_preview=True,
    )


@bot.message_handler(commands=["id"])
def show_id(message):
    if message.chat.type == "private":
        bot.reply_to(message, f"Твій Telegram ID: {message.from_user.id}")


@bot.message_handler(commands=["start", "help"])
def show_help(message):
    if not require_owner(message):
        return
    bot.reply_to(
        message,
        "📡 Радар Європи\n\n"
        "Надішли мені текст — я створю чернетку з кнопками.\n"
        "/test — тестова чернетка\n"
        "/id — дізнатися Telegram ID\n\n"
        "Пост у канал потрапить ТІЛЬКИ після натискання кнопки."
    )


@bot.message_handler(commands=["test"])
def test_draft(message):
    if not require_owner(message):
        return
    preview_draft(
        message.chat.id,
        "🧪 ТЕСТ\n\n"
        "Перевірка системи публікації «Радар Європи | Безпека».\n"
        "Це тестове повідомлення, не новина."
    )


@bot.message_handler(content_types=["text"])
def draft_from_message(message):
    if not require_owner(message):
        return
    if message.text.startswith("/"):
        bot.reply_to(message, "Невідома команда. Напиши /help.")
        return
    preview_draft(message.chat.id, message.text)


@bot.callback_query_handler(func=lambda call: True)
def handle_choice(call):
    if call.message.chat.type != "private" or not is_owner(call):
        bot.answer_callback_query(call.id, "Доступ заборонено.", show_alert=True)
        return

    try:
        action, raw_id = call.data.split(":", 1)
        draft_id = int(raw_id)
    except (AttributeError, ValueError):
        bot.answer_callback_query(call.id, "Невідома дія.")
        return

    if action not in ("publish", "archive", "reject"):
        bot.answer_callback_query(call.id, "Невідома дія.")
        return

    item = load_draft(draft_id)
    if item is None or item[1] != "pending":
        bot.answer_callback_query(call.id, "Ця чернетка вже оброблена.")
        return

    if action == "reject":
        if set_status_if_pending(draft_id, "rejected"):
            bot.answer_callback_query(call.id, "Чернетку відхилено.")
            try:
                bot.edit_message_reply_markup(
                    call.message.chat.id, call.message.message_id, reply_markup=None
                )
            except Exception:
                log.exception("Не вдалося прибрати кнопки")
            bot.send_message(call.message.chat.id, f"❌ Чернетку #{draft_id} відхилено.")
        else:
            bot.answer_callback_query(call.id, "Чернетку вже оброблено.")
        return

    if not set_status_if_pending(draft_id, "sending"):
        bot.answer_callback_query(call.id, "Чернетку вже оброблено.")
        return

    text = item[0]
    if action == "archive" and not text.lstrip().upper().startswith("АРХІВ"):
        text = "АРХІВ\n\n" + text

    try:
        result = bot.send_message(
            CHANNEL_ID,
            text,
            disable_notification=(action == "archive"),
            disable_web_page_preview=True,
        )
    except Exception as exc:
        restore_pending(draft_id)
        log.exception("Помилка публікації")
        bot.answer_callback_query(call.id, "Публікація не вдалася.", show_alert=True)
        bot.send_message(
            call.message.chat.id,
            f"Не вдалося опублікувати чернетку #{draft_id}.\n"
            f"Перевір доступ бота до каналу та журнал програми.\n"
            f"{type(exc).__name__}: {str(exc)[:300]}"
        )
        return

    with db_lock:
        db.execute(
            "UPDATE drafts SET status = ? WHERE id = ? AND status = 'sending'",
            ("archived" if action == "archive" else "published", draft_id),
        )
        db.commit()

    bot.answer_callback_query(call.id, "Опубліковано!")
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        log.exception("Не вдалося прибрати кнопки")

    bot.send_message(
        call.message.chat.id,
        f"✅ Чернетку #{draft_id} опубліковано у {CHANNEL_ID} "
        f"(повідомлення #{result.message_id})."
    )
    log.info("Опубліковано draft=%s message=%s action=%s", draft_id, result.message_id, action)


if __name__ == "__main__":
    log.info("Бот запускається. Канал: %s. OWNER_ID вказано: %s", CHANNEL_ID, bool(OWNER_ID))
    if OWNER_ID is None:
        log.warning("Вказати OWNER_ID у .env після отримання /id; публікація заблокована.")
    bot.infinity_polling(timeout=30, long_polling_timeout=25, skip_pending=True)
