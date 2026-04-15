import json
import os
from threading import Lock

FILE = "alerts_data.json"
lock = Lock()
data = {}


def _load():
    global data
    if os.path.exists(FILE):
        with open(FILE, "r") as f:
            data = json.load(f)


def _save():
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)


def _user(uid):
    if uid not in data:
        data[uid] = {
            "enabled": True,
            "alerts": [],
            "next_id": 1
        }
    return data[uid]


def add_alert(uid, asset, price, direction, note=""):
    with lock:
        u = _user(uid)
        aid = u["next_id"]

        u["alerts"].append({
            "id": aid,
            "asset": asset,
            "price": price,
            "direction": direction,
            "note": note,
            "last_alerted": 0
        })

        u["next_id"] += 1
        _save()
        return aid


def remove_alert(uid, aid):
    with lock:
        u = _user(uid)
        u["alerts"] = [a for a in u["alerts"] if a["id"] != aid]
        _save()


def get_alerts(uid):
    return _user(uid)["alerts"]


def get_all_users():
    return list(data.keys())


def is_enabled(uid):
    return _user(uid)["enabled"]


def set_enabled(uid, val):
    _user(uid)["enabled"] = val
    _save()


def update_last_alerted(uid, aid, t):
    u = _user(uid)
    for a in u["alerts"]:
        if a["id"] == aid:
            a["last_alerted"] = t
            break
    _save()


_load()