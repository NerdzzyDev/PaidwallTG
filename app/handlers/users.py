import logging
from datetime import datetime, timedelta

from aiogram import Bot, F, Router, types
from aiogram.filters import IS_MEMBER, IS_NOT_MEMBER, ChatMemberUpdatedFilter
from aiogram.types import ContentType, InlineKeyboardButton, InlineKeyboardMarkup

from app.database.models import add_user, get_user
from config.config import config

router = Router()
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [Users] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)


def get_payment_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="💸 Оплатить доступ (500₽)", url=config.payment_link)]]
    )


async def get_channel_invite_link(bot: Bot, user_id: int):
    logger.info("Generating invite link for user_id=%s", user_id)
    try:
        invite_link = await bot.create_chat_invite_link(
            chat_id=config.channel_id,
            member_limit=1,
            expire_date=int((datetime.utcnow() + timedelta(hours=24)).timestamp()),
        )
        logger.info("Invite link generated for user_id=%s: %s", user_id, invite_link.invite_link)
        return invite_link.invite_link
    except Exception as e:
        logger.error("Failed to generate invite link for user_id=%s: %s", user_id, str(e))
        raise


@router.message(F.command == "start")
async def start_command(message: types.Message):
    user = message.from_user
    logger.info("Processing /start for user_id=%s, username=%s", user.id, user.username)
    try:
        await add_user(message.bot.pool, user.id, user.first_name, user.last_name, None, user.username)
        logger.info("add_user called for user_id=%s", user.id)
        user_data = await get_user(message.bot.pool, user.id)
        if user_data:
            logger.info(
                "User retrieved after add: user_id=%s, is_subscribed=%s, expires_at=%s",
                user.id,
                user_data["is_subscribed"],
                user_data["subscription_expires_at"],
            )
        else:
            logger.error("User not found after add_user: user_id=%s", user.id)
        if user_data and user_data["is_subscribed"] and user_data["subscription_expires_at"] > datetime.utcnow():
            logger.info("User %s has active subscription until %s", user.id, user_data["subscription_expires_at"])
            invite_link = await get_channel_invite_link(message.bot, user.id)
            await message.answer(
                f"🎉 Добро пожаловать обратно, {user.first_name}! 💪\n"
                f"Ваша подписка на эксклюзивный контент Antow New Life активна до {user_data['subscription_expires_at'].strftime('%d.%m.%Y')}.\n"
                f"Присоединяйтесь к нашему премиум-каналу с тренировками, планами питания здоровым образом жизни: {invite_link}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[[InlineKeyboardButton(text="🏋️‍♂️ Перейти в канал", url=invite_link)]]
                ),
            )
        else:
            logger.info("User %s has no active subscription", user.id)
            await message.answer(
                f"🎉 Добро пожаловать в Antow New Life, {user.first_name}! 💪\n"
                f"Хотите получить доступ к эксклюзивным материалам от Антона Гусева? 🔥\n"
                f"Оплатите подписку по реквизитам ниже и отправьте скриншот оплаты в этот чат. 🚀\n\n"
                f"*Платёжные реквизиты:*\n"
                f"👤 ИП Гусев Антон Дмитриевич\n"
                f"📑 ИНН: 781699370996\n"
                f"📄 ОГРН: 322784700110622\n"
                f"🏦 Расчётный счёт: 40802810800003189325\n"
                f"🔍 БИК: 044525974\n"
                f"🏛 Банк: АО «Тинькофф Банк»\n"
                f"💼 ОКВЭД: 93.19\n"
                f"📜 [Договор публичной оферты](https://drive.google.com/file/d/1nEPW_2XbjW-Z9GJzuV88aZmd0aLCcD5h/view?usp=sharing)\n"
                f"💳 *Назначение платежа:* Услуги (консультации) тренера по бодибилдингу\n\n"
                f"👉 Оплатите 500₽ по кнопке ниже и отправьте скриншот в чат!",
                reply_markup=get_payment_keyboard(),
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error("Error in start_command for user_id=%s: %s", user.id, str(e))
        await message.answer("😔 Ой, что-то пошло не так! Пожалуйста, попробуйте снова или свяжитесь с поддержкой.")
        raise


@router.message(F.content_type.in_([ContentType.TEXT, ContentType.PHOTO]))
async def handle_message(message: types.Message):
    logger.info("Handling message from user_id=%s, content_type=%s", message.from_user.id, message.content_type)
    user = await get_user(message.bot.pool, message.from_user.id)
    if user:
        logger.info(
            "User found: user_id=%s, is_subscribed=%s, expires_at=%s",
            message.from_user.id,
            user["is_subscribed"],
            user["subscription_expires_at"],
        )
    else:
        logger.warning("User not found: user_id=%s, attempting to add", message.from_user.id)
        try:
            await add_user(
                message.bot.pool,
                message.from_user.id,
                message.from_user.first_name,
                message.from_user.last_name,
                None,
                message.from_user.username,
            )
            user = await get_user(message.bot.pool, message.from_user.id)
            if user:
                logger.info("User added and retrieved: user_id=%s", message.from_user.id)
            else:
                logger.error("Failed to add user: user_id=%s", message.from_user.id)
                await message.answer(
                    "😔 Ой, что-то пошло не так при регистрации! Пожалуйста, попробуйте команду /start снова."
                )
                return
        except Exception as e:
            logger.error("Error adding user %s: %s", message.from_user.id, str(e))
            await message.answer("😔 Произошла ошибка. Пожалуйста, попробуйте снова или свяжитесь с поддержкой.")
            return
    if user["is_subscribed"] and user["subscription_expires_at"] > datetime.utcnow():
        logger.info("User %s has active subscription until %s", message.from_user.id, user["subscription_expires_at"])
        invite_link = await get_channel_invite_link(message.bot, message.from_user.id)
        await message.answer(
            f"💪 Отлично, {message.from_user.first_name}! Ваша подписка активна до {user['subscription_expires_at'].strftime('%d.%m.%Y')}.\n"
            f"Погрузитесь в мир фитнеса, питания и мотивации в нашем премиум-канале Antow New Life! 🚀\n"
            f"Перейдите по ссылке: {invite_link}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏋️‍♂️ Перейти в канал", url=invite_link)]]
            ),
        )
        return
    if message.content_type == ContentType.PHOTO:
        user_info = f"Пользователь: {message.from_user.full_name} (@{message.from_user.username or 'нет'}, ID: {message.from_user.id})"
        admin_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✅ Подтвердить оплату", callback_data=f"approve_{message.from_user.id}"),
                    InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{message.from_user.id}"),
                ]
            ]
        )
        logger.info("Sending screenshot notification to admin for user_id=%s", message.from_user.id)
        await message.bot.send_photo(
            config.admin_id,
            photo=message.photo[-1].file_id,
            caption=f"{user_info}\nОтправил скриншот оплаты для доступа к Antow New Life.\nОтветьте на это сообщение, чтобы связаться с пользователем.",
            reply_markup=admin_keyboard,
        )
        await message.answer(
            "✅ Ваш скриншот оплаты отправлен на проверку! 🙌\n"
            "Скоро мы подтвердим ваш доступ к эксклюзивному контенту Antow New Life. Оставайтесь на связи! 😊"
        )
    else:
        logger.info("User %s sent text, prompting payment", message.from_user.id)
        await message.answer(
            "🔥 Хотите получить доступ к эксклюзивным материалам от Antow New Life? 💪\n"
            "Оплатите подписку по реквизитам ниже и отправьте скриншот оплаты в этот чат. 🚀\n\n"
            "*Платёжные реквизиты:*\n"
            "👤 ИП Гусев Антон Дмитриевич\n"
            "📑 ИНН: 781699370996\n"
            "📄 ОГРН: 322784700110622\n"
            "🏦 Расчётный счёт: 40802810800003189325\n"
            "🔍 БИК: 044525974\n"
            "🏛 Банк: АО «Тинькофф Банк»\n"
            "💼 ОКВЭД: 93.19\n"
            "📜 [Договор публичной оферты](https://drive.google.com/file/d/1nEPW_2XbjW-Z9GJzuV88aZmd0aLCcD5h/view?usp=sharing)\n"
            "💳 *Назначение платежа:* Услуги (консультации) тренера по бодибилдингу\n\n"
            "👉 Оплатите 500₽ по кнопке ниже и отправьте скриншот в чат!",
            reply_markup=get_payment_keyboard(),
            parse_mode="Markdown",
        )


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed=(IS_NOT_MEMBER >> IS_MEMBER)))
async def user_joined_channel(event: types.ChatMemberUpdated):
    logger.info("User %s joined channel", event.from_user.id)
    user = await get_user(event.bot.pool, event.from_user.id)
    if user and user["is_subscribed"]:
        logger.info("User %s has active subscription until %s", event.from_user.id, user["subscription_expires_at"])
        invite_link = await get_channel_invite_link(event.bot, event.from_user.id)
        await event.bot.send_message(
            event.from_user.id,
            f"🎉 Поздравляем, {event.from_user.first_name}! Вы в команде Antow New Life! 💪\n"
            f"Ваша подписка активна до {user['subscription_expires_at'].strftime('%d.%m.%Y')}.\n"
            f"Наслаждайтесь эксклюзивными материалом! 🚀\n"
            f"Ссылка на канал: {invite_link}",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="🏋️‍♂️ Перейти в канал", url=invite_link)]]
            ),
        )
    else:
        logger.info("User %s joined channel but has no active subscription", event.from_user.id)
        try:
            await event.bot.ban_chat_member(chat_id=config.channel_id, user_id=event.from_user.id)
            logger.info("User %s removed from channel due to no active subscription", event.from_user.id)
            await event.bot.send_message(
                event.from_user.id,
                "😔 Ваша подписка не активна. Чтобы получить доступ к эксклюзивному контенту Antow New Life, оплатите подписку по реквизитам ниже и отправьте скриншот оплаты. 💸\n\n"
                "*Платёжные реквизиты:*\n"
                "👤 ИП Гусев Антон Дмитриевич\n"
                "📑 ИНН: 781699370996\n"
                "📄 ОГРН: 322784700110622\n"
                "🏦 Расчётный счёт: 40802810800003189325\n"
                "🔍 БИК: 044525974\n"
                "🏛 Банк: АО «Тинькофф Банк»\n"
                "💼 ОКВЭД: 93.19\n"
                "📜 [Договор публичной оферты](https://drive.google.com/file/d/1nEPW_2XbjW-Z9GJzuV88aZmd0aLCcD5h/view?usp=sharing)\n"
                "💳 *Назначение платежа:* Услуги (консультации) тренера по бодибилдингу\n\n"
                "👉 Оплатите 500₽ по кнопке ниже и отправьте скриншот в чат!",
                reply_markup=get_payment_keyboard(),
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error("Failed to remove user %s from channel: %s", event.from_user.id, str(e))
            await event.bot.send_message(
                config.admin_id, f"⚠️ Ошибка при удалении пользователя {event.from_user.id} из канала: {e!s}"
            )
