from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_id: int
    channel_id: str
    payment_link: str = "https://example.com/payment"
    db: dict = {
        "path": "./bot.db"  # SQLite uses file path instead of host/port
    }

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


config = Settings()
