import json
import time
import html
import requests
from mcstatus import JavaServer

POLL_SECONDS = 120
STATE_FILE   = "status_message.json"
CHAT_ID      = "-1003582561415"
TOPIC_ID     = 6478
SERVER_ADDR  = "109.248.250.97:25591"
BOT_TOKEN    = "8618284736:AAHNsQJLCyjdpZPwQ4SR8qZLm2WaKW0qx5U"

API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def load_message_id() -> None:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f).get("message_id")
    except(OSError, json.JSONDecodeError):
        return None


def save_message_id(message_id: int) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f)


def update_status(message_id: str, text: str) -> str:
    if message_id is not None and edit(message_id, text):
        return message_id
    return post_new(text)


def edit(message_id, text):
    resp = tg_call("editMessageText", {
        "chat_id": CHAT_ID, "message_id": message_id,
        "text": text, "parse_mode": "HTML",
    })
    if resp is None:
        return None
    if resp.get("ok"):
        return True
    desc = resp.get("description", "")
    if "message is not modified" in desc:
        return True
    print(time.strftime("%d.%m %H:%M:%S"), "edit error:", desc)
    return False


def get_online() -> None:
    try:
        status = JavaServer.lookup(SERVER_ADDR).status()
    except Exception:
        return None
    sample = status.players.sample or []
    return sorted(player.name for player in sample)


def build_text(players) -> str:
    if players is None:
        return "🔴 Сервер недоступен"
    if not players:
        return "🟢 Сервер онлайн\n👥 Игроков: 0"
    lines = ["🟢 Сервер онлайн", f"👥 Игроков: {len(players)}", ""]
    lines += [f"• {html.escape(name)}" for name in players]
    return "\n".join(lines)

def post_new(text):
    resp = tg_call("sendMessage", {
        "chat_id": CHAT_ID, "message_thread_id": TOPIC_ID,
        "text": text, "parse_mode": "HTML",
    })
    if resp and resp.get("ok"):
        mid = resp["result"]["message_id"]
        try:
            save_message_id(mid)
        except OSError as exc:
            print("Не смог сохранить state-файл:", exc)
        return mid
    if resp:
        print("sendMessage error:", resp.get("description"))
    return None


def main() -> None:
    print(f"Bot running. Every {POLL_SECONDS} seconds check")
    message_id = load_message_id()

    prev = get_online()
    message_id = update_status(message_id, build_text(prev))

    while True:
        time.sleep(POLL_SECONDS)
        try:
            players = get_online()
            if players == prev:
                continue
            new_id = update_status(message_id, build_text(players))
            if new_id is not None:
                message_id = new_id
                prev = players
        except Exception as exc:
            print(time.strftime("%d.%m %H:%M:%S"), "loop error:", exc)


def tg_call(method: str, data: dict):
    try:
        return requests.post(f"{API}/{method}", data=data, timeout=10).json()
    except Exception as exc:
        print(time.strftime("%d.%m %H:%M:%S"), f"{method} failed:", exc)
        return None


if __name__ == "__main__":
    main()

