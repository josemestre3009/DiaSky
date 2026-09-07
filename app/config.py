from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    admin_token: str
    webhook_secret: str
    webhook_path_token: str
    timezone: str = "America/Bogota"
    evolution_api_url: str
    evolution_api_key: str = ""
    evolution_instance_name: str = ""
    evolution_webhook_secret: str = ""
    evolution_send_text_path: str = "/message/sendText/{instance}"
    operation_group_jids: str
    authorized_creator_jids: str
    report_recipient_jid: str
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.5-flash-lite"
    openrouter_min_confidence: float = 0.8

    @property
    def authorized_creators(self) -> set[str]:
        return {jid.strip() for jid in self.authorized_creator_jids.split(",") if jid.strip()}

    @property
    def operation_groups(self) -> set[str]:
        return {jid.strip() for jid in self.operation_group_jids.split(",") if jid.strip()}


@lru_cache
def settings() -> Settings:
    return Settings()
