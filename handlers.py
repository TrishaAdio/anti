"""Event handlers: sticker removal in DMs plus the /permit command set."""

from __future__ import annotations

import asyncio
import html
import logging

from telethon import TelegramClient, events
from telethon.errors import FloodWaitError, MessageDeleteForbiddenError, RPCError
from telethon.tl.types import User
from telethon.utils import get_display_name

from config import Config
from store import PermitStore

__all__ = ["register"]

log = logging.getLogger("stickerguard")

_background: set[asyncio.Task] = set()


def _spawn(coro) -> None:
    """Fire and forget a coroutine while keeping a strong reference to the task."""
    task = asyncio.ensure_future(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _delete_after(client: TelegramClient, chat_id: int, message_id: int, delay: int) -> None:
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, [message_id], revoke=True)
    except RPCError as exc:
        log.debug("could not clean up message %s in %s: %s", message_id, chat_id, exc)


def _label(user: User | None, user_id: int) -> str:
    name = get_display_name(user) if user is not None else ""
    if not name:
        return f"<code>{user_id}</code>"
    return f"<b>{html.escape(name)}</b> · <code>{user_id}</code>"


def register(client: TelegramClient, config: Config, store: PermitStore, me_id: int) -> None:
    """Attach every handler to the client."""

    async def reply_card(event, text: str) -> None:
        """Turn the issued command into a status card, then tidy it away."""
        try:
            message = await event.edit(text)
        except RPCError:
            message = await event.respond(text)
        if config.card_ttl > 0 and message is not None:
            _spawn(_delete_after(client, event.chat_id, message.id, config.card_ttl))

    @client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
    async def drop_stickers(event) -> None:
        if not event.sticker:
            return

        sender_id = event.sender_id
        if sender_id is None or sender_id == me_id:
            return
        if store.is_permitted(sender_id):
            return

        sender = await event.get_sender()
        if config.ignore_bots and getattr(sender, "bot", False):
            return

        try:
            await client.delete_messages(event.chat_id, [event.id], revoke=True)
        except MessageDeleteForbiddenError:
            log.warning("not allowed to delete sticker %s from %s", event.id, sender_id)
            return
        except FloodWaitError as exc:
            log.warning("flood wait of %ss while deleting sticker from %s", exc.seconds, sender_id)
            return
        except RPCError as exc:
            log.error("failed to delete sticker from %s: %s", sender_id, exc)
            return

        log.info("deleted sticker from %s (%s)", get_display_name(sender) or "unknown", sender_id)

    @client.on(
        events.NewMessage(
            outgoing=True,
            pattern=r"^[./!]permit$",
            func=lambda e: e.is_private,
        )
    )
    async def permit(event) -> None:
        user_id = event.chat_id
        if user_id == me_id:
            await reply_card(event, "▸ Nothing to permit here.")
            return

        peer = await event.get_chat()
        name = get_display_name(peer) or None
        if store.grant(user_id, name):
            await reply_card(event, f"◈ Stickers allowed\n▸ {_label(peer, user_id)}")
            log.info("permitted %s (%s)", name or "unknown", user_id)
        else:
            await reply_card(event, f"▸ Already allowed\n▸ {_label(peer, user_id)}")

    @client.on(
        events.NewMessage(
            outgoing=True,
            pattern=r"^[./!]unpermit$",
            func=lambda e: e.is_private,
        )
    )
    async def unpermit(event) -> None:
        user_id = event.chat_id
        peer = await event.get_chat()
        if store.revoke(user_id):
            await reply_card(event, f"◈ Stickers blocked\n▸ {_label(peer, user_id)}")
            log.info("unpermitted %s (%s)", get_display_name(peer) or "unknown", user_id)
        else:
            await reply_card(event, f"▸ Already blocked\n▸ {_label(peer, user_id)}")

    @client.on(
        events.NewMessage(
            outgoing=True,
            pattern=r"^[./!]permitted$",
            func=lambda e: e.is_private,
        )
    )
    async def permitted(event) -> None:
        entries = store.all()
        if not entries:
            await reply_card(event, "▸ No permits")
            return
        lines = [f"◈ Permitted · {len(entries)}"]
        for entry in entries[:50]:
            name = html.escape(entry.name) if entry.name else str(entry.user_id)
            lines.append(f"▪ {name} · <code>{entry.user_id}</code>")
        if len(entries) > 50:
            lines.append(f"∙ and {len(entries) - 50} more")
        await reply_card(event, "\n".join(lines))
