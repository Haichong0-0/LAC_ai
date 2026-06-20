"""Project-wide settings, loaded from environment / `.env`."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    llm_model: str = Field(default="claude-haiku-4-5", alias="LAC_LLM_MODEL")
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="LAC_EMBEDDING_MODEL")
    top_k: int = Field(default=5, alias="LAC_TOP_K")
    min_score: float = Field(default=0.65, alias="LAC_MIN_SCORE")

    chroma_dir: Path = Field(default=PROJECT_ROOT / "chroma_db", alias="LAC_CHROMA_DIR")
    collection: str = Field(default="corpus", alias="LAC_COLLECTION")

    title_list: Path = Field(default=PROJECT_ROOT / "data" / "title_list.json", alias="LAC_TITLE_LIST")
    corpus_path: Path = Field(default=PROJECT_ROOT / "data" / "corpus.jsonl", alias="LAC_CORPUS_PATH")


settings = Settings()
