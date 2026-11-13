from __future__ import annotations

import hashlib
import json
import os
import re
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import urlopen

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ai_agent import answer_question
from contest_knowledge import attach_knowledge, build_contest_knowledge, load_knowledge_base
from contest_crawler import get_contests as crawl_contests
from contest_crawler import load_cached_or_fallback
from contest_metrics import get_contest_sections, record_click
from hit_directory import crawl_hit_mentors, get_hit_options, mentor_filter_options, search_hit_mentors
from llm_config import get_llm_client, public_llm_status, save_deepseek_config
from match_engine import MATCH_MENTORS, MATCH_TEAMS, build_match_payload, find_match_item
from news_feed import build_home_dashboard, get_home_news
from recruitment_store import (
    apply_to_post,
    complain_member,
    create_post,
    decide_application,
    get_user_recruitment,
    get_post_detail,
    list_posts,
    polish_recruitment,
    request_unbind,
)
from self_trained_model import ensure_self_model, self_model_status
from user_store import (
    add_my_contest as store_add_my_contest,
    add_my_match as store_add_my_match,
    get_my_contests as store_get_my_contests,
    get_my_matches as store_get_my_matches,
    remove_my_contest as store_remove_my_contest,
    remove_my_match as store_remove_my_match,
)
from web_training_corpus import load_training_corpus


app = FastAPI(title="鏅虹珵宸ュぇ绔炶禌骞冲彴鍚庣")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEAM_MATCHES = MATCH_TEAMS
MENTOR_MATCHES = MATCH_MENTORS

class AskRequest(BaseModel):
    question: str
    profile: dict[str, Any] = {}
    history: list[dict[str, Any]] = []


class WechatLoginRequest(BaseModel):
    code: str


class ItemAddRequest(BaseModel):
    item_id: str | int


class MatchAddRequest(BaseModel):
    item_id: int
    item_type: str


class GenericPayload(BaseModel):
    data: dict[str, Any] = {}


class DeepSeekConfigRequest(BaseModel):
    api_key: str = ""
    model: str = "deepseek-v4-flash"
    base_url: str = "https://api.deepseek.com"


def normalize_id(value: str | int) -> str:
    return str(value)


SCHOOL_RECOGNITION_LABELS = {"校内认定", "哈工大认定", "学校认定", "鏍″唴璁ゅ畾"}

PROFILE_CATEGORY_HINTS = [
    (["计算机", "软件", "网络", "人工智能", "智能", "数据科学", "大数据"], ["编程", "AI", "数学建模", "创新创业"]),
    (["电子", "通信", "集成电路", "微电子", "自动化", "控制"], ["电子", "机器人", "AI", "编程"]),
    (["机械", "车辆", "能源", "电气", "航天", "航空"], ["机械", "机器人", "电子", "创新创业"]),
    (["材料", "化学", "环境", "生命", "生物", "海洋"], ["材料", "创新创业", "数学建模", "海洋工程"]),
    (["经济", "管理", "工商", "会计", "金融"], ["商业分析", "创新创业", "数学建模"]),
    (["外语", "英语", "日语", "翻译"], ["外语"]),
    (["建筑", "设计", "艺术", "传媒"], ["设计", "创新创业"]),
    (["交通", "土木", "建筑环境"], ["交通", "机械", "数学建模"]),
]


def _split_terms(value: Any) -> list[str]:
    if isinstance(value, list):
        raw = " ".join(str(item) for item in value)
    else:
        raw = str(value or "")
    return [part.strip() for part in re.split(r"[，,、/；;\s|]+", raw) if part.strip()]


def _contest_search_text(item: dict[str, Any]) -> str:
    parts = [
        item.get("name", ""),
        item.get("category", ""),
        item.get("status", ""),
        item.get("desc", ""),
        item.get("description", ""),
        item.get("conditions", ""),
        item.get("target_audience", ""),
        item.get("bonus_summary", ""),
        item.get("competition_level", ""),
        item.get("tag", ""),
        (item.get("prestige") or {}).get("summary", ""),
        " ".join(str(word) for word in item.get("organizers", []) or []),
        " ".join(str(word) for word in item.get("keywords", []) or []),
    ]
    return " ".join(str(part) for part in parts if part).lower()


def is_school_recognized(item: dict[str, Any]) -> bool:
    if item.get("is_hit_recognized"):
        return True
    text = _contest_search_text(item)
    return any(label.lower() in text for label in SCHOOL_RECOGNITION_LABELS)


def _profile_has_signal(profile: dict[str, Any]) -> bool:
    return any(
        str(profile.get(key, "")).strip()
        for key in ["campus", "college", "major", "grade", "target", "interests", "competition", "project", "gpa"]
    )


def _profile_text(profile: dict[str, Any]) -> str:
    values = [
        profile.get("campus", ""),
        profile.get("college", ""),
        profile.get("major", ""),
        profile.get("grade", ""),
        profile.get("target", ""),
        profile.get("interests", ""),
        profile.get("competition", ""),
        profile.get("project", ""),
    ]
    return " ".join(str(value) for value in values if value)


def _profile_category_hints(profile: dict[str, Any]) -> set[str]:
    text = _profile_text(profile)
    hints: set[str] = set()
    for keys, categories in PROFILE_CATEGORY_HINTS:
        if any(key in text for key in keys):
            hints.update(categories)
    for term in _split_terms(profile.get("interests", "")) + _split_terms(profile.get("target", "")):
        if term in {"AI", "编程", "数学建模", "电子", "机器人", "创新创业", "机械", "材料", "外语", "设计", "交通", "海洋工程"}:
            hints.add(term)
        if term == "软件开发":
            hints.update(["编程", "AI"])
        if term == "电子设计":
            hints.add("电子")
        if term in {"商业分析", "产品设计", "科研训练"}:
            hints.update(["创新创业", "数学建模"])
    return hints


def contest_profile_score(item: dict[str, Any], profile: dict[str, Any]) -> tuple[int, str]:
    if not _profile_has_signal(profile):
        return 0, ""

    text = _contest_search_text(item)
    category = str(item.get("category", ""))
    score = 8
    reasons: list[str] = []

    ignored_terms = {"竞赛", "比赛", "项目", "加分", "保研", "推免", "就业", "简历", "奖学金", "综测"}
    terms = []
    for key in ["major", "college", "competition", "project"]:
        terms.extend(_split_terms(profile.get(key, "")))
    terms.extend(_split_terms(profile.get("interests", "")))
    hits = []
    for term in dict.fromkeys(term for term in terms if len(term) >= 2):
        if term not in ignored_terms and term.lower() in text:
            hits.append(term)
    if hits:
        add = min(24, len(hits) * 5)
        score += add
        reasons.append(f"资料关键词命中：{'、'.join(hits[:4])}")

    hints = _profile_category_hints(profile)
    exact_category_hits = [hint for hint in hints if hint == category]
    related_category_hits = [hint for hint in hints if hint != category and hint.lower() in text]
    if exact_category_hits:
        score += 28
        reasons.append(f"方向匹配：{'、'.join(exact_category_hits[:3])}")
    elif related_category_hits:
        score += min(12, len(related_category_hits) * 4)
        reasons.append(f"相关方向：{'、'.join(related_category_hits[:3])}")

    target_text = str(profile.get("target", ""))
    bonus_text = str(item.get("bonus_summary", ""))
    if any(word in target_text for word in ["保研", "推免", "综测", "加分", "奖学金"]):
        if is_school_recognized(item):
            score += 12
            reasons.append("符合校内认定/加分导向")
        elif bonus_text:
            score += 5
            reasons.append("含有加分信息")
    if any(word in target_text for word in ["就业", "简历", "实习", "项目"]):
        if category in {"编程", "AI", "电子", "机器人", "创新创业", "商业分析"} or any(word in text for word in ["企业", "行业", "工程", "项目"]):
            score += 6
            reasons.append("对项目经历和简历展示有帮助")
    if any(word in target_text for word in ["科研", "论文", "实验"]):
        if category in {"数学建模", "AI", "材料", "电子"} or any(word in text for word in ["论文", "实验", "模型", "研究"]):
            score += 5
            reasons.append("与科研训练目标相关")

    status_text = str(item.get("status", "")) + " " + str(item.get("deadline", ""))
    if any(word in status_text for word in ["报名", "进行", "截止", "待官网"]):
        score += 3
    if is_school_recognized(item):
        score += 4

    try:
        score += min(7, int(float(item.get("prestige_score") or 0) // 12))
    except (TypeError, ValueError):
        pass

    reason = "；".join(reasons[:3]) or "按专业、兴趣与目标综合排序"
    return max(0, min(100, int(score))), reason


def sort_contests_for_profile(contests: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    if not _profile_has_signal(profile):
        return contests
    ranked = []
    for index, item in enumerate(contests):
        score, reason = contest_profile_score(item, profile)
        copied = dict(item)
        copied["profile_match_score"] = score
        copied["profile_match_reason"] = reason
        try:
            prestige = float(copied.get("prestige_score") or 0)
        except (TypeError, ValueError):
            prestige = 0
        ranked.append((score, prestige, -index, copied))
    ranked.sort(key=lambda value: (value[0], value[1], value[2]), reverse=True)
    return [item for _, _, _, item in ranked]


def filter_contests(
    contests: list[dict[str, Any]],
    keyword: str = "",
    category: str = "鍏ㄩ儴",
) -> list[dict[str, Any]]:
    keyword = keyword.strip().lower()
    category = category.strip()
    result = []
    for item in contests:
        if category and category not in {"鍏ㄩ儴", "全部"}:
            keywords = [str(word) for word in item.get("keywords", [])]
            if category in SCHOOL_RECOGNITION_LABELS:
                category_matched = is_school_recognized(item)
            else:
                category_matched = category == item.get("category") or category in keywords
            if not category_matched:
                continue
        if keyword:
            haystack = _contest_search_text(item)
            if keyword not in haystack:
                continue
        result.append(item)
    return result


def enrich_contests(contests: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return attach_knowledge(contests)


def light_contest_item(item: dict[str, Any]) -> dict[str, Any]:
    condition_text = str(item.get("conditions") or item.get("target_audience") or "").strip()
    condition_label = str(
        item.get("condition_label")
        or ("参赛对象" if item.get("target_audience") and not item.get("conditions") else "报名条件")
    ).strip()
    location = str(item.get("location") or item.get("venue") or "").strip()
    keywords = [str(word) for word in (item.get("keywords") or []) if str(word).strip()]
    return {
        "id": item.get("id"),
        "name": item.get("name", "竞赛"),
        "source_name": item.get("source_name", "竞赛官网"),
        "status": item.get("status") or "待官网更新",
        "category": item.get("category") or "竞赛",
        "deadline": item.get("deadline") or "",
        "location": location,
        "desc": item.get("desc") or item.get("description") or "",
        "official_link": item.get("official_link") or "",
        "latest_notice_link": item.get("latest_notice_link") or "",
        "deadline_source": item.get("deadline_source") or "",
        "keywords": keywords,
        "bonus_summary": item.get("bonus_summary") or "",
        "is_hit_recognized": bool(item.get("is_hit_recognized")),
        "conditions": condition_text,
        "condition_label": condition_label,
        "has_deadline": bool(item.get("deadline")),
        "has_location": bool(location),
        "has_conditions": bool(condition_text),
        "profile_match_score": item.get("profile_match_score"),
        "profile_match_reason": item.get("profile_match_reason") or "",
    }


def paginate_contests(contests: list[dict[str, Any]], page: int = 1, page_size: int = 20) -> dict[str, Any]:
    safe_page_size = min(50, max(1, int(page_size or 20)))
    total = len(contests)
    total_pages = (total + safe_page_size - 1) // safe_page_size
    safe_page = max(1, int(page or 1))
    if total_pages:
        safe_page = min(safe_page, total_pages)
    start = (safe_page - 1) * safe_page_size
    end = start + safe_page_size
    return {
        "total": total,
        "page": safe_page,
        "page_size": safe_page_size,
        "total_pages": total_pages,
        "items": [light_contest_item(item) for item in contests[start:end]],
    }


def _mock_wechat_login(code: str, login_type: str = "wechat-mock") -> dict[str, Any]:
    seed = f"{code}:{time.time()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return {
        "ok": True,
        "token": f"mock-token-{digest}",
        "openid": f"mock-openid-{digest}",
        "loginType": login_type,
    }


def _wechat_code_to_session(code: str) -> dict[str, Any] | None:
    appid = os.getenv("WECHAT_APPID", "").strip()
    secret = os.getenv("WECHAT_SECRET", "").strip()
    if not appid or not secret:
        return None

    query = urlencode(
        {
            "appid": appid,
            "secret": secret,
            "js_code": code,
            "grant_type": "authorization_code",
        }
    )
    url = f"https://api.weixin.qq.com/sns/jscode2session?{query}"
    with urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    openid = str(payload.get("openid") or "").strip()
    if not openid:
        raise ValueError(payload.get("errmsg") or "wechat code2Session failed")
    token_seed = f"{openid}:{time.time()}"
    token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()
    return {
        "ok": True,
        "token": token,
        "openid": openid,
        "loginType": "wechat",
    }


def get_contest_by_id(contest_id: str | int) -> dict[str, Any] | None:
    contest_id = normalize_id(contest_id)
    for item in enrich_contests(load_cached_or_fallback()):
        if normalize_id(item.get("id", "")) == contest_id:
            return item
    for item in enrich_contests(crawl_contests(force_refresh=False)):
        if normalize_id(item.get("id", "")) == contest_id:
            return item
    return None


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "backend is running"}


@app.get("/contests")
def get_contest_list(
    keyword: str = "",
    category: str = "鍏ㄩ儴",
    refresh: bool = Query(False, description="鏄惁寮哄埗鍒锋柊瀹樼綉鏁版嵁"),
) -> list[dict[str, Any]]:
    contests = enrich_contests(crawl_contests(force_refresh=refresh))
    return filter_contests(contests, keyword=keyword, category=category)


@app.get("/contests/search")
def search_contest_list(
    keyword: str = "",
    category: str = "全部",
    page: int = 1,
    page_size: int = 20,
    refresh: bool = Query(False, description="是否强制刷新官网数据"),
    campus: str = "",
    college: str = "",
    major: str = "",
    grade: str = "",
    target: str = "",
    interests: str = "",
    competition: str = "",
    project: str = "",
    gpa: str = "",
) -> dict[str, Any]:
    contests = enrich_contests(crawl_contests(force_refresh=refresh))
    filtered = filter_contests(contests, keyword=keyword, category=category)
    profile = {
        "campus": campus,
        "college": college,
        "major": major,
        "grade": grade,
        "target": target,
        "interests": interests,
        "competition": competition,
        "project": project,
        "gpa": gpa,
    }
    filtered = sort_contests_for_profile(filtered, profile)
    return paginate_contests(filtered, page=page, page_size=page_size)


@app.post("/contests/refresh")
def refresh_contests() -> dict[str, Any]:
    contests = crawl_contests(force_refresh=True)
    knowledge = build_contest_knowledge(contests, load_training_corpus())
    return {"ok": True, "count": len(contests), "knowledge_count": knowledge.get("contest_count", 0), "data": enrich_contests(contests)}


@app.get("/contests/sections")
def contest_sections() -> dict[str, list[dict[str, Any]]]:
    contests = enrich_contests(load_cached_or_fallback())
    return get_contest_sections(contests)


@app.get("/home/news")
def home_news() -> dict[str, Any]:
    return get_home_news(enrich_contests(load_cached_or_fallback()))


@app.get("/home/dashboard")
def home_dashboard() -> dict[str, Any]:
    return build_home_dashboard(enrich_contests(load_cached_or_fallback()))


@app.post("/auth/wechat-login")
def wechat_login(data: WechatLoginRequest) -> dict[str, Any]:
    code = data.code.strip()
    if not code:
        return {"ok": False, "message": "missing code"}
    try:
        payload = _wechat_code_to_session(code)
        if payload:
            return payload
    except Exception:
        return _mock_wechat_login(code, login_type="wechat-mock-fallback")
    return _mock_wechat_login(code)


@app.get("/contest/knowledge")
def contest_knowledge() -> dict[str, Any]:
    return {"ok": True, "data": load_knowledge_base()}


@app.post("/contest/knowledge/rebuild")
def rebuild_contest_knowledge() -> dict[str, Any]:
    contests = load_cached_or_fallback()
    knowledge = build_contest_knowledge(contests, load_training_corpus())
    return {"ok": True, "data": knowledge}


@app.post("/contests/hit")
def contest_hit(data: ItemAddRequest) -> dict[str, Any]:
    return {"ok": True, "data": record_click(data.item_id)}


@app.get("/contest/{contest_id}")
def get_contest_detail(contest_id: str) -> dict[str, Any]:
    contest = get_contest_by_id(contest_id)
    if contest:
        return contest
    return {"error": "contest not found"}


@app.get("/matches")
def get_matches() -> dict[str, Any]:
    return build_match_payload(enrich_contests(load_cached_or_fallback()))


@app.get("/ai/status")
def ai_status() -> dict[str, Any]:
    status = public_llm_status()
    status["self_model"] = self_model_status(enrich_contests(load_cached_or_fallback()))
    return status


@app.post("/ai/deepseek/config")
def configure_deepseek(data: DeepSeekConfigRequest) -> dict[str, Any]:
    config = save_deepseek_config(api_key=data.api_key, model=data.model, base_url=data.base_url)
    return {"ok": True, "data": public_llm_status(), "config_path": config["config_path"]}


@app.get("/ai/deepseek/test")
def test_deepseek() -> dict[str, Any]:
    client, llm = get_llm_client()
    if not client:
        return {
            "ok": False,
            "message": "DeepSeek API Key 未配置。请设置 DEEPSEEK_API_KEY 环境变量，或写入 backend/data/llm_config.local.json。",
            "data": public_llm_status(),
        }
    try:
        completion = client.chat.completions.create(
            model=llm["model"],
            messages=[
                {"role": "system", "content": "你是智竞工大竞赛智能体，只做接口连通性测试。"},
                {"role": "user", "content": "请用一句话回复：DeepSeek V4 接口已连接。"},
            ],
            temperature=0.1,
        )
        return {"ok": True, "message": completion.choices[0].message.content, "data": public_llm_status()}
    except Exception as exc:
        return {"ok": False, "message": str(exc), "data": public_llm_status()}


@app.post("/self-model/train")
def train_local_self_model(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    contests = load_cached_or_fallback()
    model = ensure_self_model(contests, force=True, collect_web=bool(payload.get("collect_web", True)))
    return {"ok": True, "data": self_model_status(enrich_contests(contests)), "trained_at": model.get("trained_at")}


@app.get("/hit/options")
def hit_options(refresh: bool = False) -> dict[str, Any]:
    return get_hit_options(force_refresh=refresh)


@app.post("/hit/options/refresh")
def refresh_hit_options() -> dict[str, Any]:
    return get_hit_options(force_refresh=True)


@app.get("/mentors")
def mentors(refresh: bool = False) -> dict[str, Any]:
    return crawl_hit_mentors(force_refresh=refresh)


@app.get("/mentors/search")
def mentors_search(
    keyword: str = "",
    college: str = "",
    campus: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    return search_hit_mentors(keyword=keyword, college=college, campus=campus, page=page, page_size=page_size)


@app.get("/mentors/options")
def mentors_options() -> dict[str, Any]:
    return mentor_filter_options()


@app.post("/mentors/refresh")
def refresh_mentors() -> dict[str, Any]:
    payload = crawl_hit_mentors(force_refresh=True)
    return {
        "ok": True,
        "count": payload.get("count", 0),
        "refreshed_at": payload.get("refreshed_at", ""),
        "sources": payload.get("sources", []),
    }


@app.get("/recruit/posts")
def recruit_posts() -> list[dict[str, Any]]:
    return list_posts()


@app.post("/recruit/posts/query")
def query_recruit_posts(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": list_posts(payload.get("profile") or {})}


@app.get("/recruit/post/{post_id}")
def recruit_post_detail(post_id: int) -> dict[str, Any]:
    item = get_post_detail(post_id)
    if not item:
        return {"ok": False, "message": "post not found"}
    return {"ok": True, "data": item}


@app.post("/recruit/posts")
def publish_recruit_post(payload: dict[str, Any]) -> dict[str, Any]:
    return create_post(payload)


@app.post("/recruit/polish")
def polish_recruit_post(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": polish_recruitment(payload)}


@app.post("/recruit/apply")
def recruit_apply(payload: dict[str, Any]) -> dict[str, Any]:
    return apply_to_post(payload)


@app.post("/recruit/my")
def my_recruitment(payload: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "data": get_user_recruitment(payload.get("profile") or {})}


@app.post("/recruit/applications/decide")
def handle_recruit_application(payload: dict[str, Any]) -> dict[str, Any]:
    return decide_application(payload)


@app.post("/recruit/unbind")
def handle_recruit_unbind(payload: dict[str, Any]) -> dict[str, Any]:
    return request_unbind(payload)


@app.post("/recruit/complain")
def handle_recruit_complain(payload: dict[str, Any]) -> dict[str, Any]:
    return complain_member(payload)


@app.get("/match/{match_type}/{match_id}")
def get_match_detail(match_type: str, match_id: int) -> dict[str, Any]:
    item = find_match_item(match_type, match_id)
    if item:
        return item
    return {"error": "match not found"}


@app.get("/my/contests")
def get_my_contests() -> list[dict[str, Any]]:
    return store_get_my_contests()


@app.post("/my/contests/add")
def add_my_contest(data: ItemAddRequest) -> dict[str, Any]:
    target = get_contest_by_id(data.item_id)
    if not target:
        return {"ok": False, "message": "contest not found"}

    ok, message, contests = store_add_my_contest(target)
    return {"ok": ok, "message": message, "data": contests}


@app.post("/my/contests/remove")
def remove_my_contest(data: ItemAddRequest) -> dict[str, Any]:
    contests = store_remove_my_contest(data.item_id)
    return {"ok": True, "message": "removed", "data": contests}


@app.get("/my/matches")
def get_my_matches() -> list[dict[str, Any]]:
    return store_get_my_matches()


@app.post("/my/matches/add")
def add_my_match(data: MatchAddRequest) -> dict[str, Any]:
    target = find_match_item(data.item_type, data.item_id)

    if not target:
        return {"ok": False, "message": "match target not found"}

    ok, message, matches = store_add_my_match(target)
    return {"ok": ok, "message": message, "data": matches}


@app.post("/my/matches/remove")
def remove_my_match(data: MatchAddRequest) -> dict[str, Any]:
    matches = store_remove_my_match(data.item_id, data.item_type)
    return {"ok": True, "message": "removed", "data": matches}


@app.post("/ask")
def ask_ai(data: AskRequest) -> dict[str, Any]:
    question = data.question.strip()
    client, llm = get_llm_client()
    return answer_question(
        question=question,
        profile=data.profile or {},
        contests=enrich_contests(load_cached_or_fallback()),
        client=client,
        model=llm["model"],
        provider_label=llm["label"],
    )


