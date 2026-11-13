from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_FILE = DATA_DIR / "contest_knowledge.json"


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _text(value: Any) -> str:
    return str(value or "").strip()


def _keywords(item: dict[str, Any]) -> list[str]:
    return [str(word).strip() for word in item.get("keywords", []) if str(word).strip()]


def _organizers(item: dict[str, Any]) -> list[str]:
    organizers = item.get("organizers")
    if isinstance(organizers, list):
        return [str(row).strip() for row in organizers if str(row).strip()]
    organizer = item.get("organizer") or item.get("source_name")
    return [str(organizer).strip()] if organizer else []


def _prestige_score(item: dict[str, Any]) -> int:
    existing = item.get("prestige_score") or (item.get("prestige") or {}).get("score") if isinstance(item.get("prestige"), dict) else 0
    try:
        score = int(float(existing or 0))
    except (TypeError, ValueError):
        score = 0
    if score:
        return max(1, min(100, score))

    score = 45
    name = _text(item.get("name"))
    category = _text(item.get("category"))
    keywords = " ".join(_keywords(item))
    source = _text(item.get("source_name"))
    haystack = f"{name} {category} {keywords} {source}"
    if any(word in haystack for word in ["全国", "国家", "中国", "国际", "教育部"]):
        score += 20
    if any(word in haystack for word in ["省", "山东", "校内", "校园"]):
        score += 8
    if item.get("is_hit_recognized"):
        score += 15
    if item.get("deadline") or item.get("registration_end_time"):
        score += 4
    if item.get("official_link") or item.get("latest_notice_link"):
        score += 4
    return max(1, min(100, score))


def _prestige_grade(score: int) -> str:
    if score >= 85:
        return "A"
    if score >= 70:
        return "B"
    if score >= 55:
        return "C"
    return "D"


def _competition_level(item: dict[str, Any]) -> str:
    text = " ".join(
        [
            _text(item.get("name")),
            _text(item.get("category")),
            " ".join(_keywords(item)),
            _text(item.get("source_name")),
        ]
    )
    if any(word in text for word in ["国际", "世界"]):
        return "国际级"
    if any(word in text for word in ["全国", "国家", "中国", "教育部"]):
        return "国家级"
    if "省" in text or "山东" in text:
        return "省级"
    if item.get("is_hit_recognized"):
        return "校级/校内认定"
    return "待确认"


def _knowledge_item(item: dict[str, Any]) -> dict[str, Any]:
    score = _prestige_score(item)
    grade = _prestige_grade(score)
    level = _competition_level(item)
    organizers = _organizers(item)
    ranking_included = bool(item.get("ranking_included") or item.get("is_hit_recognized") or score >= 70)
    summary = (
        f"{_text(item.get('name')) or '该竞赛'} 当前含金量评估为 {score} 分，"
        f"{grade} 级，级别判断为{level}。"
    )
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "score": score,
        "grade": grade,
        "competition_level": level,
        "ranking_included": ranking_included,
        "organizers": organizers,
        "summary": summary,
        "dimensions": {
            "source_authority": 20 if any(word in " ".join(organizers) for word in ["教育部", "全国", "中国"]) else 10,
            "hit_recognition": 15 if item.get("is_hit_recognized") else 0,
            "information_completeness": sum(
                1
                for field in ["deadline", "conditions", "official_link", "latest_notice_link"]
                if item.get(field)
            )
            * 5,
        },
    }


def load_knowledge_base(path: Path = KNOWLEDGE_FILE) -> dict[str, Any]:
    if not path.exists():
        return {
            "updated_at": "",
            "contest_count": 0,
            "items": [],
            "by_id": {},
            "by_name": {},
        }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {
            "updated_at": "",
            "contest_count": 0,
            "items": [],
            "by_id": {},
            "by_name": {},
        }
    if not isinstance(data, dict):
        return {
            "updated_at": "",
            "contest_count": 0,
            "items": [],
            "by_id": {},
            "by_name": {},
        }
    data.setdefault("items", [])
    data.setdefault("by_id", {str(item.get("id")): item for item in data.get("items", []) if item.get("id")})
    data.setdefault("by_name", {str(item.get("name")): item for item in data.get("items", []) if item.get("name")})
    data.setdefault("contest_count", len(data.get("items", [])))
    data.setdefault("updated_at", "")
    return data


def build_contest_knowledge(contests: list[dict[str, Any]], corpus: dict[str, Any] | None = None) -> dict[str, Any]:
    items = [_knowledge_item(item) for item in contests if item.get("id") or item.get("name")]
    payload = {
        "updated_at": _now_text(),
        "contest_count": len(items),
        "sources_count": int((corpus or {}).get("sources_count", 0) or 0),
        "items": items,
        "by_id": {str(item.get("id")): item for item in items if item.get("id")},
        "by_name": {str(item.get("name")): item for item in items if item.get("name")},
    }
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    KNOWLEDGE_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _lookup_knowledge(item: dict[str, Any], knowledge: dict[str, Any]) -> dict[str, Any]:
    by_id = knowledge.get("by_id") or {}
    by_name = knowledge.get("by_name") or {}
    item_id = str(item.get("id") or "")
    name = str(item.get("name") or "")
    found = by_id.get(item_id) if item_id else None
    if not found and name:
        found = by_name.get(name)
    return found if isinstance(found, dict) else {}


def attach_knowledge(
    contests: list[dict[str, Any]],
    knowledge: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    knowledge = knowledge or load_knowledge_base()
    if not knowledge.get("items"):
        knowledge = build_contest_knowledge(contests, {})

    enriched: list[dict[str, Any]] = []
    for item in contests:
        row = deepcopy(item)
        info = _lookup_knowledge(row, knowledge)
        if not info:
            info = _knowledge_item(row)
        row.setdefault("prestige_score", info.get("score", 0))
        row.setdefault("prestige_grade", info.get("grade", ""))
        row.setdefault("competition_level", info.get("competition_level", ""))
        row.setdefault("ranking_included", bool(info.get("ranking_included")))
        row.setdefault("organizers", info.get("organizers", []))
        row.setdefault(
            "prestige",
            {
                "score": info.get("score", 0),
                "grade": info.get("grade", ""),
                "competition_level": info.get("competition_level", ""),
                "ranking_included": bool(info.get("ranking_included")),
                "organizers": info.get("organizers", []),
                "summary": info.get("summary", ""),
                "dimensions": info.get("dimensions", {}),
            },
        )
        enriched.append(row)
    return enriched


def knowledge_training_docs(knowledge: dict[str, Any]) -> Iterable[tuple[str, str, dict[str, Any]]]:
    for item in knowledge.get("items", []):
        name = item.get("name") or "竞赛"
        text = (
            f"{name} 含金量评估：{item.get('score')}分，{item.get('grade')}级，"
            f"竞赛级别：{item.get('competition_level')}。{item.get('summary', '')}"
        )
        metadata = {
            "doc_type": "knowledge",
            "id": item.get("id"),
            "name": name,
            "prestige_score": item.get("score", 0),
            "prestige_grade": item.get("grade", ""),
            "competition_level": item.get("competition_level", ""),
            "ranking_included": bool(item.get("ranking_included")),
            "organizers": item.get("organizers", []),
            "source_name": "本地竞赛含金量知识库",
            "keywords": ["含金量", "级别", "认定", "推荐"],
        }
        yield f"knowledge-{item.get('id') or name}", text, metadata


def matching_template_training_docs() -> Iterable[tuple[str, str, dict[str, Any]]]:
    templates = [
        (
            "matching-template-team",
            "组队匹配时，应优先说明竞赛名称、目标赛道、已有成员、缺少角色、需要技能、时间安排和联系方式。",
            ["组队", "队友", "招募", "申请"],
        ),
        (
            "matching-template-mentor",
            "导师匹配时，应结合学院、校区、研究方向、职称和项目经历筛选，先准备简洁的自我介绍和竞赛计划。",
            ["导师", "学院", "校区", "研究方向"],
        ),
        (
            "matching-template-material",
            "报名材料处理时，应核对报名表、作品说明、PPT、证明材料、指导教师信息、提交入口和截止时间。",
            ["材料", "报名", "提交", "截止"],
        ),
    ]
    for doc_id, text, keywords in templates:
        yield doc_id, text, {
            "doc_type": "matching_template",
            "id": doc_id,
            "name": "匹配与参赛流程模板",
            "source_name": "本地匹配流程模板",
            "keywords": keywords,
        }
