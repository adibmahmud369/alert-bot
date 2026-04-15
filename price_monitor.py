"""
Price Monitor — ব্যাকগ্রাউন্ডে চলে, প্রতি CHECK_INTERVAL সেকেন্ডে সব অ্যালার্ট চেক করে
"""

import asyncio
import logging
import time

from telegram import Bot
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

        # কোন কোন অ্যাসেটের প্রাইস লাগবে বের করো
        needed = set()
        for uid in users:
            if storage.is_enabled(uid):
                for a in storage.get_alerts(uid):
                    needed.add(a["asset"])

        if not needed:
            return

        # একবারে সব প্রাইস ফেচ করো
        prices = {asset: price_fetcher.get_price(asset) for asset in needed}
        now = time.time()

        for uid in users:
            if not storage.is_enabled(uid):
                continue
            for alert in storage.get_alerts(uid):
                current = prices.get(alert["asset"])
                if current is None:
                    continue

                hit = (
                    (alert["direction"] == "above" and current >= alert["price"]) or
                    (alert["direction"] == "below" and current <= alert["price"])
                )
                if not hit:
                    continue

                if now - alert.get("last_alerted", 0) < ALERT_REPEAT_INTERVAL:
                    continue

                await self._fire(uid, alert, current)
                storage.update_last_alerted(uid, alert["id"], now)

    async def _fire(self, user_id: str, alert: dict, current: float):
        asset = alert["asset"]
        direction = alert["direction"]
        target = alert["price"]
        note = alert.get("note", "").strip()

        unit = "B$" if asset == "TOTAL3" else ("%" if asset == "USDT.D" else "$")
        arrow = "🔺" if direction == "above" else "🔻"

        note_line = f"\n📝 *Note:* {note}" if note else ""

        msg = (
            f"{arrow} *ALERT TRIGGERED* {arrow}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 Asset:   *{asset}*\n"
            f"🎯 Target:  `{target:,.4f}` {unit}\n"
            f"💰 Current: `{current:,.4f}` {unit}\n"
            f"📊 Type:    *{direction.upper()}*"
            f"{note_line}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Alert ID #{alert['id']}\n"
            f"_Remove alert to stop repeating._"
        )

        try:
            await self.bot.send_message(
                chat_id=int(user_id),
                text=msg,
                parse_mode="Markdown"
            )
            logger.info(f"✅ Alert fired → user:{user_id} asset:{asset} price:{current}")
        except Exception as e:
            logger.error(f"Send failed → {user_id}: {e}")