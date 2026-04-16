"""
Price Monitor — প্রতি CHECK_INTERVAL সেকেন্ডে সব অ্যালার্ট চেক করে।
Alert message এ সরাসরি "Stop" বাটন থাকবে।
Simple format: SOL = TP Hit
"""

import asyncio
import logging
import time

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from config import CHECK_INTERVAL, ALERT_REPEAT_INTERVAL
import storage
import price_fetcher

logger = logging.getLogger(__name__)


class PriceMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def run(self):
        logger.info("📡 Price monitor চালু হয়েছে।")
        while True:
            try:
                await self._check_all()
            except Exception as e:
                logger.error(f"Monitor error: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    async def _check_all(self):
        users = storage.get_all_users()
        if not users:
            return

        needed = set()
        for uid in users:
            if storage.is_enabled(uid):
                for a in storage.get_alerts(uid):
                    needed.add(a["asset"])

        if not needed:
            return

        prices = {asset: price_fetcher.get_price(asset) for asset in needed}
        now = time.time()

        for uid in users:
            if not storage.is_enabled(uid):
                continue

            for alert in storage.get_alerts(uid):
                current = prices.get(alert["asset"])
                if current is None:
                    continue

                triggered = alert.get("triggered", False)

                if not triggered:
                    hit = (
                        (alert["direction"] == "above" and current >= alert["price"]) or
                        (alert["direction"] == "below" and current <= alert["price"])
                    )
                    if not hit:
                        continue
                    storage.mark_triggered(uid, alert["id"])

                if now - alert.get("last_alerted", 0) < ALERT_REPEAT_INTERVAL:
                    continue

                await self._fire(uid, alert, current)
                storage.update_last_alerted(uid, alert["id"], now)

    async def _fire(self, user_id: str, alert: dict, current: float):
        asset = alert["asset"]
        note = alert.get("note", "").strip()
        alert_id = alert["id"]

        # ── Simple message format ──
        # note থাকলে → "SOL = TP Hit"
        # note না থাকলে → "SOL = Alert #1"
        label = note if note else f"Alert #{alert_id}"
        msg = f"🔔 *{asset} = {label}*"

        # প্রতিটা alert message এর মধ্যে Stop বাটন
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"🔕 Stop & Delete This Alert",
                callback_data=f"stop_alert_{alert_id}"
            )
        ]])

        try:
            await self.bot.send_message(
                chat_id=int(user_id),
                text=msg,
                parse_mode="Markdown",
                reply_markup=kb
            )
            logger.info(f"✅ Alert fired → user:{user_id} asset:{asset}")
        except Exception as e:
            logger.error(f"Send failed → {user_id}: {e}")