import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.database.models import init_db_pool
from app.handlers import admin, users
from app.utils.scheduler import setup_scheduler
from config.config import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [Bot] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("Starting bot")
    bot = Bot(token=config.bot_token)
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(users.router)

    logger.info("Initializing database pool")
    bot.pool = await init_db_pool(config)

    logger.info("Setting up scheduler")
    setup_scheduler(bot)

    logger.info("Starting polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
