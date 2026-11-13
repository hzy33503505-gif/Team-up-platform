from __future__ import annotations

import datetime as dt
import json
import re
from copy import deepcopy
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)
STORE_PATH = DATA_DIR / "recruitment_store.json"


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _today() -> dt.datetime:
    now = dt.datetime.now()
    return dt.datetime(now.year, now.month, now.day)


def _empty_store() -> dict:
    return {
        "posts": [],
        "applications": [],
        "unbind_requests": [],
        "complaints": [],
        "penalties": {},
        "demo_seed_version": 0,
        "counters": {"post": 0, "application": 0, "unbind": 0, "complaint": 0},
    }


def _profile(name: str, student_id: str, campus: str, college: str, major: str, grade: str, interests: list[str]) -> dict:
    return {
        "name": name,
        "studentId": student_id,
        "campus": campus,
        "college": college,
        "major": major,
        "grade": grade,
        "target": "竞赛获奖、项目经历、保研/就业材料沉淀",
        "interests": interests,
        "gpa": "",
        "phone": "",
        "qq": "",
        "phonePublic": False,
        "qqPublic": False,
    }


DEMO_RECRUITMENT_POSTS = [
    {
        "id": 101,
        "demo_key": "demo-mcm-2026",
        "title": "数学建模国赛建模与论文队友招募",
        "contest_name": "全国大学生数学建模竞赛",
        "description": "队伍已有一名负责建模和一名负责代码实现，目标是完整冲刺国赛。当前需要补齐论文写作、图表排版和结果解释，要求每周稳定投入两到三晚。",
        "tags_text": "数学建模、Python、论文写作、数据分析",
        "roles": [
            {"id": "1", "name": "论文手", "direction": "论文写作与排版", "needed": 1, "filled": 0, "skills": ["LaTeX", "Word", "论文结构"], "confirmed_members": [], "status": "招募中"},
            {"id": "2", "name": "数据分析", "direction": "模型求解与可视化", "needed": 1, "filled": 0, "skills": ["Python", "MATLAB", "可视化"], "confirmed_members": [], "status": "招募中"},
        ],
        "gates": {"campuses": [], "colleges": [], "grades": ["大二", "大三"], "majors": [], "require_statement": True},
        "publisher_id": "demo202601",
        "publisher_profile": _profile("林同学", "demo202601", "哈尔滨校区", "计算学部", "计算机科学与技术", "大二", ["数学建模", "算法", "数据分析"]),
    },
    {
        "id": 102,
        "demo_key": "demo-software-cup",
        "title": "中国软件杯AI应用队招后端与产品",
        "contest_name": "中国软件杯大学生软件设计大赛",
        "description": "准备做面向校园竞赛服务的AI应用，已有前端原型和基础需求文档。希望招募后端、算法接口和产品答辩成员，一起完成可演示系统。",
        "tags_text": "中国软件杯、AI应用、后端、产品答辩",
        "roles": [
            {"id": "1", "name": "后端开发", "direction": "接口与数据库", "needed": 1, "filled": 0, "skills": ["Python", "FastAPI", "数据库"], "confirmed_members": [], "status": "招募中"},
            {"id": "2", "name": "产品答辩", "direction": "需求梳理与PPT", "needed": 1, "filled": 0, "skills": ["原型", "PPT", "路演"], "confirmed_members": [], "status": "招募中"},
        ],
        "gates": {"campuses": [], "colleges": ["计算学部"], "grades": [], "majors": [], "require_statement": False},
        "publisher_id": "demo202602",
        "publisher_profile": _profile("周同学", "demo202602", "哈尔滨校区", "计算学部", "软件工程", "大三", ["AI", "软件开发", "产品设计"]),
    },
    {
        "id": 103,
        "demo_key": "demo-nuedc",
        "title": "电子设计竞赛硬件调试队补控制方向",
        "contest_name": "全国大学生电子设计竞赛",
        "description": "队伍已有电路基础和仪器资源，方向偏嵌入式控制与信号采集。需要能做单片机/STM32调试、传感器采集或测试记录的同学。",
        "tags_text": "电子设计、STM32、硬件调试、控制",
        "roles": [
            {"id": "1", "name": "控制算法", "direction": "嵌入式控制", "needed": 1, "filled": 0, "skills": ["STM32", "C语言", "控制"], "confirmed_members": [], "status": "招募中"},
            {"id": "2", "name": "测试记录", "direction": "实验记录与报告", "needed": 1, "filled": 1, "skills": ["示波器", "报告", "数据整理"], "confirmed_members": [{"application_id": 0, "user_id": "demo-member-103", "profile": _profile("已定成员", "demo-member-103", "威海校区", "信息科学与工程学院", "电子信息工程", "大二", ["电子设计"]), "joined_at": _now()}], "status": "已确定"},
        ],
        "gates": {"campuses": ["威海校区"], "colleges": [], "grades": [], "majors": [], "require_statement": True},
        "publisher_id": "demo202603",
        "publisher_profile": _profile("王同学", "demo202603", "威海校区", "信息科学与工程学院", "电子信息工程", "大二", ["电子设计", "嵌入式"]),
    },
    {
        "id": 104,
        "demo_key": "demo-robomaster",
        "title": "RoboMaster视觉识别方向招募",
        "contest_name": "RoboMaster高校系列赛",
        "description": "实验室队伍需要补视觉识别和ROS联调方向，已有机械和电控同学。适合愿意长期投入、能做代码复盘和现场调试的同学。",
        "tags_text": "RoboMaster、机器人、OpenCV、ROS",
        "roles": [
            {"id": "1", "name": "视觉识别", "direction": "目标检测与追踪", "needed": 2, "filled": 0, "skills": ["OpenCV", "Python", "深度学习"], "confirmed_members": [], "status": "招募中"},
            {"id": "2", "name": "ROS联调", "direction": "机器人系统集成", "needed": 1, "filled": 0, "skills": ["ROS", "Linux", "C++"], "confirmed_members": [], "status": "招募中"},
        ],
        "gates": {"campuses": [], "colleges": [], "grades": ["大一", "大二", "大三"], "majors": [], "require_statement": True},
        "publisher_id": "demo202604",
        "publisher_profile": _profile("赵同学", "demo202604", "深圳校区", "机电工程与自动化学院", "自动化", "大三", ["机器人", "机器视觉"]),
    },
    {
        "id": 105,
        "demo_key": "demo-challenge-cup",
        "title": "挑战杯创业计划项目招产品与调研",
        "contest_name": "挑战杯中国大学生创业计划竞赛",
        "description": "项目方向是校园低碳能源管理，已有技术方案雏形。希望补充用户调研、商业模式、路演PPT和财务测算，目标形成完整创业计划书。",
        "tags_text": "挑战杯、创新创业、产品、调研、路演",
        "roles": [
            {"id": "1", "name": "用户调研", "direction": "访谈与数据整理", "needed": 1, "filled": 0, "skills": ["问卷", "访谈", "数据分析"], "confirmed_members": [], "status": "招募中"},
            {"id": "2", "name": "路演材料", "direction": "PPT与商业计划书", "needed": 1, "filled": 0, "skills": ["PPT", "商业模式", "文案"], "confirmed_members": [], "status": "招募中"},
        ],
        "gates": {"campuses": [], "colleges": [], "grades": [], "majors": [], "require_statement": False},
        "publisher_id": "demo202605",
        "publisher_profile": _profile("陈同学", "demo202605", "哈尔滨校区", "经济与管理学院", "工商管理", "大二", ["创新创业", "产品设计"]),
    },
]


def _ensure_demo_posts(data: dict) -> bool:
    existing = {item.get("demo_key") for item in data.get("posts", []) if item.get("demo_key")}
    changed = False
    for post in DEMO_RECRUITMENT_POSTS:
        if post["demo_key"] in existing:
            continue
        copied = deepcopy(post)
        copied.setdefault("created_at", _now())
        copied.setdefault("updated_at", _now())
        data["posts"].append(copied)
        changed = True
    if changed:
        data["counters"]["post"] = max(int(data.get("counters", {}).get("post", 0)), 105)
        data["demo_seed_version"] = 1
    return changed


def _load() -> dict:
    if not STORE_PATH.exists():
        data = _empty_store()
        _ensure_demo_posts(data)
        return data
    try:
        data = json.loads(STORE_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        data = _empty_store()
        _ensure_demo_posts(data)
        return data
    base = _empty_store()
    base.update(data)
    base["counters"].update(data.get("counters", {}))
    if _ensure_demo_posts(base):
        _save(base)
    return base


def _save(data: dict) -> None:
    STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _next_id(data: dict, key: str) -> int:
    data["counters"][key] = int(data["counters"].get(key, 0)) + 1
    return data["counters"][key]


def user_id(profile: dict | None) -> str:
    profile = profile or {}
    return str(
        profile.get("studentId")
        or profile.get("hitAccount")
        or profile.get("name")
        or "anonymous"
    ).strip()


def profile_is_complete(profile: dict | None) -> tuple[bool, list[str]]:
    profile = profile or {}
    required = [
        ("name", "姓名"),
        ("studentId", "学号"),
        ("campus", "校区"),
        ("college", "学院"),
        ("major", "专业"),
        ("grade", "年级"),
    ]
    missing = [label for key, label in required if not str(profile.get(key, "")).strip()]
    return not missing, missing


def _split_words(value: str) -> list[str]:
    return [part.strip() for part in re.split(r"[，,；;\s、/|]+", value or "") if part.strip()]


def _profile_text(profile: dict) -> str:
    return " ".join(
        [
            str(profile.get("major", "")),
            str(profile.get("target", "")),
            " ".join(profile.get("interests", []) if isinstance(profile.get("interests"), list) else []),
            str(profile.get("competition", "")),
            str(profile.get("project", "")),
        ]
    )


def _public_profile(profile: dict, include_experience: bool = False) -> dict:
    result = {
        "name": profile.get("name", ""),
        "studentId": profile.get("studentId", ""),
        "campus": profile.get("campus", ""),
        "college": profile.get("college", ""),
        "major": profile.get("major", ""),
        "grade": profile.get("grade", ""),
        "target": profile.get("target", ""),
        "interests": profile.get("interests", []) if isinstance(profile.get("interests"), list) else [],
        "gpa": profile.get("gpa", ""),
        "phone": profile.get("phone", "") if profile.get("phonePublic") else "",
        "qq": profile.get("qq", "") if profile.get("qqPublic") else "",
        "phonePublic": bool(profile.get("phonePublic")),
        "qqPublic": bool(profile.get("qqPublic")),
    }
    if include_experience:
        result.update(
            {
                "competition": profile.get("competition", ""),
                "project": profile.get("project", ""),
            }
        )
    return result


def _gate_values(gates: dict, key: str) -> list[str]:
    value = gates.get(key)
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def get_penalty(profile: dict | None) -> dict | None:
    data = _load()
    uid = user_id(profile)
    penalty = data.get("penalties", {}).get(uid)
    if not penalty:
        return None
    until_text = penalty.get("until", "")
    try:
        until = dt.datetime.strptime(until_text, "%Y-%m-%d")
    except ValueError:
        return None
    if until >= _today():
        return penalty
    data["penalties"].pop(uid, None)
    _save(data)
    return None


def evaluate_candidate(post: dict, role: dict | None, profile: dict | None, statement: str = "") -> dict:
    profile = profile or {}
    role = role or {}
    gates = post.get("gates", {})
    passed = True
    reasons: list[str] = []

    for gate_key, profile_key, label in [
        ("campuses", "campus", "校区"),
        ("colleges", "college", "学院"),
        ("grades", "grade", "年级"),
        ("majors", "major", "专业"),
    ]:
        allowed = _gate_values(gates, gate_key)
        if allowed and profile.get(profile_key) not in allowed:
            passed = False
            reasons.append(f"{label}不符合发布者门槛")
        elif allowed:
            reasons.append(f"{label}符合门槛")

    penalty = get_penalty(profile)
    if penalty:
        passed = False
        reasons.append(f"账号处于组队限制期，截止 {penalty.get('until')}")

    if gates.get("require_statement") and not statement.strip():
        passed = False
        reasons.append("发布者要求填写申请说明")

    score = 40 if passed else 0
    details: list[dict] = []

    if post.get("publisher_profile", {}).get("campus") == profile.get("campus"):
        score += 8
        details.append({"label": "校区", "value": 8, "reason": "与发布者同校区，线下沟通成本低"})
    if post.get("publisher_profile", {}).get("college") == profile.get("college"):
        score += 6
        details.append({"label": "学院", "value": 6, "reason": "与发布者同学院，课程与资源更接近"})

    profile_text = _profile_text(profile)
    role_words = _split_words(" ".join([role.get("name", ""), role.get("direction", ""), " ".join(role.get("skills", []))]))
    hits = [word for word in role_words if word and word in profile_text]
    if hits:
        add = min(28, 8 + len(hits) * 5)
        score += add
        details.append({"label": "技能经历", "value": add, "reason": f"命中岗位关键词：{'、'.join(hits[:4])}"})
    else:
        details.append({"label": "技能经历", "value": 0, "reason": "暂未从个人经历中识别到岗位关键词"})

    interest_hits = [word for word in _split_words(post.get("tags_text", "")) if word and word in profile_text]
    if interest_hits:
        add = min(12, len(interest_hits) * 4)
        score += add
        details.append({"label": "方向兴趣", "value": add, "reason": f"个人信息中出现相关方向：{'、'.join(interest_hits[:3])}"})

    if statement.strip():
        score += 8
        details.append({"label": "申请说明", "value": 8, "reason": "提交了具体申请说明，便于发布者判断"})

    score = max(0, min(100, score))
    return {
        "passed": passed,
        "score": score,
        "reasons": reasons or ["无硬性门槛"],
        "details": details,
    }


def polish_recruitment(payload: dict) -> dict:
    text = str(payload.get("description", "")).strip()
    contest_name = str(payload.get("contest_name", "")).strip() or "目标竞赛"
    roles_text = str(payload.get("roles_text", "")).strip()
    tags = _split_words(" ".join([contest_name, text, roles_text]))
    useful_tags = [word for word in tags if len(word) >= 2][:8]
    title = str(payload.get("title", "")).strip() or f"{contest_name}队友招募"
    direction = "综合协作"
    if any(word in " ".join([contest_name, text, roles_text]) for word in ["AI", "人工智能", "数据", "模型", "算法"]):
        direction = "算法/数据/模型"
    elif any(word in " ".join([contest_name, text, roles_text]) for word in ["数学建模", "统计", "建模"]):
        direction = "建模/论文/数据分析"
    elif any(word in " ".join([contest_name, text, roles_text]) for word in ["电子", "硬件", "机器人", "智能车", "控制"]):
        direction = "硬件/控制/调试"
    elif any(word in " ".join([contest_name, text, roles_text]) for word in ["创业", "挑战杯", "互联网", "产品", "商业"]):
        direction = "产品/调研/路演"
    elif any(word in " ".join([contest_name, text, roles_text]) for word in ["设计", "视频", "广告", "视觉"]):
        direction = "视觉/文案/展示"

    raw_need = text or "希望补齐关键分工，尽快形成可提交作品和答辩材料。"
    role_hint = roles_text or f"{direction}方向队友1-2名"
    summary = (
        f"我们准备围绕{contest_name}组建/补强队伍，目前重点方向是{direction}。"
        f"当前需求：{raw_need} "
        f"拟招募角色：{role_hint}。"
        "希望队友能稳定沟通、按周推进，参与资料整理、方案实现、测试记录和最终答辩。"
        "申请时请简单说明：你能承担的角色、相关课程/项目/竞赛经历、每周可投入时间，以及为什么想加入本队。"
    )
    if len(summary) > 360:
        summary = summary[:359] + "…"
    return {
        "title": title,
        "summary": summary,
        "tags_text": "、".join(useful_tags),
        "suggestion": "已按竞赛目标、当前进度、角色缺口、时间投入和申请说明做结构化扩写；发布前仍可手动修改门槛和联系方式公开范围。",
    }


def _parse_roles(payload: dict) -> list[dict]:
    raw_roles = payload.get("roles")
    if isinstance(raw_roles, list) and raw_roles:
        roles = raw_roles
    else:
        roles = []
        roles_text = str(payload.get("roles_text", "")).strip()
        for index, chunk in enumerate(re.split(r"[;\n；]+", roles_text), start=1):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = [part.strip() for part in chunk.split(":")]
            name = parts[0] or f"方向{index}"
            try:
                needed = int(parts[1]) if len(parts) >= 2 and parts[1] else 1
            except ValueError:
                needed = 1
            skills = _split_words(parts[2]) if len(parts) >= 3 else []
            roles.append({"name": name, "needed": needed, "skills": skills, "direction": name})
    if not roles:
        roles = [{"name": "队友", "needed": 1, "skills": [], "direction": "综合协作"}]

    normalized = []
    for index, role in enumerate(roles, start=1):
        needed = max(1, int(role.get("needed") or 1))
        normalized.append(
            {
                "id": str(index),
                "name": str(role.get("name") or f"方向{index}"),
                "direction": str(role.get("direction") or role.get("name") or f"方向{index}"),
                "needed": needed,
                "filled": 0,
                "skills": role.get("skills") if isinstance(role.get("skills"), list) else _split_words(str(role.get("skills", ""))),
                "confirmed_members": [],
                "status": "招募中",
            }
        )
    return normalized


def _decorate_post(post: dict, profile: dict | None = None) -> dict:
    item = deepcopy(post)
    total_needed = sum(int(role.get("needed", 0)) for role in item.get("roles", []))
    total_filled = sum(int(role.get("filled", 0)) for role in item.get("roles", []))
    item["total_needed"] = total_needed
    item["total_filled"] = total_filled
    item["remaining"] = max(0, total_needed - total_filled)
    item["status"] = "已满员" if item["remaining"] == 0 else "招募中"
    item["is_publisher"] = user_id(profile) == item.get("publisher_id") if profile else False
    if profile:
        scores = []
        for role in item.get("roles", []):
            if int(role.get("filled", 0)) < int(role.get("needed", 0)):
                scores.append(evaluate_candidate(item, role, profile))
        best = max(scores, key=lambda value: value["score"], default=evaluate_candidate(item, None, profile))
        item["match_score"] = best["score"]
        item["match_reasons"] = best["reasons"]
        item["match_details"] = best["details"]
    return item


def list_posts(profile: dict | None = None) -> list[dict]:
    data = _load()
    posts = [_decorate_post(post, profile) for post in data.get("posts", [])]
    posts.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return posts


def get_post_detail(post_id: int | str, profile: dict | None = None) -> dict | None:
    data = _load()
    post = next((item for item in data.get("posts", []) if str(item.get("id")) == str(post_id)), None)
    return _decorate_post(post, profile) if post else None


def create_post(payload: dict) -> dict:
    profile = payload.get("profile") or {}
    ok, missing = profile_is_complete(profile)
    if not ok:
        return {"ok": False, "message": f"请先补全个人信息：{'、'.join(missing)}"}
    penalty = get_penalty(profile)
    if penalty:
        return {"ok": False, "message": f"账号处于组队限制期，截止 {penalty.get('until')}，暂不能发布招募"}

    data = _load()
    post_id = _next_id(data, "post")
    title = str(payload.get("title", "")).strip() or "队友招募"
    description = str(payload.get("description", "")).strip()
    roles = _parse_roles(payload)
    gates = payload.get("gates") or {}
    tags_text = str(payload.get("tags_text", "")).strip()

    post = {
        "id": post_id,
        "title": title,
        "contest_name": str(payload.get("contest_name", "")).strip(),
        "description": description,
        "tags_text": tags_text,
        "roles": roles,
        "gates": {
            "campuses": _gate_values(gates, "campuses"),
            "colleges": _gate_values(gates, "colleges"),
            "grades": _gate_values(gates, "grades"),
            "majors": _gate_values(gates, "majors"),
            "require_statement": bool(gates.get("require_statement")),
        },
        "publisher_id": user_id(profile),
        "publisher_profile": _public_profile(profile),
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["posts"].append(post)
    _save(data)
    return {"ok": True, "message": "招募已发布", "data": _decorate_post(post, profile)}


def apply_to_post(payload: dict) -> dict:
    profile = payload.get("profile") or {}
    ok, missing = profile_is_complete(profile)
    if not ok:
        return {"ok": False, "message": f"请先补全个人信息：{'、'.join(missing)}"}

    data = _load()
    post = next((item for item in data["posts"] if str(item.get("id")) == str(payload.get("post_id"))), None)
    if not post:
        return {"ok": False, "message": "招募不存在"}
    if post.get("publisher_id") == user_id(profile):
        return {"ok": False, "message": "不能申请自己发布的招募"}

    role = next((item for item in post.get("roles", []) if str(item.get("id")) == str(payload.get("role_id"))), None)
    if not role:
        return {"ok": False, "message": "岗位不存在"}
    if int(role.get("filled", 0)) >= int(role.get("needed", 0)):
        return {"ok": False, "message": "该方向已招满"}

    statement = str(payload.get("statement", "")).strip()
    evaluation = evaluate_candidate(post, role, profile, statement)
    if not evaluation["passed"]:
        return {"ok": False, "message": "暂不能发送申请：" + "；".join(evaluation["reasons"]), "evaluation": evaluation}

    applicant_id = user_id(profile)
    for item in data["applications"]:
        if (
            str(item.get("post_id")) == str(post["id"])
            and str(item.get("role_id")) == str(role["id"])
            and item.get("applicant_id") == applicant_id
            and item.get("status") in ("pending", "accepted")
        ):
            return {"ok": False, "message": "你已申请过该方向"}

    application = {
        "id": _next_id(data, "application"),
        "post_id": post["id"],
        "post_title": post["title"],
        "role_id": role["id"],
        "role_name": role["name"],
        "publisher_id": post["publisher_id"],
        "applicant_id": applicant_id,
        "applicant_profile": _public_profile(profile, include_experience=True),
        "statement": statement,
        "match_score": evaluation["score"],
        "score_detail": evaluation["details"],
        "gate_reasons": evaluation["reasons"],
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["applications"].append(application)
    _save(data)
    return {"ok": True, "message": "申请已发送", "data": application}


def decide_application(payload: dict) -> dict:
    profile = payload.get("profile") or {}
    data = _load()
    application = next((item for item in data["applications"] if str(item.get("id")) == str(payload.get("application_id"))), None)
    if not application:
        return {"ok": False, "message": "申请不存在"}
    if application.get("publisher_id") != user_id(profile):
        return {"ok": False, "message": "只有发布者可以处理申请"}
    if application.get("status") != "pending":
        return {"ok": False, "message": "该申请已处理"}

    decision = str(payload.get("decision", "reject")).lower()
    post = next((item for item in data["posts"] if str(item.get("id")) == str(application.get("post_id"))), None)
    role = None
    if post:
        role = next((item for item in post.get("roles", []) if str(item.get("id")) == str(application.get("role_id"))), None)

    if decision == "accept":
        if not post or not role:
            return {"ok": False, "message": "关联岗位不存在"}
        if int(role.get("filled", 0)) >= int(role.get("needed", 0)):
            application["status"] = "role_full"
            _save(data)
            return {"ok": False, "message": "该方向已满员"}
        application["status"] = "accepted"
        role["filled"] = int(role.get("filled", 0)) + 1
        role["confirmed_members"].append(
            {
                "application_id": application["id"],
                "user_id": application["applicant_id"],
                "profile": application["applicant_profile"],
                "joined_at": _now(),
            }
        )
        role["status"] = "已确定" if int(role["filled"]) >= int(role["needed"]) else "招募中"
        post["updated_at"] = _now()
        message = "已同意申请，岗位人数已同步更新"
    else:
        application["status"] = "rejected"
        message = "已拒绝申请"
    application["updated_at"] = _now()
    _save(data)
    return {"ok": True, "message": message, "data": application}


def get_user_recruitment(profile: dict | None) -> dict:
    uid = user_id(profile)
    data = _load()
    my_posts = [_decorate_post(post, profile) for post in data["posts"] if post.get("publisher_id") == uid]
    sent = [item for item in data["applications"] if item.get("applicant_id") == uid]
    received = [item for item in data["applications"] if item.get("publisher_id") == uid]
    accepted_ids = {item.get("post_id") for item in data["applications"] if item.get("applicant_id") == uid and item.get("status") == "accepted"}
    matched = [_decorate_post(post, profile) for post in data["posts"] if post.get("id") in accepted_ids or post.get("publisher_id") == uid]
    return {
        "my_posts": my_posts,
        "sent": sorted(sent, key=lambda item: item.get("created_at", ""), reverse=True),
        "received": sorted(received, key=lambda item: item.get("created_at", ""), reverse=True),
        "matched": matched,
        "penalty": get_penalty(profile),
    }


def _team_member_ids(post: dict) -> set[str]:
    ids = {post.get("publisher_id", "")}
    for role in post.get("roles", []):
        for member in role.get("confirmed_members", []):
            ids.add(member.get("user_id", ""))
    return {item for item in ids if item}


def request_unbind(payload: dict) -> dict:
    profile = payload.get("profile") or {}
    uid = user_id(profile)
    data = _load()
    post = next((item for item in data["posts"] if str(item.get("id")) == str(payload.get("post_id"))), None)
    if not post or uid not in _team_member_ids(post):
        return {"ok": False, "message": "只有已匹配成员可以发起解绑"}
    target_id = str(payload.get("target_user_id") or "").strip()
    if not target_id or target_id not in _team_member_ids(post):
        return {"ok": False, "message": "解绑对象不在队伍中"}

    existing = next(
        (
            item
            for item in data["unbind_requests"]
            if str(item.get("post_id")) == str(post["id"])
            and set(item.get("parties", [])) == {uid, target_id}
            and item.get("status") == "pending"
        ),
        None,
    )
    if existing:
        if uid not in existing["confirmed_by"]:
            existing["confirmed_by"].append(uid)
        if target_id in existing["confirmed_by"] and uid in existing["confirmed_by"]:
            existing["status"] = "completed"
            _remove_member_from_post(post, target_id)
            _mark_application_unbound(data, post["id"], target_id)
            message = "双方已确认，解绑完成"
        else:
            message = "已记录解绑确认，等待对方同意"
    else:
        existing = {
            "id": _next_id(data, "unbind"),
            "post_id": post["id"],
            "parties": [uid, target_id],
            "confirmed_by": [uid],
            "status": "pending",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data["unbind_requests"].append(existing)
        message = "解绑申请已发送，需对方同意"
    existing["updated_at"] = _now()
    _save(data)
    return {"ok": True, "message": message, "data": existing}


def _remove_member_from_post(post: dict, target_id: str) -> None:
    for role in post.get("roles", []):
        before = len(role.get("confirmed_members", []))
        role["confirmed_members"] = [member for member in role.get("confirmed_members", []) if member.get("user_id") != target_id]
        removed = before - len(role["confirmed_members"])
        if removed:
            role["filled"] = max(0, int(role.get("filled", 0)) - removed)
            role["status"] = "招募中"
    post["updated_at"] = _now()


def _mark_application_unbound(data: dict, post_id: int, target_id: str) -> None:
    for item in data["applications"]:
        if str(item.get("post_id")) == str(post_id) and item.get("applicant_id") == target_id and item.get("status") == "accepted":
            item["status"] = "unbound"
            item["updated_at"] = _now()


def complain_member(payload: dict) -> dict:
    profile = payload.get("profile") or {}
    uid = user_id(profile)
    target_id = str(payload.get("target_user_id") or "").strip()
    data = _load()
    post = next((item for item in data["posts"] if str(item.get("id")) == str(payload.get("post_id"))), None)
    if not post:
        return {"ok": False, "message": "队伍不存在"}
    members = _team_member_ids(post)
    if uid not in members or target_id not in members or uid == target_id:
        return {"ok": False, "message": "只有队伍成员可以投诉其他已匹配成员"}

    for item in data["complaints"]:
        if str(item.get("post_id")) == str(post["id"]) and item.get("target_id") == target_id and item.get("complainant_id") == uid:
            return {"ok": False, "message": "你已提交过投诉"}

    complaint = {
        "id": _next_id(data, "complaint"),
        "post_id": post["id"],
        "target_id": target_id,
        "complainant_id": uid,
        "reason": str(payload.get("reason", "")).strip(),
        "created_at": _now(),
    }
    data["complaints"].append(complaint)

    complainants = {
        item.get("complainant_id")
        for item in data["complaints"]
        if str(item.get("post_id")) == str(post["id"]) and item.get("target_id") == target_id
    }
    required = members - {target_id}
    if required and required.issubset(complainants):
        until = (_today() + dt.timedelta(days=30)).strftime("%Y-%m-%d")
        data["penalties"][target_id] = {
            "until": until,
            "reason": "已组队成员经其他成员一致投诉为消极怠工",
            "post_id": post["id"],
            "created_at": _now(),
        }
        message = f"投诉已达到全员一致，目标用户限制组队至 {until}"
    else:
        message = f"投诉已记录，还需 {len(required - complainants)} 名成员确认"

    _save(data)
    return {"ok": True, "message": message, "data": complaint}
