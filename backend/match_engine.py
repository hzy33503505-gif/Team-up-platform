from __future__ import annotations

from copy import deepcopy

from hit_directory import crawl_hit_mentors
from recruitment_store import list_posts


MATCH_TEAMS: list[dict] = []
MATCH_MENTORS: list[dict] = []


def _mentor_to_match_item(mentor: dict) -> dict:
    return {
        "id": mentor.get("id"),
        "type": "mentor",
        "title": mentor.get("name", "导师"),
        "subtitle": " · ".join(
            part
            for part in [mentor.get("campus"), mentor.get("college"), mentor.get("title")]
            if part
        ),
        "score": 0,
        "intro": mentor.get("direction") or "导师研究方向以官方主页为准。",
        "demand": mentor.get("requirements", ""),
        "tags": mentor.get("tags", []),
        "members": mentor.get("contact_email", ""),
        "fit": mentor.get("direction", ""),
        "advice": "导师信息来自官方教师主页或学院教师名录，请点击官方链接核对后再联系。",
        "homepage": mentor.get("homepage") or mentor.get("source_url"),
        "source_url": mentor.get("source_url"),
    }


def build_match_payload(contests: list[dict] | None = None) -> dict:
    mentors = [_mentor_to_match_item(item) for item in crawl_hit_mentors(force_refresh=False).get("items", [])]
    posts = list_posts()
    return {
        "teams": posts,
        "mentors": mentors,
        "feed": posts,
        "topics": ["综合", "队友招募", "导师库"],
        "strategy": [
            {
                "title": "先门槛后适配",
                "desc": "先看发布者设置的校区、学院、年级、专业门槛，再计算技能和经历匹配。",
            },
            {
                "title": "申请制匹配",
                "desc": "用户发送申请，发布者同意后才算组队成功，岗位人数同步减少。",
            },
            {
                "title": "官方导师源",
                "desc": "导师库只展示可追溯到哈工大官方主页或学院名录的信息。",
            },
        ],
        "behavior_tags": [],
    }


def find_match_item(match_type: str, match_id) -> dict | None:
    if match_type == "team":
        for item in list_posts():
            if str(item.get("id")) == str(match_id):
                return deepcopy(item)
    if match_type == "mentor":
        for item in crawl_hit_mentors(force_refresh=False).get("items", []):
            if str(item.get("id")) == str(match_id):
                return _mentor_to_match_item(item)
    return None
