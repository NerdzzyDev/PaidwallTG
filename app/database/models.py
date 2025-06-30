import logging
from datetime import datetime, timedelta

import aiosqlite
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_id: int
    channel_id: str
    payment_link: str = "https://example.com/payment"
    db: dict = {"path": "./bot.db"}

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Settings()

# Configure logger for database operations
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [DB] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("db")


async def init_db(config):
    db_path = config.db["path"]
    logger.info("Initializing SQLite database at %s", db_path)
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    phone_number TEXT,
                    username TEXT,
                    is_subscribed BOOLEAN DEFAULT FALSE,
                    subscription_expires_at TIMESTAMP
                )
            """)
            await db.commit()
        logger.info("SQLite DB initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize SQLite DB: %s", str(e))
        raise


async def add_user(db_path, user_id, first_name, last_name, phone_number, username):
    logger.info("Adding user: user_id=%s, username=%s", user_id, username)
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                INSERT OR IGNORE INTO users (user_id, first_name, last_name, phone_number, username)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, first_name, last_name, phone_number, username),
            )
            await db.commit()
            logger.info("User added: user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to add user %s: %s", user_id, str(e))
        raise


async def get_user(db_path, user_id):
    logger.info("Fetching user: user_id=%s", user_id)
    try:
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    logger.info(
                        "User found: user_id=%s, is_subscribed=%s, expires_at=%s",
                        user_id,
                        row["is_subscribed"],
                        row["subscription_expires_at"],
                    )
                else:
                    logger.info("User not found: user_id=%s", user_id)
                return row
    except Exception as e:
        logger.error("Failed to fetch user %s: %s", user_id, str(e))
        raise


async def update_subscription(db_path, user_id, is_subscribed, expires_at):
    logger.info(
        "Updating subscription: user_id=%s, is_subscribed=%s, expires_at=%s", user_id, is_subscribed, expires_at
    )
    try:
        async with aiosqlite.connect(db_path) as db:
            await db.execute(
                """
                UPDATE users
                SET is_subscribed = ?, subscription_expires_at = ?
                WHERE user_id = ?
            """,
                (is_subscribed, expires_at, user_id),
            )
            await db.commit()
            logger.info("Subscription updated successfully: user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to update subscription for user %s: %s", user_id, str(e))
        raise


async def get_expiring_subscriptions(db_path, days_left):
    logger.info("Fetching subscriptions expiring in %s days", days_left)
    try:
        cutoff = datetime.utcnow() + timedelta(days=days_left)
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT user_id, subscription_expires_at
                FROM users
                WHERE is_subscribed = 1
                AND subscription_expires_at <= ?
            """,
                (cutoff,),
            ) as cursor:
                rows = await cursor.fetchall()
                logger.info("Found %s expiring subscriptions", len(rows))
                return rows
    except Exception as e:
        logger.error("Failed to fetch expiring subscriptions: %s", str(e))
        raise


async def get_expired_subscriptions(db_path):
    logger.info("Fetching expired subscriptions")
    try:
        now = datetime.utcnow()
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT user_id, subscription_expires_at
                FROM users
                WHERE is_subscribed = 1
                AND subscription_expires_at <= ?
            """,
                (now,),
            ) as cursor:
                rows = await cursor.fetchall()
                logger.info("Found %s expired subscriptions", len(rows))
                return rows
    except Exception as e:
        logger.error("Failed to fetch expired subscriptions: %s", str(e))
        raise


async def get_stats(db_path):
    logger.info("Fetching statistics")
    try:
        now = datetime.utcnow()
        async with aiosqlite.connect(db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT COUNT(*) AS count FROM users") as cur:
                total_users = (await cur.fetchone())["count"]

            async with db.execute(
                """
                SELECT COUNT(*) AS count
                FROM users
                WHERE is_subscribed = 1
                AND subscription_expires_at > ?
            """,
                (now,),
            ) as cur:
                active_subscribers = (await cur.fetchone())["count"]

            non_subscribers = total_users - active_subscribers
            estimated_income = active_subscribers * 500  # ₽

            stats = {
                "total_users": total_users,
                "active_subscribers": active_subscribers,
                "non_subscribers": non_subscribers,
                "estimated_income": estimated_income,
            }

            logger.info(
                "Stats: total=%s, active=%s, non_subs=%s, income=%s₽",
                total_users,
                active_subscribers,
                non_subscribers,
                estimated_income,
            )
            return stats
    except Exception as e:
        logger.error("Failed to fetch stats: %s", str(e))
        raise
