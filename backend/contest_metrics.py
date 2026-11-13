from __future__ import annotations

import json
import time
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
METRICS_FILE = BASE_DIR / "data" / "contest_metrics.json"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def load_metrics(path: Path = METRICS_FILE) -> dict:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def save_metrics(metrics: dict, path: Path = METRICS_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")


def record_click(contest_id: str | int) -> dict:
    contest_id = str(contest_id)
    metrics = load_metrics()
    row = metrics.setdefault(contest_id, {"clicks": 0, "last_clicked_at": ""})
    row["clicks"] = int(row.get("clicks", 0)) + 1
    row["last_clicked_at"] = _now_text()
    row["updated_at"] = time.time()
    save_metrics(metrics)
    total_clicks = _total_clicks(metrics)
    return {
        **row,
        "global_click_count": int(row.get("clicks", 0) or 0),
        "global_total_clicks": total_clicks,
        "global_click_rate": _click_rate(int(row.get("clicks", 0) or 0), total_clicks),
    }


def _total_clicks(metrics: dict) -> int:
    total = 0
    for row in metrics.values():
        if isinstance(row, dict):
            total += int(row.get("clicks", 0) or 0)
    return total


def _click_rate(clicks: int, total_clicks: int) -> float:
    if total_clicks <= 0:
        return 0.0
    return round(clicks * 100 / total_clicks, 1)


def attach_metrics(items: list[dict]) -> list[dict]:
    metrics = load_metrics()
    total_clicks = _total_clicks(metrics)
    result = []
    for item in items:
        copied = deepcopy(item)
        row = metrics.get(str(copied.get("id", "")), {})
        clicks = int(row.get("clicks", 0) or 0) if isinstance(row, dict) else 0
        copied["click_count"] = clicks
        copied["global_click_count"] = clicks
        copied["global_total_clicks"] = total_clicks
        copied["global_click_rate"] = _click_rate(clicks, total_clicks)
        copied["last_clicked_at"] = row.get("last_clicked_at", "") if isinstance(row, dict) else ""
        result.append(copied)
    return result


def _date_value(value: str) -> date | None:
    try:
        return datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def get_recent_items(items: list[dict], limit: int = 6) -> list[dict]:
    today = date.today()
    enriched = attach_metrics(items)
    upcoming = []
    for item in enriched:
        deadline = _date_value(str(item.get("deadline", "")))
        if deadline and deadline >= today:
            upcoming.append((deadline, item))
    upcoming.sort(key=lambda pair: (pair[0], pair[1].get("status") != "报名中"))

    result = [item for _, item in upcoming[:limit]]
    if len(result) >= limit:
        return result

    seen = {str(item.get("id", "")) for item in result}
    live_status = [
        item
        for item in enriched
        if str(item.get("id", "")) not in seen and item.get("status") in {"报名中", "即将开始"}
    ]
    live_status.sort(key=lambda item: (item.get("status") != "报名中", item.get("name", "")))
    return result + live_status[: limit - len(result)]


def get_hot_items(items: list[dict], limit: int = 6) -> list[dict]:
    enriched = attach_metrics(items)
    enriched.sort(
        key=lambda item: (
            -float(item.get("global_click_rate", 0) or 0),
            -int(item.get("global_click_count", 0) or 0),
            not bool(item.get("is_hit_recognized")),
            not bool(item.get("has_deadline")),
            item.get("handbook_rank", 999),
        )
    )
    return enriched[:limit]


def get_contest_sections(items: list[dict], limit: int = 6) -> dict:
    return {
        "recent": get_recent_items(items, limit),
        "hot": get_hot_items(items, limit),
    }
