import json
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Job Scraper & Application Assistant"
    
    # Path pointing to your project folder inside the private config submodule
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
    """
    Resolves configuration files from the central private config repository.
    Searches:
    1. ./my-private-config/job-scraper-autoapply/<filename>
    2. ./my-private-config/<filename>
    3. ../<filename>
    4. ./<filename>
    5. ./<filename>.example
    """
    candidates = [
        Path(settings.PRIVATE_CONFIG_DIR) / filename,
        Path("./my-private-config") / filename,
        Path("../") / filename,
        Path("./") / filename,
        Path("./") / f"{filename}.example",
    ]

    for path in candidates:
        if path.exists():
            return path

    raise FileNotFoundError(
        f"Configuration file '{filename}' not found! Searched in {settings.PRIVATE_CONFIG_DIR}"
    )


def load_json_config(filename: str = "candidate_profile.json") -> Dict[str, Any]:
    """Loads any JSON configuration file from the private repo path."""
    config_path = get_private_config_path(filename)
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)