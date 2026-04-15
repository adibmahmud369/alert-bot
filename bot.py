"""
Aler Bot (Adib) — Main Entry Point
এই ফাইলটি রান করলেই বট চালু হবে।
"""

import asyncio
import logging
from telegram.ext import Application
from config import BOT_TOKEN
from handlers import register_handlers
from price_monitor import PriceMonitor

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("🚀 Aler Bot চালু হচ্ছে...")
    app = Application.builder().token(BOT_TOKEN).build()
    register_handlers(app)

    monitor = PriceMonitor(app.bot)
    app.bot_data["monitor"] = monitor

    async with app:
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        logger.info("✅ Bot চালু! Telegram এ /start পাঠাও।")
        asyncio.create_task(monitor.run())
        await asyncio.Event().wait()  # চিরকাল চলতে থাকবে


if __name__ == "__main__":
    asyncio.run(main())