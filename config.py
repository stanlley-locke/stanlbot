import json
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Optional, Any, Dict

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_IDS: list[int] = []
    DB_PATH: Path = Path("storage/bot.db")
    LOG_LEVEL: str = "INFO"
    DEFAULT_LANG: str = "en"
    ENABLE_SEMANTIC_SEARCH: bool = False
    ENABLE_WHATSAPP_IMPORT: bool = True
    AWS_REGION: str = "us-east-1"
    EC2_INSTANCE_ID: Optional[str] = None
    DEPLOY_WEBHOOK_URL: Optional[str] = None
    HEALTH_CHECK_URL: Optional[str] = None
    MAX_MEMORY_PERCENT: int = 85
    RATE_LIMIT_MSGS: int = 10
    RATE_LIMIT_WINDOW: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @model_validator(mode="before")
    @classmethod
    def parse_admin_ids(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        raw_ids = values.get("ADMIN_IDS", "")
        if isinstance(raw_ids, str):
            raw_ids = raw_ids.strip()
            if not raw_ids:
                values["ADMIN_IDS"] = []
            elif raw_ids.startswith("["):
                # Handle JSON format: [123, 456]
                try:
                    values["ADMIN_IDS"] = json.loads(raw_ids)
                except json.JSONDecodeError:
                    values["ADMIN_IDS"] = []
            else:
                # Handle comma-separated format: 123,456
                values["ADMIN_IDS"] = [
                    int(x.strip()) for x in raw_ids.split(",") if x.strip().isdigit()
                ]
        return values

settings = Settings()