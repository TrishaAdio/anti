"""Entry point for the sticker-guard Telethon userbot.

Run with: python userbot.py
"""

from __future__ import annotations

import asyncio
import logging
import sys

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.utils import get_display_name

from config import Config, ConfigError
from handlers import register
from store import PermitStore

log = logging.getLogger("stickerguard")


def build_client(config: Config) -> TelegramClient:
    session = StringSession(config.string_session) if config.string_session else str(config.session_path)
    client = TelegramClient(session, config.api_id, config.api_hash)
    client.parse_mode = "html"
    return client


async def run(config: Config) -> None:
    store = PermitStore(config.db_path)
    client = build_client(config)

    await client.start()
    me = await client.get_me()
    register(client, config, store, me.id)

    log.info(
        "signed in as %s (%s) · %d permitted user(s)",
        get_display_name(me) or "unknown",
        me.id,
        len(store),
    )
    log.info("guarding private chats · /permit, /unpermit, /permitted")

    try:
        await client.run_until_disconnected()
    finally:
        store.close()
        if client.is_connected():
            await client.disconnect()


def main() -> int:
    try:
        config = Config.load()
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2

    logging.basicConfig(
        level=getattr(logging, config.log_level, logging.INFO),
        format="%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S",
    )
    logging.getLogger("telethon").setLevel(logging.WARNING)

    try:
        asyncio.run(run(config))
    except KeyboardInterrupt:
        log.info("stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
