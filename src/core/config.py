import json
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Scraper & Application Assistant"
    
    PRIVATE_CONFIG_DIR: str = "./my-private-config/job-scraper-autoapply"
    
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/job_sandbox"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    HEADLESS_MODE: bool = True
    MAX_CONCURRENT_SCRAPES: int = 3
    SCRAPE_DELAY_SECONDS: float = 2.5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_private_config_path(filename: str) -> Path:
    candidates = [
        Path(settings.PRIVATE_CONFIG_DIR) / filename,
        Path("./my-private-config") / filename,
        Path("../") / filename,
        Path("./") / filename,
        Path("./") / f"{filename}.example",
    ]

    for path in candidates:
        if path.exists():
            print(f"[DEBUG Config Path] Found config at: {path.resolve()}")
            return path

    raise FileNotFoundError(
        f"Configuration file '{filename}' not found! Searched candidates: {candidates}"
    )


def load_json_config(filename: str = "candidate_profile.json") -> Dict[str, Any]:
    config_path = get_private_config_path(filename)
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data