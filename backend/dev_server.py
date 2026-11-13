from __future__ import annotations

import hashlib
import json
import os
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import urlopen

from ai_agent import answer_question
from contest_knowledge import attach_knowledge, build_contest_knowledge, load_knowledge_base
from contest_crawler import get_contests, load_cached_or_fallback
from contest_metrics import get_contest_sections, record_click
from hit_directory import crawl_hit_mentors, get_hit_options, mentor_filter_options, search_hit_mentors
from llm_config import get_llm_client, public_llm_status
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
    add_my_contest,
    add_my_match,
    get_my_contests,
    get_my_matches,
    remove_my_contest,
    remove_my_match,
)
from web_training_corpus import load_training_corpus


TEAM_MATCHES = MATCH_TEAMS
MENTOR_MATCHES = MATCH_MENTORS


def normalize_id(value) -> str:
    return str(value)


def filter_contests(items: list[dict], keyword: str = "", category: str = "鍏ㄩ儴") -> list[dict]:
    keyword = keyword.strip().lower()
    category = category.strip()
    result = []
    for item in items:
        if category and category not in {"鍏ㄩ儴", "全部"}:
            keywords = [str(word) for word in item.get("keywords", [])]
            category_matched = (
                bool(item.get("is_hit_recognized"))
                if category == "鏍″唴璁ゅ畾"
                else category == item.get("category") or category in keywords
            )
            if not category_matched:
                continue
        if keyword:
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("category", "")),
                    str(item.get("desc", "")),
                    str(item.get("bonus_summary", "")),
                    str(item.get("prestige_score", "")),
                    str((item.get("prestige") or {}).get("summary", "")),
                    " ".join(item.get("organizers", [])),
                    " ".join(item.get("keywords", [])),
                ]
            ).lower()
            if keyword not in haystack:
                continue
        result.append(item)
    return result


def enrich_contests(items: list[dict]) -> list[dict]:
    return attach_knowledge(items)


def light_contest_item(item: dict) -> dict:
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
        "keywords": keywords,
        "bonus_summary": item.get("bonus_summary") or "",
        "is_hit_recognized": bool(item.get("is_hit_recognized")),
        "conditions": condition_text,
        "condition_label": condition_label,
        "has_deadline": bool(item.get("deadline")),
        "has_location": bool(location),
        "has_conditions": bool(condition_text),
    }


def paginate_contests(contests: list[dict], page: int = 1, page_size: int = 20) -> dict:
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


def _mock_wechat_login(code: str, login_type: str = "wechat-mock") -> dict:
    seed = f"{code}:{time.time()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:24]
    return {
        "ok": True,
        "token": f"mock-token-{digest}",
        "openid": f"mock-openid-{digest}",
        "loginType": login_type,
    }


def _wechat_code_to_session(code: str) -> dict | None:
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


def find_contest(contest_id: str) -> dict | None:
    for item in enrich_contests(load_cached_or_fallback()):
        if normalize_id(item.get("id")) == normalize_id(contest_id):
            return item
    for item in enrich_contests(get_contests(force_refresh=False)):
        if normalize_id(item.get("id")) == normalize_id(contest_id):
            return item
    return None


def find_match(match_type: str, match_id) -> dict | None:
    return find_match_item(match_type, match_id)


class Handler(BaseHTTPRequestHandler):
    server_version = "ZhijingDevServer/1.0"

    def _send_json(self, payload, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:
        self._send_json({"ok": True})

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/":
            self._send_json({"message": "dev backend is running"})
            return

        if parsed.path == "/contests":
            refresh = query.get("refresh", ["false"])[0].lower() == "true"
            keyword = query.get("keyword", [""])[0]
            category = query.get("category", ["鍏ㄩ儴"])[0]
            items = get_contests(force_refresh=True) if refresh else load_cached_or_fallback()
            items = enrich_contests(items)
            self._send_json(filter_contests(items, keyword=keyword, category=category))
            return

        if parsed.path == "/contests/search":
            refresh = query.get("refresh", ["false"])[0].lower() == "true"
            keyword = query.get("keyword", [""])[0]
            category = query.get("category", ["全部"])[0]
            page = int(query.get("page", ["1"])[0] or 1)
            page_size = int(query.get("page_size", ["20"])[0] or 20)
            items = get_contests(force_refresh=True) if refresh else load_cached_or_fallback()
            items = enrich_contests(items)
            filtered = filter_contests(items, keyword=keyword, category=category)
            self._send_json(paginate_contests(filtered, page=page, page_size=page_size))
            return

        if parsed.path == "/contests/sections":
            items = enrich_contests(load_cached_or_fallback())
            self._send_json(get_contest_sections(items))
            return

        if parsed.path == "/home/news":
            self._send_json(get_home_news(enrich_contests(load_cached_or_fallback())))
            return

        if parsed.path == "/home/dashboard":
            self._send_json(build_home_dashboard(enrich_contests(load_cached_or_fallback())))
            return

        if parsed.path == "/contest/knowledge":
            self._send_json({"ok": True, "data": load_knowledge_base()})
            return

        if parsed.path.startswith("/contest/"):
            contest_id = unquote(parsed.path.split("/contest/", 1)[1])
            item = find_contest(contest_id)
            self._send_json(item or {"error": "contest not found"}, 200 if item else 404)
            return

        if parsed.path == "/matches":
            self._send_json(build_match_payload(enrich_contests(load_cached_or_fallback())))
            return

        if parsed.path == "/ai/status":
            status = public_llm_status()
            status["self_model"] = self_model_status(enrich_contests(load_cached_or_fallback()))
            self._send_json(status)
            return

        if parsed.path == "/hit/options":
            refresh = query.get("refresh", ["false"])[0].lower() == "true"
            self._send_json(get_hit_options(force_refresh=refresh))
            return

        if parsed.path == "/mentors":
            refresh = query.get("refresh", ["false"])[0].lower() == "true"
            self._send_json(crawl_hit_mentors(force_refresh=refresh))
            return

        if parsed.path == "/mentors/search":
            keyword = query.get("keyword", [""])[0]
            college = query.get("college", [""])[0]
            campus = query.get("campus", [""])[0]
            page = int(query.get("page", ["1"])[0] or 1)
            page_size = int(query.get("page_size", ["20"])[0] or 20)
            self._send_json(search_hit_mentors(keyword=keyword, college=college, campus=campus, page=page, page_size=page_size))
            return

        if parsed.path == "/mentors/options":
            self._send_json(mentor_filter_options())
            return

        if parsed.path == "/recruit/posts":
            self._send_json(list_posts())
            return

        if parsed.path.startswith("/recruit/post/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3:
                item = get_post_detail(parts[2])
                self._send_json({"ok": bool(item), "data": item} if item else {"ok": False, "message": "post not found"}, 200 if item else 404)
                return

        if parsed.path.startswith("/match/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3:
                item = find_match(parts[1], parts[2])
                self._send_json(item or {"error": "match not found"}, 200 if item else 404)
                return

        if parsed.path == "/my/contests":
            self._send_json(get_my_contests())
            return

        if parsed.path == "/my/matches":
            self._send_json(get_my_matches())
            return

        self._send_json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {}

        if parsed.path == "/contests/refresh":
            items = get_contests(force_refresh=True)
            knowledge = build_contest_knowledge(items, load_training_corpus())
            self._send_json({"ok": True, "count": len(items), "knowledge_count": knowledge.get("contest_count", 0), "data": enrich_contests(items)})
            return

        if parsed.path == "/contests/hit":
            contest_id = payload.get("item_id") or payload.get("contest_id") or ""
            if not contest_id:
                self._send_json({"ok": False, "message": "缂哄皯绔炶禌ID"})
                return
            metric = record_click(contest_id)
            self._send_json({"ok": True, "data": metric})
            return

        if parsed.path == "/contest/knowledge/rebuild":
            contests = load_cached_or_fallback()
            knowledge = build_contest_knowledge(contests, load_training_corpus())
            self._send_json({"ok": True, "data": knowledge})
            return

        if parsed.path == "/hit/options/refresh":
            self._send_json(get_hit_options(force_refresh=True))
            return

        if parsed.path == "/mentors/refresh":
            payload = crawl_hit_mentors(force_refresh=True)
            self._send_json({
                "ok": True,
                "count": payload.get("count", 0),
                "refreshed_at": payload.get("refreshed_at", ""),
                "sources": payload.get("sources", []),
            })
            return

        if parsed.path == "/recruit/posts/query":
            self._send_json({"ok": True, "data": list_posts(payload.get("profile") or {})})
            return

        if parsed.path == "/recruit/posts":
            self._send_json(create_post(payload))
            return

        if parsed.path == "/recruit/polish":
            self._send_json({"ok": True, "data": polish_recruitment(payload)})
            return

        if parsed.path == "/recruit/apply":
            self._send_json(apply_to_post(payload))
            return

        if parsed.path == "/recruit/my":
            self._send_json({"ok": True, "data": get_user_recruitment(payload.get("profile") or {})})
            return

        if parsed.path == "/recruit/applications/decide":
            self._send_json(decide_application(payload))
            return

        if parsed.path == "/recruit/unbind":
            self._send_json(request_unbind(payload))
            return

        if parsed.path == "/recruit/complain":
            self._send_json(complain_member(payload))
            return

        if parsed.path == "/ask":
            client, llm = get_llm_client()
            self._send_json(
                answer_question(
                    question=payload.get("question", ""),
                    profile=payload.get("profile") or {},
                    contests=enrich_contests(load_cached_or_fallback()),
                    client=client,
                    model=llm["model"],
                    provider_label=llm["label"],
                )
            )
            return

        if parsed.path == "/self-model/train":
            contests = load_cached_or_fallback()
            model = ensure_self_model(contests, force=True, collect_web=bool(payload.get("collect_web", True)))
            self._send_json({"ok": True, "data": self_model_status(enrich_contests(contests)), "trained_at": model.get("trained_at")})
            return

        if parsed.path == "/auth/wechat-login":
            code = str(payload.get("code") or "").strip()
            if not code:
                self._send_json({"ok": False, "message": "missing code"})
                return
            try:
                login_payload = _wechat_code_to_session(code)
                if login_payload:
                    self._send_json(login_payload)
                    return
            except Exception:
                self._send_json(_mock_wechat_login(code, login_type="wechat-mock-fallback"))
                return
            self._send_json(_mock_wechat_login(code))
            return

        if parsed.path == "/my/contests/add":
            item = find_contest(payload.get("item_id", ""))
            if not item:
                self._send_json({"ok": False, "message": "contest not found"})
                return
            ok, message, contests = add_my_contest(item)
            self._send_json({"ok": ok, "message": message, "data": contests})
            return

        if parsed.path == "/my/contests/remove":
            contests = remove_my_contest(payload.get("item_id", ""))
            self._send_json({"ok": True, "message": "removed", "data": contests})
            return

        if parsed.path == "/my/matches/add":
            item = find_match(payload.get("item_type", ""), payload.get("item_id", ""))
            if not item:
                self._send_json({"ok": False, "message": "match target not found"})
                return
            ok, message, matches = add_my_match(item)
            self._send_json({"ok": ok, "message": message, "data": matches})
            return

        if parsed.path == "/my/matches/remove":
            matches = remove_my_match(payload.get("item_id", ""), payload.get("item_type", ""))
            self._send_json({"ok": True, "message": "removed", "data": matches})
            return

        self._send_json({"error": "not found"}, 404)


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"dev backend listening on http://{host}:{port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    run()


