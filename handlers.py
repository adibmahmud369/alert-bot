"""
Handlers — সব বাটন, কথোপকথন, কমান্ড
Note feature সহ + OFF CLEAN DELETE SYSTEM
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ConversationHandler, MessageHandler, filters, ContextTypes,
)
import storage
import price_fetcher

logger = logging.getLogger(__name__)

(
    CHOOSE_ASSET,
    CHOOSE_DIRECTION,
    ENTER_PRICE,
    ENTER_NOTE,
    REMOVE_ID,
) = range(5)

ASSETS = ["BTC", "ETH", "SOL", "TOTAL3", "USDT.D"]


# ================= MAIN MENU =================

def _menu_kb(user_id: str) -> InlineKeyboardMarkup:
    enabled = storage.is_enabled(user_id)
    toggle = "🔴 Bot বন্ধ করো" if enabled else "🟢 Bot চালু করো"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Alert যোগ করো", callback_data="menu_add")],
        [InlineKeyboardButton("🗑 Alert মুছে ফেলো", callback_data="menu_remove")],
        [InlineKeyboardButton("📋 সব Alert দেখো", callback_data="menu_view")],
        [InlineKeyboardButton("💰 Live Prices", callback_data="menu_prices")],
        [InlineKeyboardButton(toggle, callback_data="menu_toggle")],
    ])


def _status(user_id: str) -> str:
    return "✅ চালু" if storage.is_enabled(user_id) else "⛔ বন্ধ"


# ================= START =================

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name or "Trader"
    count = len(storage.get_alerts(uid))

    text = (
        f"👋 স্বাগতম, *{name}*!\n\n"
        f"🤖 *Aler Bot*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔔 Bot Status: {_status(uid)}\n"
        f"📌 Active Alerts: *{count}টি*\n\n"
        f"নিচের বাটন ব্যবহার করো:"
    )

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_menu_kb(uid))


# ================= BACK MENU =================

async def _back_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(update.effective_user.id)
    alerts = storage.get_alerts(uid)

    text = (
        f"🤖 *Main Menu*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔔 Status: {_status(uid)}\n"
        f"📌 Active Alerts: *{len(alerts)}টি*\n"
    )

    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=_menu_kb(uid))


# ================= TOGGLE (ON/OFF + CLEAN DELETE) =================

async def toggle_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(update.effective_user.id)

    cur = storage.is_enabled(uid)
    storage.set_enabled(uid, not cur)

    # 🔥 IF TURNING OFF → DELETE ALL BOT MESSAGES
    if cur:  # currently ON → turning OFF
        for msg_id in storage.get_message_ids(uid):
            try:
                await ctx.bot.delete_message(chat_id=int(uid), message_id=msg_id)
            except:
                pass

        storage.clear_message_ids(uid)

    label = "🟢 Bot চালু হয়েছে!" if not cur else "🔴 Bot বন্ধ + সব Alert পরিষ্কার!"

    await q.answer(label, show_alert=True)
    await _back_menu(update, ctx)


# ================= VIEW ALERTS =================

async def view_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = str(update.effective_user.id)
    alerts = storage.get_alerts(uid)

    if not alerts:
        text = "📭 কোনো Alert নেই"
    else:
        text = "📋 আপনার Alerts:\n\n"
        for a in alerts:
            unit = "$"
            arrow = "🔺" if a["direction"] == "above" else "🔻"
            text += f"{arrow} #{a['id']} {a['asset']} → {a['price']}\n"

    await q.edit_message_text(text, reply_markup=_menu_kb(uid))


# ================= LIVE PRICES =================

async def show_prices(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    text = "💰 Live Prices\n━━━━━━━━━━\n"
    for a in ASSETS:
        p = price_fetcher.get_price(a)
        text += f"{a}: {p}\n"

    kb = [
        [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]
    ]

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))


# ================= REGISTER =================

def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))

    app.add_handler(CallbackQueryHandler(_back_menu, pattern="^back_menu$"))
    app.add_handler(CallbackQueryHandler(view_alerts, pattern="^menu_view$"))
    app.add_handler(CallbackQueryHandler(toggle_bot, pattern="^menu_toggle$"))
    app.add_handler(CallbackQueryHandler(show_prices, pattern="^menu_prices$"))