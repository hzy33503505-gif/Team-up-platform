from __future__ import annotations

from typing import Any


def generated_training_docs(
    contests: list[dict[str, Any]],
) -> tuple[list[tuple[str, str, dict[str, Any]]], dict[str, Any]]:
    docs: list[tuple[str, str, dict[str, Any]]] = []
    for item in contests[:200]:
        contest_id = item.get("id") or item.get("name")
        name = item.get("name") or "竞赛"
        if not contest_id:
            continue
        deadline = item.get("deadline") or item.get("registration_end_time") or "以官网通知为准"
        category = item.get("category") or "综合"
        status = item.get("status") or "待官网更新"
        conditions = item.get("conditions") or item.get("target_audience") or "参赛条件以官网通知为准"
        bonus = item.get("bonus_summary") or "校内加分以学校和学院当年认定为准"
        link = item.get("official_link") or item.get("latest_notice_link") or "暂无官网链接"
        keywords = [str(word) for word in item.get("keywords", [])[:8]]
        text = (
            f"{name} 是{category}类竞赛，当前状态为{status}。"
            f"报名截止或关键时间：{deadline}。"
            f"参赛条件：{conditions}。"
            f"校内认定/加分：{bonus}。"
            f"官网或通知入口：{link}。"
        )
        metadata = {
            "doc_type": "synthetic_contest_qa",
            "id": contest_id,
            "name": name,
            "category": category,
            "status": status,
            "deadline": deadline,
            "conditions": conditions,
            "bonus_summary": bonus,
            "official_link": link,
            "source_name": "本地竞赛库自动扩写语料",
            "keywords": keywords,
            "is_hit_recognized": bool(item.get("is_hit_recognized")),
            "prestige_score": item.get("prestige_score") or (item.get("prestige") or {}).get("score", 0)
            if isinstance(item.get("prestige"), dict)
            else item.get("prestige_score", 0),
            "prestige_grade": item.get("prestige_grade") or (item.get("prestige") or {}).get("grade", "")
            if isinstance(item.get("prestige"), dict)
            else item.get("prestige_grade", ""),
            "competition_level": item.get("competition_level")
            or ((item.get("prestige") or {}).get("competition_level", "") if isinstance(item.get("prestige"), dict) else ""),
        }
        docs.append((f"synthetic-contest-{contest_id}", text, metadata))
    return docs, {
        "counts": {
            "synthetic_contest_qa": len(docs),
        }
    }
