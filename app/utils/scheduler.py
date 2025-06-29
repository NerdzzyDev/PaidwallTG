import logging

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.database.models import get_expired_subscriptions, get_expiring_subscriptions, get_stats, update_subscription
from config.config import config

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [Scheduler] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def setup_scheduler(bot: Bot):
    logger.info("Setting up scheduler")
    scheduler = AsyncIOScheduler()

    async def check_subscriptions():
        logger.info("Checking subscriptions")
        # Check for subscriptions expiring in 3 days
        expiring = await get_expiring_subscriptions(bot.pool, days_left=3)
        for user in expiring:
            logger.info("Sending expiration reminder to user_id=%s", user["user_id"])
            await bot.send_message(
                user["user_id"],
                f"Ваша подписка истекает {user['subscription_expires_at'].strftime('%d.%m.%Y')}. "
                "Пожалуйста, продлите подписку, чтобы сохранить доступ.",
            )

        # Check for expired subscriptions
        expired = await get_expired_subscriptions(bot.pool)
        for user in expired:
            logger.info("Processing expired subscription for user_id=%s", user["user_id"])
            await update_subscription(bot.pool, user["user_id"], False, None)
            try:
                await bot.ban_chat_member(chat_id=config.channel_id, user_id=user["user_id"])
                await bot.send_message(
                    user["user_id"], "Ваша подписка истекла. Пожалуйста, оплатите подписку снова для доступа к каналу."
                )
                logger.info("User %s removed from channel", user["user_id"])
            except Exception as e:
                logger.error("Failed to remove user %s from channel: %s", user["user_id"], str(e))
                await bot.send_message(
                    config.admin_id, f"Ошибка при удалении пользователя {user['user_id']} из канала: {e!s}"
                )

    async def send_weekly_stats():
        logger.info("Sending weekly stats to admin")
        try:
            stats = await get_stats(bot.pool)
            response = (
                f"📊 Еженедельная статистика:\n"
                f"Всего пользователей: {stats['total_users']}\n"
                f"Активные подписчики: {stats['active_subscribers']}\n"
                f"Без подписки: {stats['non_subscribers']}\n"
                f"Оценочный месячный доход: {stats['estimated_income']}₽"
            )
            logger.info("Sending weekly stats to admin: %s", response)
            await bot.send_message(config.admin_id, response)
        except Exception as e:
            logger.error("Failed to send weekly stats to admin: %s", str(e))
            await bot.send_message(config.admin_id, f"Ошибка при отправке статистики: {e!s}")

    scheduler.add_job(check_subscriptions, "interval", days=1)
    scheduler.add_job(send_weekly_stats, "cron", day_of_week="sun", hour=10, minute=0)
    logger.info("Scheduler jobs added: check_subscriptions, send_weekly_stats")
    scheduler.start()
    logger.info("Scheduler started")
