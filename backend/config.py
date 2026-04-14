import os
import json
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Dict, List, Any

class Settings(BaseSettings):
    PROJECT_NAME: str = "Advanced Interview Prep System"
    API_V1_STR: str = "/api"
    
    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    
    # LLM API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Load dynamic config from JSON
    _config_path: Path = Path(__file__).parent / "config.json"
    
    @property
    def config(self) -> Dict[str, Any]:
        if not self._config_path.exists():
            return {}
        with open(self._config_path, "r") as f:
            return json.load(f)
            
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
