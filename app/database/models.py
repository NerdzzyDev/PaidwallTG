import logging
from datetime import datetime, timedelta

import asyncpg

# Configure logger for database operations
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] [DB] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("db")


async def init_db_pool(config):
    logger.info(
        "Initializing database pool with config: host=%s, port=%s, database=%s",
        config.db["host"],
        config.db["port"],
        config.db["database"],
    )
    try:
        pool = await asyncpg.create_pool(
            host=config.db["host"],
            port=config.db["port"],
            user=config.db["user"],
            password=config.db["password"],
            database=config.db["database"],
        )
        async with pool.acquire() as conn:
            logger.info("Creating users table if not exists")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    phone_number TEXT,
                    username TEXT,
                    is_subscribed BOOLEAN DEFAULT FALSE,
                    subscription_expires_at TIMESTAMP
                )
            """)
        logger.info("Database pool initialized successfully")
        return pool
    except Exception as e:
        logger.error("Failed to initialize database pool: %s", str(e))
        raise


async def add_user(pool, user_id, first_name, last_name, phone_number, username):
    logger.info("Adding user: user_id=%s, username=%s", user_id, username)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users (user_id, first_name, last_name, phone_number, username)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (user_id) DO NOTHING
            """,
                user_id,
                first_name,
                last_name,
                phone_number,
                username,
            )
            logger.info("User added successfully: user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to add user %s: %s", user_id, str(e))
        raise


async def get_user(pool, user_id):
    logger.info("Fetching user: user_id=%s", user_id)
    try:
        async with pool.acquire() as conn:
            user = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            if user:
                logger.info(
                    "User found: user_id=%s, is_subscribed=%s, expires_at=%s",
                    user_id,
                    user["is_subscribed"],
                    user["subscription_expires_at"],
                )
            else:
                logger.info("User not found: user_id=%s", user_id)
            return user
    except Exception as e:
        logger.error("Failed to fetch user %s: %s", user_id, str(e))
        raise


async def update_subscription(pool, user_id, is_subscribed, expires_at):
    logger.info(
        "Updating subscription: user_id=%s, is_subscribed=%s, expires_at=%s", user_id, is_subscribed, expires_at
    )
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET is_subscribed = $2, subscription_expires_at = $3
                WHERE user_id = $1
            """,
                user_id,
                is_subscribed,
                expires_at,
            )
            logger.info("Subscription updated successfully: user_id=%s", user_id)
    except Exception as e:
        logger.error("Failed to update subscription for user %s: %s", user_id, str(e))
        raise


async def get_expiring_subscriptions(pool, days_left):
    logger.info("Fetching subscriptions expiring in %s days", days_left)
    try:
        async with pool.acquire() as conn:
            users = await conn.fetch(
                """
                SELECT user_id, subscription_expires_at
                FROM users
                WHERE is_subscribed = TRUE
                AND subscription_expires_at <= $1
            """,
                datetime.utcnow() + timedelta(days=days_left),
            )
            logger.info("Found %s expiring subscriptions", len(users))
            return users
    except Exception as e:
        logger.error("Failed to fetch expiring subscriptions: %s", str(e))
        raise


async def get_expired_subscriptions(pool):
    logger.info("Fetching expired subscriptions")
    try:
        async with pool.acquire() as conn:
            users = await conn.fetch(
                """
                SELECT user_id, subscription_expires_at
                FROM users
                WHERE is_subscribed = TRUE
                AND subscription_expires_at <= $1
            """,
                datetime.utcnow(),
            )
            logger.info("Found %s expired subscriptions", len(users))
            return users
    except Exception as e:
        logger.error("Failed to fetch expired subscriptions: %s", str(e))
        raise


async def get_stats(pool):
    logger.info("Fetching statistics")
    try:
        async with pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")
            active_subscribers = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM users
                WHERE is_subscribed = TRUE
                AND subscription_expires_at > $1
            """,
                datetime.utcnow(),
            )
            non_subscribers = total_users - active_subscribers
            estimated_income = active_subscribers * 500  # 500₽ per subscription
            stats = {
                "total_users": total_users,
                "active_subscribers": active_subscribers,
                "non_subscribers": non_subscribers,
                "estimated_income": estimated_income,
            }
            logger.info(
                "Statistics retrieved: total_users=%s, active_subscribers=%s, non_subscribers=%s, estimated_income=%s₽",
                total_users,
                active_subscribers,
                non_subscribers,
                estimated_income,
            )
            return stats
    except Exception as e:
        logger.error("Failed to fetch statistics: %s", str(e))
        raise
