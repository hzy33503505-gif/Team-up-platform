from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from contest_knowledge import (
    attach_knowledge,
    build_contest_knowledge,
    knowledge_training_docs,
    matching_template_training_docs,
)
from generated_training_corpus import generated_training_docs
from web_training_corpus import collect_training_corpus, load_training_corpus


BASE_DIR = Path(__file__).resolve().parent
MODEL_FILE = BASE_DIR / "data" / "self_competition_model.json"
MODEL_NAME = "HIT-Contest-ZeroModel-v5"
MODEL_LABEL = "自训练竞赛领域模型"
MODEL_VERSION = "5.0"


INTENT_KEYWORDS = {
    "deadline": ["报名", "截止", "时间", "什么时候", "日程", "赛程"],
    "condition": ["条件", "资格", "对象", "要求", "能不能", "适合"],
    "bonus": ["加分", "学分", "推免", "奖励", "认定"],
    "official": ["官网", "链接", "网址", "入口", "通知"],
    "recommend": ["推荐", "适合", "参加什么", "选哪个", "有哪些"],
    "career_plan": ["规划", "路线", "生涯", "三个月", "大学四年", "保研", "就业"],
    "team_match": ["组队", "队友", "招募", "申请", "匹配", "找人"],
    "material": ["材料", "方案", "答辩", "ppt", "报名表", "申报书", "计划书", "润色"],
    "mentor": ["导师", "课题组", "实验室", "研究方向", "老师"],
    "prestige": ["含金量", "级别", "榜单", "排行榜", "主办单位", "参赛规模", "获奖比例", "获奖数量", "行业认可", "竞赛价值"],
}


def _now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _source_hash(contests: list[dict[str, Any]], corpus: dict[str, Any] | None = None) -> str:
    corpus = corpus or load_training_corpus()
    compact = [
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "deadline": item.get("deadline"),
            "status": item.get("status"),
            "conditions": item.get("conditions"),
            "bonus": item.get("bonus_summary"),
            "link": item.get("official_link") or item.get("latest_notice_link"),
            "prestige_score": item.get("prestige_score"),
            "prestige_grade": item.get("prestige_grade"),
            "ranking_included": item.get("ranking_included"),
        }
        for item in contests
    ]
    compact_web = [
        {
            "id": item.get("id"),
            "title": item.get("title"),
            "url": item.get("url"),
            "text": str(item.get("text", ""))[:260],
        }
        for item in corpus.get("docs", [])
    ]
    payload = {"contests": compact, "web": compact_web}
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _zh_ngrams(text: str) -> list[str]:
    chunks = re.findall(r"[\u4e00-\u9fff]+", text)
    tokens: list[str] = []
    for chunk in chunks:
        if len(chunk) == 1:
            tokens.append(chunk)
            continue
        for size in (2, 3, 4):
            if len(chunk) >= size:
                tokens.extend(chunk[i : i + size] for i in range(len(chunk) - size + 1))
        if len(chunk) <= 8:
            tokens.append(chunk)
    return tokens


def tokenize(text: str) -> list[str]:
    text = _clean(text).lower()
    words = re.findall(r"[a-z0-9+#.]+", text)
    return words + _zh_ngrams(text)


def _contest_text(item: dict[str, Any]) -> str:
    fields = [
        item.get("name"),
        item.get("category"),
        item.get("tag"),
        " ".join(str(word) for word in item.get("keywords", [])),
        item.get("status"),
        item.get("deadline"),
        item.get("registration_start_time"),
        item.get("registration_end_time"),
        item.get("conditions"),
        item.get("target_audience"),
        item.get("bonus_summary"),
        item.get("special_bonus_note"),
        item.get("competition_level"),
        item.get("prestige_score"),
        item.get("prestige_grade"),
        " ".join(str(word) for word in item.get("organizers", [])),
        (item.get("prestige") or {}).get("summary") if isinstance(item.get("prestige"), dict) else "",
        " ".join(
            f"{key}{value}"
            for key, value in ((item.get("prestige") or {}).get("dimensions") or {}).items()
        )
        if isinstance(item.get("prestige"), dict)
        else "",
        item.get("desc"),
        item.get("rules"),
        " ".join(str(row.get("title", "")) + " " + str(row.get("time", "")) for row in item.get("schedule", [])),
    ]
    return " ".join(_clean(field) for field in fields if field)


def _web_text(item: dict[str, Any]) -> str:
    fields = [
        item.get("title"),
        item.get("source_name"),
        item.get("source_type"),
        " ".join(str(word) for word in item.get("keywords", [])),
        item.get("text"),
    ]
    return " ".join(_clean(field) for field in fields if field)


def _metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_type": "contest",
        "id": item.get("id"),
        "name": item.get("name"),
        "category": item.get("category") or "综合",
        "status": item.get("status") or "待官网更新",
        "deadline": item.get("deadline") or "",
        "registration_start_time": item.get("registration_start_time") or "",
        "registration_end_time": item.get("registration_end_time") or item.get("deadline") or "",
        "conditions": item.get("conditions") or item.get("target_audience") or "",
        "bonus_summary": item.get("bonus_summary") or "",
        "special_bonus_note": item.get("special_bonus_note") or "",
        "official_link": item.get("official_link") or item.get("latest_notice_link") or "",
        "latest_notice_link": item.get("latest_notice_link") or "",
        "source_name": item.get("source_name") or "竞赛官网",
        "is_hit_recognized": bool(item.get("is_hit_recognized")),
        "keywords": item.get("keywords", [])[:10],
        "desc": item.get("desc") or item.get("description") or "",
        "prestige_score": item.get("prestige_score") or (item.get("prestige") or {}).get("score", 0),
        "prestige_grade": item.get("prestige_grade") or (item.get("prestige") or {}).get("grade", ""),
        "competition_level": item.get("competition_level") or (item.get("prestige") or {}).get("competition_level", ""),
        "ranking_included": bool(item.get("ranking_included") or (item.get("prestige") or {}).get("ranking_included")),
        "organizers": item.get("organizers") or (item.get("prestige") or {}).get("organizers", []),
        "prestige_summary": (item.get("prestige") or {}).get("summary", "") if isinstance(item.get("prestige"), dict) else "",
    }


def _web_metadata(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_type": "web",
        "id": item.get("id"),
        "name": item.get("title") or item.get("source_name") or "网络训练资料",
        "title": item.get("title") or item.get("source_name") or "网络训练资料",
        "category": item.get("source_type") or "网络资料",
        "status": "",
        "deadline": "",
        "conditions": "",
        "bonus_summary": "",
        "special_bonus_note": "",
        "official_link": item.get("url") or "",
        "latest_notice_link": item.get("url") or "",
        "source_name": item.get("source_name") or "网络公开资料",
        "source_type": item.get("source_type") or "网络资料",
        "is_hit_recognized": False,
        "keywords": item.get("keywords", [])[:12],
        "desc": str(item.get("text", ""))[:420],
    }


def _has_specific_value(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    vague = {
        "以官网通知为准",
        "待官网更新",
        "暂无官网链接",
        "参赛条件以官网通知为准",
        "校内加分以学生手册和学院认定为准",
    }
    return text not in vague


def _instruction_metadata(item: dict[str, Any], intent: str, question: str) -> dict[str, Any]:
    meta = _metadata(item)
    meta["doc_type"] = "instruction"
    meta["training_kind"] = "generated_qa"
    meta["intent"] = intent
    meta["question"] = question
    meta["source_name"] = "竞赛库自动生成问答样本"
    return meta


def _category_strategy(category: str) -> str:
    category = category or "综合"
    if any(word in category for word in ["计算机", "软件", "人工智能", "信息", "数据"]):
        return "优先补齐编程基础、数据处理、模型/系统实现、代码管理和答辩展示，组队时至少覆盖算法/后端/前端或文档表达。"
    if any(word in category for word in ["数学", "统计", "建模"]):
        return "优先训练建模套路、论文写作、数据分析和可解释性表达，组队时覆盖建模、编程、论文三类能力。"
    if any(word in category for word in ["电子", "机器人", "工程", "智能车"]):
        return "优先确认器材、规则、场地调试和工程可靠性，组队时覆盖硬件、控制、软件和测试记录。"
    if any(word in category for word in ["创新", "创业", "挑战杯", "互联网"]):
        return "优先打磨问题价值、用户/市场证据、技术实现、商业闭环和路演材料，组队时需要产品、技术、调研和答辩分工。"
    if any(word in category for word in ["外语", "英语", "广告", "艺术", "设计"]):
        return "优先理解命题要求、表达风格、作品规范和展示材料，组队时覆盖创意、文案、视觉/视频和现场表达。"
    return "优先核对官网规则、报名时间、参赛资格、提交材料和校内认定，再按个人兴趣与可投入时间决定是否加入。"


def _instruction_docs(contests: list[dict[str, Any]]) -> list[tuple[str, str, dict[str, Any]]]:
    docs: list[tuple[str, str, dict[str, Any]]] = []
    categories: dict[str, list[dict[str, Any]]] = {}
    for item in contests:
        if not item.get("id") or not item.get("name"):
            continue
        name = _clean(item.get("name"))
        category = _clean(item.get("category") or "综合")
        categories.setdefault(category, []).append(item)
        deadline = _clean(item.get("deadline") or item.get("registration_end_time"))
        start_time = _clean(item.get("registration_start_time"))
        conditions = _clean(item.get("conditions") or item.get("target_audience"))
        bonus = _clean(item.get("bonus_summary"))
        note = _clean(item.get("special_bonus_note"))
        link = _clean(item.get("official_link") or item.get("latest_notice_link"))
        status = _clean(item.get("status") or "待官网更新")
        strategy = _category_strategy(category)
        desc = _clean(item.get("desc") or item.get("description"))

        question = f"{name}什么时候报名 报名截止时间 赛程安排"
        answer = (
            f"{name}当前状态为{status}。"
            f"报名开始：{start_time or '未提取到明确开始时间'}；"
            f"报名截止/关键时间：{deadline or '未提取到明确截止时间，需以官网通知为准'}。"
            f"官网入口：{link or '暂无官网链接'}。"
        )
        docs.append(
            (
                f"{item['id']}:qa:deadline",
                f"问题：{question}\n回答：{answer}\n相关词：报名 截止 时间 日程 赛程 提醒 官网 通知 {name} {category}",
                _instruction_metadata(item, "deadline", question),
            )
        )

        question = f"{name}报名条件 参赛资格 适合哪些学生"
        answer = (
            f"{name}的参赛条件/适合对象："
            f"{conditions if _has_specific_value(conditions) else '当前未提取到明确条件，建议以官网当年通知为准'}。"
            f"{strategy}"
        )
        docs.append(
            (
                f"{item['id']}:qa:condition",
                f"问题：{question}\n回答：{answer}\n相关词：条件 资格 对象 年级 学院 专业 校区 门槛 {name} {category}",
                _instruction_metadata(item, "condition", question),
            )
        )

        if _has_specific_value(bonus) or item.get("is_hit_recognized"):
            question = f"{name}加分 学分绩 综测 推免认定"
            answer = (
                f"{name}的校内加分/认定信息："
                f"{bonus if _has_specific_value(bonus) else '学生手册未给出单独摘要，按学校和学院当年认定为准'}。"
                f"{note if note and note not in bonus else ''}"
            )
            docs.append(
                (
                    f"{item['id']}:qa:bonus",
                    f"问题：{question}\n回答：{answer}\n相关词：加分 学分绩 综测 保研 推免 奖项 证书 {name} {category}",
                    _instruction_metadata(item, "bonus", question),
                )
            )

        question = f"{name}官网链接 通知入口 报名网址"
        answer = f"{name}的官网/通知入口：{link or '暂无官网链接'}。如官网年份更新，报名、赛程和规则以最新通知为准。"
        docs.append(
            (
                f"{item['id']}:qa:official",
                f"问题：{question}\n回答：{answer}\n相关词：官网 链接 网址 通知 报名入口 规则 章程 {name} {category}",
                _instruction_metadata(item, "official", question),
            )
        )

        question = f"参加{name}怎么找队友 怎么写申请 怎么分工"
        answer = (
            f"参加{name}组队时建议先确认目标赛道、缺口角色、每周投入时间和交付物。"
            f"{strategy}申请说明可以写：可承担角色、相关课程/项目/竞赛经历、每周可投入时间、希望加入该队伍的原因。"
        )
        docs.append(
            (
                f"{item['id']}:qa:team",
                f"问题：{question}\n回答：{answer}\n相关词：队友 组队 招募 申请 匹配 角色 分工 门槛 {name} {category}",
                _instruction_metadata(item, "team_match", question),
            )
        )

        if desc:
            question = f"{name}是什么 有什么特点 备赛重点"
            answer = f"{name}简介：{desc[:240]}。备赛重点：{strategy}"
            docs.append(
                (
                    f"{item['id']}:qa:intro",
                    f"问题：{question}\n回答：{answer}\n相关词：介绍 特色 方向 备赛 规划 推荐 {name} {category}",
                    _instruction_metadata(item, "general", question),
                )
            )

    for category, items in categories.items():
        names = "、".join(_clean(item.get("name")) for item in items[:10] if item.get("name"))
        strategy = _category_strategy(category)
        meta = {
            "doc_type": "guide",
            "id": f"guide:{category}",
            "name": f"{category}竞赛规划指南",
            "title": f"{category}竞赛规划指南",
            "category": category,
            "status": "",
            "deadline": "",
            "conditions": "",
            "bonus_summary": "",
            "special_bonus_note": "",
            "official_link": "",
            "latest_notice_link": "",
            "source_name": "竞赛库自动生成规划样本",
            "source_type": "generated_guide",
            "is_hit_recognized": False,
            "keywords": [category, "规划", "推荐", "组队", "材料", "备赛"],
            "desc": strategy,
            "training_kind": "generated_guide",
        }
        docs.append(
            (
                f"guide:{category}",
                (
                    f"问题：{category}方向有哪些竞赛适合推荐，应该如何规划和组队？\n"
                    f"回答：{category}方向可优先关注：{names or '竞赛库中同类赛事'}。{strategy}"
                    "建议先选一个主赛道，再根据报名截止时间、参赛条件、队友缺口、加分认定和材料要求排序。"
                    "\n相关词：推荐 生涯规划 竞赛路线 近期比赛 热门比赛 组队 材料 导师"
                ),
                meta,
            )
        )
    return docs


def _add_doc(
    docs: list[dict[str, Any]],
    dfs: Counter[str],
    doc_id: str,
    text: str,
    metadata: dict[str, Any],
) -> None:
    tokens = tokenize(text)
    if not tokens:
        return
    term_counts = Counter(tokens)
    dfs.update(term_counts.keys())
    docs.append(
        {
            "id": doc_id,
            "terms": dict(term_counts),
            "length": sum(term_counts.values()),
            "metadata": metadata,
        }
    )


def train_self_model(
    contests: list[dict[str, Any]],
    path: Path = MODEL_FILE,
    collect_web: bool = False,
) -> dict[str, Any]:
    corpus = collect_training_corpus() if collect_web else load_training_corpus()
    knowledge = build_contest_knowledge(contests, corpus)
    contests = attach_knowledge(contests, knowledge)
    docs = []
    dfs: Counter[str] = Counter()
    for item in contests:
        if not item.get("id") or not item.get("name"):
            continue
        text = _contest_text(item)
        _add_doc(docs, dfs, str(item.get("id")), text, _metadata(item))

    for item in corpus.get("docs", []):
        if not item.get("id") or not item.get("text"):
            continue
        _add_doc(docs, dfs, str(item.get("id")), _web_text(item), _web_metadata(item))

    for doc_id, text, metadata in _instruction_docs(contests):
        _add_doc(docs, dfs, doc_id, text, metadata)

    for doc_id, text, metadata in knowledge_training_docs(knowledge):
        _add_doc(docs, dfs, doc_id, text, metadata)

    for doc_id, text, metadata in matching_template_training_docs():
        _add_doc(docs, dfs, doc_id, text, metadata)

    generated_docs, generated_payload = generated_training_docs(contests)
    for doc_id, text, metadata in generated_docs:
        _add_doc(docs, dfs, doc_id, text, metadata)

    total = max(1, len(docs))
    idf = {term: round(math.log((total + 1) / (df + 1)) + 1, 6) for term, df in dfs.items()}
    avg_doc_length = round(sum(doc.get("length", 0) for doc in docs) / total, 3)
    payload = {
        "model": MODEL_NAME,
        "label": MODEL_LABEL,
        "version": MODEL_VERSION,
        "algorithm": "从零训练的竞赛领域 RAG 检索排序模型（竞赛库 + 官网/政策/GitHub/数据集平台语料 + 含金量知识库 + 匹配扩写模板 + BM25/TF-IDF混合排序）",
        "trained_at": _now_text(),
        "source_hash": _source_hash(contests, corpus),
        "contest_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "contest"]),
        "web_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "web"]),
        "instruction_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "instruction"]),
        "guide_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "guide"]),
        "knowledge_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "knowledge"]),
        "matching_template_docs_count": len([doc for doc in docs if doc.get("metadata", {}).get("doc_type") == "matching_template"]),
        "synthetic_docs_count": len(
            [
                doc
                for doc in docs
                if str(doc.get("metadata", {}).get("doc_type", "")).startswith("synthetic_")
            ]
        ),
        "synthetic_breakdown": generated_payload.get("counts", {}),
        "knowledge_updated_at": knowledge.get("updated_at", ""),
        "web_corpus_updated_at": corpus.get("updated_at", ""),
        "training_sources_count": corpus.get("sources_count", 0),
        "docs_count": len(docs),
        "vocab_size": len(idf),
        "avg_doc_length": avg_doc_length,
        "docs": docs,
        "idf": idf,
        "notes": "该模型不使用外部预训练权重，训练数据来自本项目竞赛库、学生手册加分信息、公开官网/高校通知/政策页面/GitHub和数据集平台资料、竞赛含金量知识库，以及由竞赛字段和匹配页模板自动生成的本地问答样本。",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def load_self_model(path: Path = MODEL_FILE) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def ensure_self_model(contests: list[dict[str, Any]], force: bool = False, collect_web: bool = False) -> dict[str, Any]:
    corpus = load_training_corpus()
    current_hash = _source_hash(attach_knowledge(contests), corpus)
    model = load_self_model()
    if force or not model or model.get("source_hash") != current_hash:
        return train_self_model(contests, collect_web=collect_web)
    return model


def self_model_status(contests: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    model = load_self_model()
    corpus = load_training_corpus()
    source_hash = _source_hash(attach_knowledge(contests), corpus) if contests is not None else ""
    stale = bool(model and source_hash and model.get("source_hash") != source_hash)
    return {
        "available": bool(model),
        "label": MODEL_LABEL,
        "model": MODEL_NAME,
        "version": MODEL_VERSION,
        "algorithm": model.get("algorithm") if model else "从零训练的竞赛领域 TF-IDF 检索排序模型",
        "trained_at": model.get("trained_at", "") if model else "",
        "docs_count": model.get("docs_count", 0) if model else 0,
        "contest_docs_count": model.get("contest_docs_count", 0) if model else 0,
        "web_docs_count": model.get("web_docs_count", 0) if model else 0,
        "instruction_docs_count": model.get("instruction_docs_count", 0) if model else 0,
        "guide_docs_count": model.get("guide_docs_count", 0) if model else 0,
        "knowledge_docs_count": model.get("knowledge_docs_count", 0) if model else 0,
        "matching_template_docs_count": model.get("matching_template_docs_count", 0) if model else 0,
        "synthetic_docs_count": model.get("synthetic_docs_count", 0) if model else 0,
        "synthetic_breakdown": model.get("synthetic_breakdown", {}) if model else {},
        "knowledge_updated_at": model.get("knowledge_updated_at", "") if model else "",
        "training_sources_count": model.get("training_sources_count", 0) if model else 0,
        "vocab_size": model.get("vocab_size", 0) if model else 0,
        "web_corpus_updated_at": model.get("web_corpus_updated_at", "") if model else "",
        "stale": stale,
        "path": str(MODEL_FILE),
    }


def _intent(question: str) -> str:
    if any(word in question for word in INTENT_KEYWORDS["recommend"]):
        return "recommend"
    for intent, words in INTENT_KEYWORDS.items():
        if intent == "recommend":
            continue
        if any(word in question for word in words):
            return intent
    return "general"


def _profile_terms(profile: dict[str, Any] | None) -> list[str]:
    profile = profile or {}
    terms = [
        profile.get("campus"),
        profile.get("college"),
        profile.get("major"),
        profile.get("grade"),
        profile.get("target"),
    ]
    if isinstance(profile.get("interests"), list):
        terms.extend(profile.get("interests"))
    return [_clean(item) for item in terms if _clean(item)]


def _query_vector(question: str, profile: dict[str, Any] | None, model: dict[str, Any]) -> dict[str, float]:
    terms = tokenize(question + " " + " ".join(_profile_terms(profile)))
    counts = Counter(terms)
    idf = model.get("idf", {})
    return {term: count * float(idf.get(term, 1.0)) for term, count in counts.items()}


def _query_counts(question: str, profile: dict[str, Any] | None) -> Counter[str]:
    return Counter(tokenize(question + " " + " ".join(_profile_terms(profile))))


def _cosine(query: dict[str, float], terms: dict[str, int], idf: dict[str, float]) -> float:
    if not query or not terms:
        return 0.0
    dot = 0.0
    doc_norm = 0.0
    for term, count in terms.items():
        weight = float(count) * float(idf.get(term, 1.0))
        doc_norm += weight * weight
        if term in query:
            dot += query[term] * weight
    query_norm = sum(weight * weight for weight in query.values())
    if not query_norm or not doc_norm:
        return 0.0
    return dot / math.sqrt(query_norm * doc_norm)


def _bm25(query_counts: Counter[str], terms: dict[str, int], idf: dict[str, float], doc_len: int, avg_len: float) -> float:
    if not query_counts or not terms:
        return 0.0
    k1 = 1.35
    b = 0.72
    avg_len = avg_len or 1.0
    score = 0.0
    for term, query_count in query_counts.items():
        freq = int(terms.get(term, 0))
        if not freq:
            continue
        denom = freq + k1 * (1 - b + b * (max(1, doc_len) / avg_len))
        score += float(idf.get(term, 1.0)) * ((freq * (k1 + 1)) / denom) * min(2, query_count)
    return score


def _rank(question: str, profile: dict[str, Any] | None, model: dict[str, Any]) -> list[dict[str, Any]]:
    query = _query_vector(question, profile, model)
    query_counts = _query_counts(question, profile)
    idf = model.get("idf", {})
    avg_len = float(model.get("avg_doc_length") or 1.0)
    ranked = []
    lower_question = question.lower()
    for doc in model.get("docs", []):
        meta = doc.get("metadata", {})
        terms = doc.get("terms", {})
        cosine_score = _cosine(query, terms, idf)
        bm25_score = _bm25(query_counts, terms, idf, int(doc.get("length") or 0), avg_len)
        score = cosine_score + min(0.28, bm25_score / 35)
        name = str(meta.get("name", "")).lower()
        if name and (name in lower_question or lower_question in name):
            score += 0.45
        for keyword in meta.get("keywords", []):
            if keyword and str(keyword).lower() in lower_question:
                score += 0.08
        if meta.get("is_hit_recognized"):
            score += 0.03
        if meta.get("status") == "报名中":
            score += 0.03
        if meta.get("doc_type") == "instruction":
            score += 0.025
        if meta.get("doc_type") == "knowledge" and any(word in question for word in INTENT_KEYWORDS["prestige"]):
            score += 0.16
        if meta.get("prestige_score") and any(word in question for word in ["含金量", "推荐", "高价值", "保研", "就业"]):
            score += min(0.08, float(meta.get("prestige_score") or 0) / 1000)
        ranked.append({"score": score, "metadata": meta})
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked


def _line_for_contest(meta: dict[str, Any], index: int) -> str:
    deadline = meta.get("deadline") or "以官网通知为准"
    conditions = meta.get("conditions") or "参赛条件以官网通知为准"
    bonus = meta.get("bonus_summary") or "校内加分以学生手册和学院认定为准"
    link = meta.get("official_link") or "暂无官网链接"
    prestige = ""
    if meta.get("prestige_score"):
        prestige = f"\n   含金量：{meta.get('prestige_score')}分 / {meta.get('prestige_grade') or '待评估'}级 / {meta.get('competition_level') or '级别待确认'}"
    return (
        f"{index}. {meta.get('name')}（{meta.get('category')}，{meta.get('status')}）\n"
        f"   报名/截止：{deadline}\n"
        f"   条件：{conditions[:90]}\n"
        f"   加分：{bonus[:90]}\n"
        f"   官网：{link}"
        f"{prestige}"
    )


def _specific_answer(intent: str, meta: dict[str, Any]) -> str:
    name = meta.get("name")
    deadline = meta.get("deadline") or meta.get("registration_end_time") or "以官网通知为准"
    link = meta.get("official_link") or meta.get("latest_notice_link") or "暂无官网链接"
    if intent == "deadline":
        return f"{name} 当前记录的报名截止/关键时间是：{deadline}。具体赛程可能按年份调整，建议以官网通知为准：{link}"
    if intent == "condition":
        return f"{name} 的参赛条件/适合对象：{meta.get('conditions') or '当前未提取到明确条件，建议以官网通知为准'}。官网：{link}"
    if intent == "bonus":
        bonus = meta.get("bonus_summary") or "学生手册未给出单独摘要，按学校和学院当年认定为准"
        note = meta.get("special_bonus_note") or ""
        extra = f"。{note}" if note and note not in bonus else ""
        return (
            f"{name} 的校内加分信息：{bonus}{extra}"
        )
    if intent == "official":
        return f"{name} 的官网/通知入口：{link}"
    if intent == "prestige":
        organizers = "、".join(meta.get("organizers") or []) or "待官网确认"
        listed = "已匹配高校竞赛榜单线索" if meta.get("ranking_included") else "暂未匹配到高校竞赛榜单线索"
        score = meta.get("prestige_score") or "待评估"
        grade = meta.get("prestige_grade") or "待评估"
        level = meta.get("competition_level") or meta.get("level") or "级别待确认"
        return (
            f"{name} 的含金量评估：{score}分，{grade}级，竞赛级别为{level}。"
            f"主办/指导单位：{organizers}；{listed}；"
            f"{'已纳入哈工大校内认定。' if meta.get('is_hit_recognized') else '校内认定待确认。'}"
            "评分来自本地知识库对主办单位权威性、榜单收录、学校认定、参赛规模、获奖难度、行业认可、成果转化和风险控制等维度的综合计算。"
        )
    return (
        f"{name} 属于{meta.get('category')}类竞赛，当前状态为{meta.get('status')}，"
        f"报名截止：{deadline}。{meta.get('desc', '')[:120]}\n官网：{link}"
    )


def _asked_field_intents(question: str) -> list[str]:
    fields: list[str] = []
    for intent in ["deadline", "condition", "bonus", "official", "prestige"]:
        if any(word in question for word in INTENT_KEYWORDS[intent]):
            fields.append(intent)
    return fields


def _multi_field_answer(meta: dict[str, Any], question: str) -> str:
    name = meta.get("name")
    link = meta.get("official_link") or meta.get("latest_notice_link") or "暂无官网链接"
    fields = _asked_field_intents(question)
    if not fields:
        fields = ["deadline", "condition", "official"]
    def sentence(text: str) -> str:
        text = _clean(text)
        return text if text.endswith(("。", "！", "？", ".", "!", "?")) else f"{text}。"

    lines = [f"{name} 的关键信息如下："]
    if "deadline" in fields:
        deadline = meta.get("deadline") or meta.get("registration_end_time") or "以官网通知为准"
        start_time = meta.get("registration_start_time") or ""
        if start_time:
            lines.append(f"1. 报名时间：{start_time} 至 {deadline}。")
        else:
            lines.append(f"1. 报名/截止：{deadline}。")
    if "condition" in fields:
        lines.append(f"2. 报名条件：{sentence(meta.get('conditions') or '当前未提取到明确条件，建议以官网通知为准')}")
    if "bonus" in fields:
        bonus = meta.get("bonus_summary") or "学生手册未给出单独摘要，按学校和学院当年认定为准"
        note = meta.get("special_bonus_note") or ""
        text = sentence(bonus)
        if note and note not in bonus:
            text += sentence(note)
        lines.append(f"3. 加分/认定：{text}")
    if "official" in fields or any(word in question for word in ["哪里", "入口", "网址", "链接"]):
        lines.append(f"4. 官网/通知入口：{link}")
    if "prestige" in fields:
        lines.append(
            f"5. 含金量：{meta.get('prestige_score') or '待评估'}分 / {meta.get('prestige_grade') or '待评估'}级 / {meta.get('competition_level') or '级别待确认'}。"
        )
    if link and link != "暂无官网链接":
        lines.append("具体赛程、组别、材料格式和资格要求每年可能调整，最终以官网最新通知为准。")
    return "\n".join(lines)


def _profile_summary(profile: dict[str, Any] | None) -> str:
    terms = _profile_terms(profile)
    return "、".join(terms[:5]) if terms else "当前资料尚不完整"


def _contest_items(ranked: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    items = []
    seen: set[str] = set()
    for item in ranked:
        meta = item.get("metadata", {})
        if meta.get("doc_type") not in {"contest", "instruction"}:
            continue
        key = str(meta.get("id") or meta.get("name") or "")
        if key in seen:
            continue
        seen.add(key)
        items.append(item)
        if len(items) >= limit:
            break
    return items


def _web_items(ranked: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    items = [item for item in ranked if item.get("metadata", {}).get("doc_type") == "web"]
    return items[:limit]


def _career_answer(profile: dict[str, Any] | None, contests: list[dict[str, Any]], web_docs: list[dict[str, Any]]) -> str:
    profile = profile or {}
    grade = str(profile.get("grade", ""))
    stage = "先明确主赛道，再用一个作品沉淀可证明成果"
    if grade in {"大一", "大二"}:
        stage = "打基础、试错和形成第一个可展示项目"
    elif grade in {"大三", "研一"}:
        stage = "围绕保研/就业目标冲高价值成果"
    elif grade in {"大四", "研二", "研三", "博士"}:
        stage = "成果收口、证明材料归档和简历表达"
    lines = [
        f"基于自训练模型对你的画像（{_profile_summary(profile)}）和公开竞赛资料的匹配，建议目标定为：{stage}。",
        "",
        "1. 第1-2周：确定1个主赛道和1个备选赛道，先核对报名截止、参赛资格、组队人数、材料格式和校内备案。",
        "2. 第3-6周：围绕主赛道完成最小作品闭环，至少留下代码/实验记录/调研文档/PPT/视频中的两类证据。",
        "3. 第7-10周：用官网规则反查作品短板，补齐创新点、数据来源、测试结果、分工说明和答辩脚本。",
        "4. 第11-12周：提交前做风险检查，重点看原创性、材料命名、队伍信息、指导教师、学院认定和证书留存。",
    ]
    if contests:
        lines.append("")
        lines.append("可优先绑定的竞赛：")
        lines.extend(_line_for_contest(item["metadata"], index) for index, item in enumerate(contests[:3], start=1))
    if web_docs:
        lines.append("")
        lines.append("训练语料提示：竞赛官网/高校通知通常把“报名通知、参赛资格、作品提交、评审规则”拆在不同页面，备赛时要逐项核对。")
    return "\n".join(lines)


def _team_answer(profile: dict[str, Any] | None, contests: list[dict[str, Any]], context: dict[str, Any] | None) -> str:
    posts = (context or {}).get("posts", [])[:4]
    lines = [
        "自训练模型建议把组队判断拆成四步：目标竞赛是否一致、岗位缺口是否明确、每周投入是否匹配、申请说明是否能证明能力。",
        f"你的画像：{_profile_summary(profile)}",
    ]
    if contests:
        lines.append("")
        lines.append("适合作为组队目标的竞赛：")
        lines.extend(_line_for_contest(item["metadata"], index) for index, item in enumerate(contests[:3], start=1))
    if posts:
        lines.append("")
        lines.append("当前招募大厅可优先查看：")
        for index, post in enumerate(posts, start=1):
            lines.append(
                f"{index}. {post.get('title')} / {post.get('contest_name') or '未填竞赛'}，"
                f"剩余{post.get('remaining', 0)}人，适配度{post.get('match_score', '待计算')}"
            )
    lines.append("")
    lines.append("申请说明模板：我能承担的角色 + 相关经历/课程/项目 + 每周可投入时间 + 希望加入该队伍的原因。")
    return "\n".join(lines)


def _material_answer(profile: dict[str, Any] | None, contests: list[dict[str, Any]], web_docs: list[dict[str, Any]]) -> str:
    lines = [
        "自训练模型按官网/高校通知中的高频要求，建议材料按下面结构准备：",
        "1. 参赛资格：学院、年级、学籍、队伍人数、指导教师是否符合通知。",
        "2. 作品主体：问题背景、方案路线、创新点、实现过程、测试/实验结果。",
        "3. 证明材料：报名表、作品说明、代码/数据、演示视频、PPT、分工表、校内备案。",
        "4. 风险检查：原创性、数据来源、格式命名、提交时间、官网账号和联系方式。",
    ]
    if contests:
        lines.append("")
        lines.append("结合当前问题最相关竞赛：")
        for item in contests[:2]:
            meta = item["metadata"]
            lines.append(f"- {meta.get('name')}：先核对 {meta.get('official_link') or '官网通知'}；条件：{meta.get('conditions') or '以官网为准'}")
    if web_docs:
        lines.append("")
        lines.append("训练语料显示：高校通知常把校内报名、选拔、集训和最终官网报名分开，提交前要同时核对校内通知和赛事官网。")
    return "\n".join(lines)


def _mentor_answer(profile: dict[str, Any] | None, context: dict[str, Any] | None) -> str:
    mentors = (context or {}).get("mentors", [])[:5]
    lines = [
        "导师匹配建议不要只看职称，优先看研究方向能否支撑竞赛作品、课题组是否有设备/数据/工程经验、联系方式是否公开。",
        f"你的画像：{_profile_summary(profile)}",
    ]
    if mentors:
        lines.append("")
        lines.append("当前导师库匹配结果：")
        for index, mentor in enumerate(mentors, start=1):
            contact = mentor.get("contact_email") or mentor.get("contact_phone") or "官方页未公开"
            lines.append(
                f"{index}. {mentor.get('name')}（{mentor.get('campus')} / {mentor.get('college')}）"
                f"：{mentor.get('direction') or '方向待确认'}；联系：{contact}"
            )
    lines.append("")
    lines.append("联系导师前准备：一句话目标竞赛、已有基础、希望导师帮助的问题、时间投入和目前队伍分工。")
    return "\n".join(lines)


def _synthesis_answer(
    intent: str,
    question: str,
    profile: dict[str, Any] | None,
    contest_hits: list[dict[str, Any]],
    web_hits: list[dict[str, Any]],
    context: dict[str, Any] | None,
) -> str:
    if intent == "career_plan":
        return _career_answer(profile, contest_hits, web_hits)
    if intent == "team_match":
        return _team_answer(profile, contest_hits, context)
    if intent == "material":
        return _material_answer(profile, contest_hits, web_hits)
    if intent == "mentor":
        return _mentor_answer(profile, context)
    if intent == "prestige":
        picked = sorted(
            contest_hits[:6],
            key=lambda item: (
                -(float(item.get("score", 0)) * 0.8 + float(item["metadata"].get("prestige_score") or 0) / 100 * 0.5),
            ),
        )[:4]
        if not picked:
            return "暂时没有找到足够的含金量知识库证据。可以先刷新竞赛知识库，再查看主办单位、榜单收录和参赛规模。"
        lines = ["根据竞赛知识库的主办单位、榜单收录、学校认定、规模和获奖难度，当前可参考："]
        lines.extend(_line_for_contest(item["metadata"], index) for index, item in enumerate(picked, start=1))
        lines.append("评分是辅助排序，不等同于官方结论；最终仍应结合专业相关性、时间成本和个人目标判断。")
        return "\n".join(lines)
    if intent == "recommend":
        picked = contest_hits[:4]
        lines = [f"根据增强自训练模型对“{_profile_summary(profile)}”和官网语料的匹配，优先推荐："]
        lines.extend(_line_for_contest(item["metadata"], index) for index, item in enumerate(picked, start=1))
        lines.append("建议先选择1个主赛道加入“我的竞赛”，再去匹配页找队友或发布招募。")
        return "\n".join(lines)
    picked = contest_hits[:3]
    if picked:
        lines = ["我从自训练模型中找到这些相关竞赛/资料："]
        lines.extend(_line_for_contest(item["metadata"], index) for index, item in enumerate(picked, start=1))
    else:
        lines = ["我从网上训练语料中找到相关资料，但还没有匹配到具体竞赛。"]
    if web_hits:
        lines.append("")
        lines.append("可参考的训练语料来源：")
        for index, item in enumerate(web_hits[:3], start=1):
            meta = item["metadata"]
            lines.append(f"{index}. {meta.get('title') or meta.get('name')}：{meta.get('official_link')}")
    return "\n".join(lines)


def answer_with_self_model(
    question: str,
    profile: dict[str, Any] | None,
    contests: list[dict[str, Any]],
    intent: str | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    model = ensure_self_model(contests)
    intent = intent or _intent(question)
    if intent == "contest_recommend":
        intent = "recommend"
    if intent == "contest_detail":
        intent = "general"
    if intent not in {
        "deadline",
        "condition",
        "bonus",
        "official",
        "recommend",
        "general",
        "career_plan",
        "team_match",
        "material",
        "mentor",
        "prestige",
    }:
        return None
    ranked = _rank(question, profile, model)
    top = [item for item in ranked if item["score"] > 0.035][:5]
    contest_hits = _contest_items(ranked, limit=5)
    web_hits = _web_items(ranked, limit=4)
    if not top and intent not in {"team_match", "mentor", "material", "career_plan"}:
        return None

    if intent in {"deadline", "condition", "bonus", "official", "general", "prestige"} and contest_hits and contest_hits[0]["score"] >= 0.09:
        if len(_asked_field_intents(question)) >= 2:
            answer = _multi_field_answer(contest_hits[0]["metadata"], question)
        else:
            answer = _specific_answer(intent, contest_hits[0]["metadata"])
        picked = [contest_hits[0]]
    else:
        picked = (contest_hits[:3] or top[:3])
        answer = _synthesis_answer(intent, question, profile, contest_hits, web_hits, context)

    sources = []
    source_items = picked[:3] + web_hits[:2]
    for item in source_items:
        meta = item["metadata"]
        is_contest_source = meta.get("doc_type") in {"contest", "instruction", "knowledge"}
        sources.append(
            {
                "type": "contest" if is_contest_source else "web",
                "title": meta.get("name") or meta.get("title") or "训练资料",
                "subtitle": f"{meta.get('status', '')} / 截止 {meta.get('deadline') or '待确认'}",
                "url": meta.get("official_link") or meta.get("latest_notice_link") or "",
            }
        )
    base_scores = picked or top or web_hits
    confidence = round(min(0.99, max((item["score"] for item in base_scores), default=0.12)), 3)
    if intent in {"team_match", "mentor", "material", "career_plan"}:
        confidence = max(confidence, 0.18)
    return {
        "answer": answer,
        "confidence": confidence,
        "sources": sources,
        "model": MODEL_NAME,
        "provider": MODEL_LABEL,
        "mode": "self_trained",
        "status": self_model_status(contests),
        "debug_top": [deepcopy(item["metadata"].get("name")) for item in picked],
    }
