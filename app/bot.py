import asyncio
import logging

from aiogram import Bot, Dispatcher
from database.models import init_db  # теперь это SQLite

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

    logger.info("Initializing SQLite database")
    await init_db(config)  # создает таблицы, если нужно

    logger.info("Setting up scheduler")
    setup_scheduler(config.db["path"])  # передаём путь к SQLite

    logger.info("Starting polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
