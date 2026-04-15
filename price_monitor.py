import asyncio
import time
import logging
from telegram import Bot

import storage
import price_fetcher
from config import CHECK_INTERVAL

logger = logging.getLogger(__name__)


class PriceMonitor:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def run(self):
        logger.info("Monitor started")
        while True:
            try:
                await self.check()
            except Exception as e:
                logger.error(e)

            await asyncio.sleep(CHECK_INTERVAL)

    async def check(self):
        users = storage.get_all_users()
        if not users:
            return

        needed = set()

        for u in users:
            if storage.is_enabled(u):
                for a in storage.get_alerts(u):
                    needed.add(a["asset"])

        if not needed:
            return

        prices = {a: price_fetcher.get_price(a) for a in needed}
        now = time.time()

        for u in users:
            if not storage.is_enabled(u):
                continue

            for a in storage.get_alerts(u):
                price = prices.get(a["asset"])
                if price is None:
                    continue

                hit = (
                    (a["direction"] == "above" and price >= a["price"]) or
                    (a["direction"] == "below" and price <= a["price"])
                )

                if hit:
                    # 🔥 repeat alert system (every 10 sec)
                    if now - a.get("last_alerted", 0) < 10:
                        continue

                    await self.send(u, a, price)
                    storage.update_last_alerted(u, a["id"], now)

    async def send(self, uid, alert, price):
        arrow = "🔺" if alert["direction"] == "above" else "🔻"

        msg = (
            f"{arrow} ALERT\n"
            f"{alert['asset']}\n"
            f"Target: {alert['price']}\n"
            f"Current: {price}\n"
            f"Note: {alert.get('note','')}"
        )

        await self.bot.send_message(chat_id=int(uid), text=msg)