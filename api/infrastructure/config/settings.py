from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

JWT_SECRET_MIN_LENGTH = 32
DB_POOL_MIN_DEFAULT = 1
DB_POOL_MAX_DEFAULT = 10


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://alba:alba@localhost:5432/alba"
    jwt_secret: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-6-luna"
    demo_login: bool = False
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    mail_from: str = "Alba <no-reply@alba.local>"
    db_pool_min: int = DB_POOL_MIN_DEFAULT
    db_pool_max: int = DB_POOL_MAX_DEFAULT

    @field_validator("demo_login", mode="before")
    @classmethod
    def parse_demo_login(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}


def require_jwt_secret(secret: str) -> None:
    if len(secret) < JWT_SECRET_MIN_LENGTH:
        raise RuntimeError(
            f"JWT_SECRET is missing or shorter than {JWT_SECRET_MIN_LENGTH} characters. "
            "Set it in .env (for example: openssl rand -hex 32)."
        )


settings = Settings()
