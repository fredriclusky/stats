from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str
    sync_database_url: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    partner_token: str
    openai_api_key: str = ""
    admin_username: str = "admin"
    admin_password: str = "changeme123"

    class Config:
        env_file = "/opt/stats-tool/.env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
