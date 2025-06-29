import logging
import re
from datetime import datetime, timedelta

from aiogram import F, Router, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import get_stats, update_subscription
from config.config import config

router = Router()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [Admin] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


@router.message(Command("a"))
async def admin_stats(message: types.Message):
    logger.info("Received /a command from user_id=%s", message.from_user.id)
    if message.from_user.id != config.admin_id:
        logger.warning("Unauthorized access to /a by user_id=%s", message.from_user.id)
        await message.answer("У вас нет прав для этого действия.")
        return
    logger.info("Admin %s requesting statistics", message.from_user.id)
    try:
        stats = await get_stats(message.bot.pool)
        response = (
            f"📊 Статистика:\n"
            f"Всего пользователей: {stats['total_users']}\n"
            f"Активные подписчики: {stats['active_subscribers']}\n"
            f"Без подписки: {stats['non_subscribers']}\n"
            f"Оценочный месячный доход: {stats['estimated_income']}₽"
        )
        logger.info("Sending stats to admin: %s", response)
        await message.answer(response)
    except Exception as e:
        logger.error("Failed to fetch stats for admin %s: %s", message.from_user.id, str(e))
        await message.answer("Произошла ошибка при получении статистики.")


@router.callback_query(lambda c: c.data.startswith("approve_"))
async def approve_subscription(callback: types.CallbackQuery):
    if callback.from_user.id != config.admin_id:
        logger.warning("Unauthorized callback approve by user_id=%s", callback.from_user.id)
        await callback.answer("У вас нет прав для этого действия.", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    expires_at = datetime.utcnow() + timedelta(days=30)
    try:
        await update_subscription(callback.bot.pool, user_id, True, expires_at)
        logger.info("Approved subscription for user_id=%s until %s", user_id, expires_at)
        await callback.message.edit_reply_markup(reply_markup=None)  # Remove buttons
        await callback.message.answer(
            f"Подписка для пользователя {user_id} подтверждена до {expires_at.strftime('%d.%m.%Y')}."
        )
        await callback.bot.send_message(
            user_id,
            f"Ваша подписка подтверждена до {expires_at.strftime('%d.%m.%Y')}!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="Перейти в канал", url=f"https://t.me/{config.channel_id}")]
                ]
            ),
        )
        await callback.answer("Подписка подтверждена.")
    except Exception as e:
        logger.error("Failed to approve subscription for user_id=%s: %s", user_id, str(e))
        await callback.answer("Ошибка при подтверждении подписки.", show_alert=True)


@router.callback_query(lambda c: c.data.startswith("reject_"))
async def reject_subscription(callback: types.CallbackQuery):
    if callback.from_user.id != config.admin_id:
        logger.warning("Unauthorized callback reject by user_id=%s", callback.from_user.id)
        await callback.answer("У вас нет прав для этого действия.", show_alert=True)
        return
    user_id = int(callback.data.split("_")[1])
    try:
        logger.info("Rejected subscription for user_id=%s", user_id)
        await callback.message.edit_reply_markup(reply_markup=None)  # Remove buttons
        await callback.message.answer(f"Подписка для пользователя {user_id} отклонена.")
        await callback.bot.send_message(user_id, "Ваша оплата была отклонена. Пожалуйста, свяжитесь с поддержкой.")
        await callback.answer("Подписка отклонена.")
    except Exception as e:
        logger.error("Failed to reject subscription for user_id=%s: %s", user_id, str(e))
        await callback.answer("Ошибка при отклонении подписки.", show_alert=True)


@router.message(F.reply_to_message & F.from_user.id == config.admin_id)
async def handle_admin_reply(message: types.Message):
    logger.info("Received reply from admin_id=%s", message.from_user.id)
    if not message.reply_to_message or not message.reply_to_message.caption:
        logger.warning("Admin reply has no valid reply_to_message or caption")
        await message.answer("Пожалуйста, ответьте на сообщение с информацией о пользователе.")
        return
    caption = message.reply_to_message.caption
    user_id_match = re.search(r"ID: (\d+)", caption)
    if not user_id_match:
        logger.warning("Could not extract user ID from caption: %s", caption)
        await message.answer("Не удалось определить ID пользователя из сообщения.")
        return
    user_id = int(user_id_match.group(1))
    try:
        await message.bot.send_message(user_id, message.text)
        logger.info("Admin replied to user_id=%s with message: %s", user_id, message.text)
        await message.answer(f"Сообщение отправлено пользователю {user_id}.")
    except Exception as e:
        logger.error("Failed to send reply to user_id=%s: %s", user_id, str(e))
        await message.answer("Ошибка при отправке сообщения пользователю.")
