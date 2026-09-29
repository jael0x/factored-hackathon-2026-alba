from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://alba:alba@localhost:5432/alba"
    jwt_secret: str = ""
    openai_api_key: str = ""
    llm_model: str = "gpt-6-luna"
    demo_inbox: bool = False

    @field_validator("demo_inbox", mode="before")
    @classmethod
    def parse_demo_inbox(cls, value: object) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"1", "true", "yes", "on"}


settings = Settings()
