"""Configuration loading for the sticker-guard userbot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:  # optional dependency, only needed for .env files
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent

TRUE_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_VALUES = {"0", "false", "no", "n", "off"}


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or malformed."""


def _flag(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    value = raw.strip().lower()
    if value in TRUE_VALUES:
        return True
    if value in FALSE_VALUES:
        return False
    raise ConfigError(f"{name} must be a boolean value, got {raw!r}")


def _integer(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw.strip())
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer, got {raw!r}") from exc


def _text(name: str, default: str) -> str:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip()


@dataclass(frozen=True)
class Config:
    api_id: int
    api_hash: str
    session_path: Path
    string_session: str | None
    db_path: Path
    card_ttl: int
    ignore_bots: bool
    log_level: str

    @classmethod
    def load(cls) -> Config:
        if load_dotenv is not None:
            load_dotenv(BASE_DIR / ".env")

        raw_api_id = os.getenv("API_ID", "").strip()
        api_hash = os.getenv("API_HASH", "").strip()
        if not raw_api_id or not api_hash:
            raise ConfigError(
                "API_ID and API_HASH are required. Copy .env.example to .env and fill them in "
                "with credentials from https://my.telegram.org/apps"
            )
        try:
            api_id = int(raw_api_id)
        except ValueError as exc:
            raise ConfigError(f"API_ID must be an integer, got {raw_api_id!r}") from exc

        string_session = os.getenv("STRING_SESSION", "").strip() or None
        session_name = _text("SESSION_NAME", "sticker_guard")
        db_name = _text("DB_PATH", "permits.db")

        return cls(
            api_id=api_id,
            api_hash=api_hash,
            session_path=(BASE_DIR / session_name).resolve(),
            string_session=string_session,
            db_path=(BASE_DIR / db_name).resolve(),
            card_ttl=_integer("CARD_TTL", 6),
            ignore_bots=_flag("IGNORE_BOTS", True),
            log_level=_text("LOG_LEVEL", "INFO").upper(),
        )
