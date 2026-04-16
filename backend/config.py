import json
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Dict, Any, Optional

_CONFIG_PATH = Path(__file__).parent / "config.json"
_config_cache: Optional[Dict[str, Any]] = None


def _load_config() -> Dict[str, Any]:
    global _config_cache
    if _config_cache is None:
        if _CONFIG_PATH.exists():
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                _config_cache = json.load(f)
        else:
            _config_cache = {}
    return _config_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    PROJECT_NAME: str = "Advanced Interview Prep System"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_KEY: str

    # LLM API Keys
    GEMINI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""

    @property
    def config(self) -> Dict[str, Any]:
        return _load_config()

    @property
    def ROLES(self) -> Dict[str, Any]:
        return self.config.get("roles", {})

    @property
    def CATEGORIES(self) -> Dict[str, Any]:
        return self.config.get("categories", {})

    @property
    def LLM_PROVIDERS(self) -> Dict[str, Any]:
        return self.config.get("llm_providers", {})


settings = Settings()
