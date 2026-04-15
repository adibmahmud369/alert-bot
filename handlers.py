from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes

import storage


def menu(uid):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Alert", callback_data="add")],
        [InlineKeyboardButton("📋 Alerts", callback_data="view")],
        [InlineKeyboardButton("🔴 ON/OFF", callback_data="toggle")]
    ])


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    await update.message.reply_text("Bot Ready 🚀", reply_markup=menu(uid))


async def toggle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(update.effective_user.id)

    cur = storage.is_enabled(uid)
    storage.set_enabled(uid, not cur)

    await q.answer("Toggled")
    await q.edit_message_text("Updated", reply_markup=menu(uid))


def register_handlers(app):
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(toggle, pattern="toggle"))