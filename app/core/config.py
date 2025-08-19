from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    ENV: str = "development"
    DEBUG: bool = True

    DB_USER: str = "postgres"
    DB_PW: str = "postgres"
    DB_HOST: str = "localhost"
    DATABASE: str = "scourt"

    KAKAO_NOTI_API_URL: str
    KAKAO_NOTI_SECRET_KEY: str
    KAKAO_NOTI_APP_KEY: str
    KAKAO_NOTI_SENDER_KEY: str

    @property
    def DATABASE_URL(self):
        return (
            f"postgresql://{self.DB_USER}:{self.DB_PW}@{self.DB_HOST}/{self.DATABASE}"
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
