from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
USER_DATA_FILE = BASE_DIR / "data" / "my_items.json"


def normalize_id(value) -> str:
    return str(value)


def load_user_data(path: Path = USER_DATA_FILE) -> dict:
    if not path.exists():
        return {"contests": [], "matches": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"contests": [], "matches": []}
    return {
        "contests": payload.get("contests", []) if isinstance(payload.get("contests", []), list) else [],
        "matches": payload.get("matches", []) if isinstance(payload.get("matches", []), list) else [],
    }


def save_user_data(data: dict, path: Path = USER_DATA_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_my_contests() -> list[dict]:
    return load_user_data()["contests"]


def add_my_contest(item: dict) -> tuple[bool, str, list[dict]]:
    data = load_user_data()
    contests = data["contests"]
    exists = any(normalize_id(row.get("id", "")) == normalize_id(item.get("id", "")) for row in contests)
    if exists:
        return False, "已在我的竞赛中", contests
    contests.insert(0, deepcopy(item))
    save_user_data(data)
    return True, "已加入我的竞赛", contests


def remove_my_contest(item_id) -> list[dict]:
    data = load_user_data()
    item_id = normalize_id(item_id)
    data["contests"] = [
        item for item in data["contests"] if normalize_id(item.get("id", "")) != item_id
    ]
    save_user_data(data)
    return data["contests"]


def get_my_matches() -> list[dict]:
    return load_user_data()["matches"]


def add_my_match(item: dict) -> tuple[bool, str, list[dict]]:
    data = load_user_data()
    matches = data["matches"]
    exists = any(
        normalize_id(row.get("id", "")) == normalize_id(item.get("id", ""))
        and row.get("type") == item.get("type")
        for row in matches
    )
    if exists:
        return False, "已在我的匹配中", matches
    matches.insert(0, deepcopy(item))
    save_user_data(data)
    return True, "已加入我的匹配", matches


def remove_my_match(item_id, item_type: str) -> list[dict]:
    data = load_user_data()
    item_id = normalize_id(item_id)
    data["matches"] = [
        item
        for item in data["matches"]
        if not (normalize_id(item.get("id", "")) == item_id and item.get("type") == item_type)
    ]
    save_user_data(data)
    return data["matches"]
