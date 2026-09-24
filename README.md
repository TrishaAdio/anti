# sticker-guard

A Telethon userbot that runs on your own Telegram account. Any sticker someone sends you in a
private chat is deleted for both sides the moment it arrives, with no reply of any kind. Send
`/permit` in that person's DM and their stickers are left alone from then on.

Groups and channels are never touched — every handler is filtered to private chats.

## Commands

All commands are typed by you, in the DM of the person they apply to. `.` and `!` work as prefixes
too (`.permit`, `!permit`).

| Command | Effect |
| --- | --- |
| `/permit` | Allow stickers from this chat partner |
| `/unpermit` | Block them again |
| `/permitted` | List everyone currently allowed |

The command message is edited into a short status card and then removed after `CARD_TTL` seconds.

## Setup

```bash
cd sticker-guard
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # then fill in API_ID and API_HASH
python userbot.py
```

`API_ID` / `API_HASH` come from <https://my.telegram.org/apps>. The first run asks for your phone
number, the login code, and your 2FA password if you have one. That creates
`sticker_guard.session` next to `userbot.py`; later runs reuse it and start straight away.

Permits live in `permits.db` (SQLite), so they survive restarts.

### Running on a server

Generate a session string locally and pass it through `STRING_SESSION` instead of copying the
`.session` file:

```bash
python -c "from telethon.sync import TelegramClient; from telethon.sessions import StringSession; \
print(TelegramClient(StringSession(), API_ID, 'API_HASH').start().session.save())"
```

## Settings

| Variable | Default | Meaning |
| --- | --- | --- |
| `API_ID`, `API_HASH` | — | Required Telegram app credentials |
| `SESSION_NAME` | `sticker_guard` | Session file name |
| `STRING_SESSION` | empty | Use a session string instead of a file |
| `DB_PATH` | `permits.db` | Permit database location |
| `CARD_TTL` | `6` | Seconds before a `/permit` status card self-deletes (`0` keeps it) |
| `IGNORE_BOTS` | `true` | Leave DMs with bots alone |
| `LOG_LEVEL` | `INFO` | `DEBUG` for verbose Telethon-side detail |

## Behaviour notes

- Deletions are silent. The sender gets no warning message, only the vanished sticker.

- Static, animated (`.tgs`) and video (`.webm`) stickers are all covered.
- Deletion uses `revoke=True`, which in private chats removes the message for both participants.
- Only live messages are handled. Stickers that arrive while the process is down stay in the chat.
- Your own stickers are never deleted, and Saved Messages is left alone.
