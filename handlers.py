"""
Handlers — সব বাটন, কথোপকথন, কমান্ড
Note feature সহ।
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

# Conversation states
(
    CHOOSE_ASSET,
    CHOOSE_DIRECTION,
    ENTER_PRICE,
    ENTER_NOTE,
    REMOVE_ID,
) = range(5)

ASSETS = ["BTC", "ETH", "SOL", "TOTAL3", "USDT.D"]


# ══════════════════════════════════════════════
# MAIN MENU
# ══════════════════════════════════════════════

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


async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    name = update.effective_user.first_name or "Trader"
    alerts = storage.get_alerts(uid)
    count = len(alerts)

    text = (
        f"👋 স্বাগতম, *{name}*!\n\n"
        f"🤖 *Aler Bot (Adib)*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📡 Monitoring: BTC · ETH · SOL · TOTAL3 · USDT.D\n"
        f"🔔 Bot Status: {_status(uid)}\n"
        f"📌 Active Alerts: *{count}টি*\n\n"
        f"নিচের বাটন থেকে কাজ করো:"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=_menu_kb(uid))


async def _back_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(update.effective_user.id)
    alerts = storage.get_alerts(uid)
    text = (
        f"🤖 *Aler Bot — Main Menu*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔔 Status: {_status(uid)}\n"
        f"📌 Active Alerts: *{len(alerts)}টি*\n\n"
        f"নিচের বাটন থেকে কাজ করো:"
    )
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=_menu_kb(uid))


# ══════════════════════════════════════════════
# VIEW ALERTS
# ══════════════════════════════════════════════

async def view_alerts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(update.effective_user.id)
    alerts = storage.get_alerts(uid)

    if not alerts:
        text = "📭 *কোনো Alert নেই।*\n\n➕ Add Alert দিয়ে নতুন Alert তৈরি করো।"
    else:
        lines = [f"📋 *তোমার Active Alerts ({len(alerts)}টি):*\n"]
        for a in alerts:
            unit = "B$" if a["asset"] == "TOTAL3" else ("%" if a["asset"] == "USDT.D" else "$")
            arrow = "🔺" if a["direction"] == "above" else "🔻"
            note_text = f"\n    📝 _{a['note']}_" if a.get("note", "").strip() else ""
            lines.append(
                f"{arrow} *#{a['id']}* | `{a['asset']}` → `{a['price']:,.4f}` {unit} ({a['direction'].upper()})"
                f"{note_text}"
            )
        text = "\n".join(lines)

    kb = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
    await q.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════
# TOGGLE ON/OFF
# ══════════════════════════════════════════════

async def toggle_bot(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    uid = str(update.effective_user.id)
    cur = storage.is_enabled(uid)
    storage.set_enabled(uid, not cur)
    label = "✅ Bot চালু হয়েছে!" if not cur else "⛔ Bot বন্ধ করা হয়েছে।"
    await q.answer(label, show_alert=True)
    await _back_menu(update, ctx)


# ══════════════════════════════════════════════
# LIVE PRICES
# ══════════════════════════════════════════════

async def show_prices(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("প্রাইস লোড হচ্ছে...")

    lines = ["💰 *Live Prices*\n━━━━━━━━━━━━━━"]
    for asset in ASSETS:
        p = price_fetcher.get_price(asset)
        unit = "B$" if asset == "TOTAL3" else ("%" if asset == "USDT.D" else "$")
        val = f"`{p:,.4f}` {unit}" if p is not None else "⚠️ পাওয়া যাচ্ছে না"
        lines.append(f"• *{asset}*: {val}")

    lines.append("\n_প্রতি ৫ সেকেন্ডে auto-check চলছে_")
    kb = [
        [InlineKeyboardButton("🔄 Refresh", callback_data="menu_prices")],
        [InlineKeyboardButton("⬅️ Back", callback_data="back_menu")],
    ]
    await q.edit_message_text("\n".join(lines), parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(kb))


# ══════════════════════════════════════════════
# ADD ALERT — ConversationHandler (4 ধাপ)
# ══════════════════════════════════════════════

async def add_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    kb = [
        [InlineKeyboardButton(a, callback_data=f"asset_{a}") for a in ASSETS[:3]],
        [InlineKeyboardButton(a, callback_data=f"asset_{a}") for a in ASSETS[3:]],
        [InlineKeyboardButton("❌ বাতিল", callback_data="cancel_conv")],
    ]
    await q.edit_message_text(
        "📌 *ধাপ ১/৪ — Asset বেছে নাও:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSE_ASSET


async def choose_asset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    asset = q.data.replace("asset_", "")
    ctx.user_data["asset"] = asset
    kb = [
        [
            InlineKeyboardButton("🔺 এর উপরে গেলে", callback_data="dir_above"),
            InlineKeyboardButton("🔻 এর নিচে গেলে", callback_data="dir_below"),
        ],
        [InlineKeyboardButton("❌ বাতিল", callback_data="cancel_conv")],
    ]
    await q.edit_message_text(
        f"📌 *ধাপ ২/৪ — Alert কখন আসবে?*\n\nAsset: *{asset}*\n\nকোন direction এ alert দেব?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return CHOOSE_DIRECTION


async def choose_direction(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    direction = q.data.replace("dir_", "")
    ctx.user_data["direction"] = direction
    asset = ctx.user_data["asset"]
    unit = "Billion Dollar (B$)" if asset == "TOTAL3" else ("Percent (%)" if asset == "USDT.D" else "USDT ($)")
    arrow = "🔺 উপরে" if direction == "above" else "🔻 নিচে"
    await q.edit_message_text(
        f"📌 *ধাপ ৩/৪ — Target Price লেখো:*\n\n"
        f"Asset: *{asset}*\nDirection: *{arrow}*\nUnit: `{unit}`\n\n"
        f"✏️ *নিচে price টাইপ করে পাঠাও:*\n"
        f"_(উদাহরণ: 3500 অথবা 3500.50)_",
        parse_mode="Markdown"
    )
    return ENTER_PRICE


async def enter_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", "")
    try:
        price = float(text)
    except ValueError:
        await update.message.reply_text(
            "❌ ভুল! শুধু সংখ্যা লেখো। যেমন: `3500` বা `3500.50`",
            parse_mode="Markdown"
        )
        return ENTER_PRICE

    ctx.user_data["price"] = price
    asset = ctx.user_data["asset"]

    kb = [[
        InlineKeyboardButton("⏭ Note ছাড়াই Save", callback_data="note_skip"),
    ]]
    await update.message.reply_text(
        f"📌 *ধাপ ৪/৪ — Note যোগ করো (ঐচ্ছিক):*\n\n"
        f"Asset: *{asset}* → `{price:,.4f}`\n\n"
        f"📝 Alert আসলে কোনো বার্তা দেখাতে চাও?\n"
        f"_(যেমন: \"BTC সেল জোন\", \"ETH Buy করো\", \"SOL রেসিস্ট্যান্স\")_\n\n"
        f"✏️ *Note টাইপ করে পাঠাও অথবা নিচের বাটনে ক্লিক করো:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )
    return ENTER_NOTE


async def enter_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    await _save_alert(update, ctx, note)
    return ConversationHandler.END


async def skip_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # Fake an update with empty note
    uid = str(update.effective_user.id)
    asset = ctx.user_data["asset"]
    price = ctx.user_data["price"]
    direction = ctx.user_data["direction"]

    alert_id = storage.add_alert(uid, asset, price, direction, note="")
    unit = "B$" if asset == "TOTAL3" else ("%" if asset == "USDT.D" else "$")
    arrow = "🔺" if direction == "above" else "🔻"

    await q.edit_message_text(
        f"✅ *Alert তৈরি হয়েছে!*\n\n"
        f"🆔 Alert ID: *#{alert_id}*\n"
        f"{arrow} *{asset}* → `{price:,.4f}` {unit} ({direction.upper()})\n\n"
        f"প্রাইস এই লেভেলে পৌঁছালে তোমাকে জানাব!",
        parse_mode="Markdown",
        reply_markup=_menu_kb(uid)
    )
    ctx.user_data.clear()
    return ConversationHandler.END


async def _save_alert(update: Update, ctx: ContextTypes.DEFAULT_TYPE, note: str):
    uid = str(update.effective_user.id)
    asset = ctx.user_data["asset"]
    price = ctx.user_data["price"]
    direction = ctx.user_data["direction"]

    alert_id = storage.add_alert(uid, asset, price, direction, note=note)
    unit = "B$" if asset == "TOTAL3" else ("%" if asset == "USDT.D" else "$")
    arrow = "🔺" if direction == "above" else "🔻"
    note_line = f"\n📝 Note: _{note}_" if note else ""

    await update.message.reply_text(
        f"✅ *Alert তৈরি হয়েছে!*\n\n"
        f"🆔 Alert ID: *#{alert_id}*\n"
        f"{arrow} *{asset}* → `{price:,.4f}` {unit} ({direction.upper()})"
        f"{note_line}\n\n"
        f"প্রাইস এই লেভেলে পৌঁছালে তোমাকে জানাব!",
        parse_mode="Markdown",
        reply_markup=_menu_kb(uid)
    )
    ctx.user_data.clear()


# ══════════════════════════════════════════════
# REMOVE ALERT
# ══════════════════════════════════════════════

async def remove_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(update.effective_user.id)
    alerts = storage.get_alerts(uid)

    if not alerts:
        kb = [[InlineKeyboardButton("⬅️ Back", callback_data="back_menu")]]
        await q.edit_message_text(
            "📭 *কোনো Alert নেই মুছার জন্য।*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return ConversationHandler.END

    buttons = []
    for a in alerts:
        unit = "B$" if a["asset"] == "TOTAL3" else ("%" if a["asset"] == "USDT.D" else "$")
        arrow = "🔺" if a["direction"] == "above" else "🔻"
        note_preview = f" | {a['note'][:15]}..." if a.get("note", "").strip() else ""
        label = f"#{a['id']} {arrow} {a['asset']} {a['price']:,.2f}{unit}{note_preview}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"rm_{a['id']}")])

    buttons.append([InlineKeyboardButton("❌ বাতিল", callback_data="cancel_conv")])
    await q.edit_message_text(
        "🗑 *কোন Alert মুছবে? বেছে নাও:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return REMOVE_ID


async def do_remove(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    uid = str(update.effective_user.id)
    alert_id = int(q.data.replace("rm_", ""))
    removed = storage.remove_alert(uid, alert_id)
    msg = f"✅ Alert *#{alert_id}* মুছে ফেলা হয়েছে।" if removed else f"⚠️ Alert *#{alert_id}* পাওয়া যায়নি।"
    await q.edit_message_text(msg, parse_mode="Markdown", reply_markup=_menu_kb(uid))
    return ConversationHandler.END


# ══════════════════════════════════════════════
# CANCEL
# ══════════════════════════════════════════════

async def cancel_conv(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("বাতিল করা হয়েছে।")
    ctx.user_data.clear()
    await _back_menu(update, ctx)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# REGISTER
# ══════════════════════════════════════════════

def register_handlers(app: Application):
    app.add_handler(CommandHandler("start", cmd_start))

    add_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(add_start, pattern="^menu_add$")],
        states={
            CHOOSE_ASSET:    [CallbackQueryHandler(choose_asset, pattern="^asset_"),
                              CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$")],
            CHOOSE_DIRECTION:[CallbackQueryHandler(choose_direction, pattern="^dir_"),
                              CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$")],
            ENTER_PRICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_price)],
            ENTER_NOTE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_note),
                              CallbackQueryHandler(skip_note, pattern="^note_skip$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$")],
        per_message=False,
    )

    remove_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(remove_start, pattern="^menu_remove$")],
        states={
            REMOVE_ID: [CallbackQueryHandler(do_remove, pattern="^rm_"),
                        CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$")],
        },
        fallbacks=[CallbackQueryHandler(cancel_conv, pattern="^cancel_conv$")],
        per_message=False,
    )

    app.add_handler(add_conv)
    app.add_handler(remove_conv)
    app.add_handler(CallbackQueryHandler(_back_menu,    pattern="^back_menu$"))
    app.add_handler(CallbackQueryHandler(view_alerts,  pattern="^menu_view$"))
    app.add_handler(CallbackQueryHandler(toggle_bot,   pattern="^menu_toggle$"))
    app.add_handler(CallbackQueryHandler(show_prices,  pattern="^menu_prices$"))