from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTAID_", env_file=".env", extra="ignore")
    db_url: str = "sqlite+aiosqlite:///./agentaid.db"
    online_eval_sample_rate: float = 1.0
    judge_model_default: str = "claude-haiku-4-5"
    cost_budget_default: float = 0.50

settings = Settings()
