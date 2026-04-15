"""
Storage — সব অ্যালার্ট JSON ফাইলে সেভ করে রাখে
"""

import json
import os
from threading import Lock

STORAGE_FILE = "alerts_data.json"
_lock = Lock()
_data: dict = {}


def _load():
    global _data
    if os.path.exists(STORAGE_FILE):
        with open(STORAGE_FILE, "r", encoding="utf-8") as f:
            _data = json.load(f)


def _save():
    with open(STORAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(_data, f, indent=2, ensure_ascii=False)


def _get_user(user_id: str) -> dict:
    if user_id not in _data:
        _data[user_id] = {"enabled": True, "alerts": [], "next_id": 1, "menu_message_ids": []}
    return _data[user_id]


def add_alert(user_id: str, asset: str, price: float, direction: str, note: str = "") -> int:
    with _lock:
        user = _get_user(user_id)
        alert_id = user["next_id"]
        user["alerts"].append({
            "id": alert_id,
            "asset": asset,
            "price": price,
            "direction": direction,
            "note": note,
            "triggered": False,   # একবার hit হলে True — তারপর সবসময় alert আসবে
            "last_alerted": 0
        })
        user["next_id"] += 1
        _save()
        return alert_id


def mark_triggered(user_id: str, alert_id: int):
    """প্রথমবার price hit হলে triggered=True সেট করো।"""
    with _lock:
        user = _get_user(user_id)
        for a in user["alerts"]:
            if a["id"] == alert_id:
                a["triggered"] = True
                break
        _save()


def remove_alert(user_id: str, alert_id: int) -> bool:
    with _lock:
        user = _get_user(user_id)
        before = len(user["alerts"])
        user["alerts"] = [a for a in user["alerts"] if a["id"] != alert_id]
        changed = len(user["alerts"]) < before
        if changed:
            _save()
        return changed


def get_alerts(user_id: str) -> list:
    with _lock:
        return list(_get_user(user_id)["alerts"])


def get_all_users() -> list:
    with _lock:
        return list(_data.keys())


def is_enabled(user_id: str) -> bool:
    with _lock:
        return _get_user(user_id).get("enabled", True)


def set_enabled(user_id: str, value: bool):
    with _lock:
        _get_user(user_id)["enabled"] = value
        _save()


def update_last_alerted(user_id: str, alert_id: int, timestamp: float):
    with _lock:
        user = _get_user(user_id)
        for a in user["alerts"]:
            if a["id"] == alert_id:
                a["last_alerted"] = timestamp
                break
        _save()


# ── Menu message tracking (পুরনো বাটন delete করার জন্য) ──

def save_menu_message(user_id: str, message_id: int):
    """যে menu/button message পাঠানো হয়েছে তার ID সেভ করো।"""
    with _lock:
        user = _get_user(user_id)
        ids = user.get("menu_message_ids", [])
        ids.append(message_id)
        user["menu_message_ids"] = ids[-20:]
        _save()


def pop_menu_messages(user_id: str) -> list:
    """সব saved message ID নিয়ে নাও এবং list খালি করো।"""
    with _lock:
        user = _get_user(user_id)
        ids = user.get("menu_message_ids", [])
        user["menu_message_ids"] = []
        if ids:
            _save()
        return ids


_load()