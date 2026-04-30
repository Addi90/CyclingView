from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CV_", env_file=".env", extra="ignore")

    # Repo root contains the Strava export and the data/ output dir.
    repo_root: Path = Path(__file__).resolve().parents[2]
    data_dir: Path = Path(__file__).resolve().parents[2] / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "cycling.db"

    @property
    def streams_dir(self) -> Path:
        return self.data_dir / "streams"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
