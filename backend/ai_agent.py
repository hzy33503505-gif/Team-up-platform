from __future__ import annotations

import datetime as dt
import re
from typing import Any

from contest_metrics import attach_metrics, get_contest_sections
from hit_directory import crawl_hit_mentors
from recruitment_store import get_user_recruitment, list_posts
from self_trained_model import MODEL_LABEL, answer_with_self_model
from user_store import get_my_contests


INTENT_LABELS = {
    "contest_recommend": "竞赛推荐",
    "contest_detail": "竞赛信息查询",
    "career_plan": "竞赛生涯规划",
    "team_match": "组队匹配",
    "mentor": "导师与课题组",
    "deadline": "报名提醒",
    "bonus": "竞赛加分",
    "material": "材料与答辩",
    "prestige": "含金量评估",
    "general": "综合咨询",
}


DOMAIN_TAGS = [
    "AI",
    "人工智能",
    "机器人",
    "机器视觉",
    "数学建模",
    "数模",
    "电子",
    "嵌入式",
    "创新创业",
    "互联网+",
    "挑战杯",
    "软件",
    "编程",
    "材料",
    "机械",
    "智能制造",
    "外语",
    "商业",
    "数据",
    "产品",
    "车辆",
    "海洋",
]


def _today_text() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def _date_value(value: str) -> dt.date | None:
    try:
        return dt.datetime.strptime(value or "", "%Y-%m-%d").date()
    except ValueError:
        return None


def _split_query(text: str) -> list[str]:
    words = [part.strip() for part in re.split(r"[\s，,。；;、/|：:（）()]+", text or "") if part.strip()]
    hits = [tag for tag in DOMAIN_TAGS if tag.lower() in text.lower()]
    return list(dict.fromkeys([*words, *hits]))


def _profile_terms(profile: dict) -> list[str]:
    terms = []
    for key in ("campus", "college", "major", "grade", "target"):
        if profile.get(key):
            terms.append(str(profile[key]))
    if isinstance(profile.get("interests"), list):
        terms.extend(str(item) for item in profile["interests"] if item)
    return list(dict.fromkeys(terms))


def detect_intent(question: str) -> str:
    text = question.lower()
    if any(word in question for word in ["导师", "课题组", "实验室", "研究方向", "老师"]):
        return "mentor"
    if any(word in question for word in ["组队", "队友", "招募", "申请", "匹配", "找人", "队伍", "团队", "成员", "靠谱", "避坑", "风险", "跑路", "放跑路", "投诉", "消极怠工", "解绑", "门槛"]):
        return "team_match"
    if any(word in question for word in ["规划", "路线", "生涯", "大学四年", "保研", "就业", "简历"]):
        return "career_plan"
    if any(word in question for word in ["截止", "报名时间", "提醒", "日程", "什么时候"]):
        return "deadline"
    if any(word in question for word in ["加分", "学分", "推免", "认定", "奖励"]):
        return "bonus"
    if any(word in question for word in ["材料", "方案", "答辩", "ppt", "报名表", "申报书", "计划书"]):
        return "material"
    if any(word in question for word in ["含金量", "竞赛价值", "主办单位", "参赛规模", "获奖比例", "获奖数量", "榜单", "排行榜", "行业认可"]):
        return "prestige"
    if any(word in question for word in ["推荐", "适合", "参加什么", "比赛", "竞赛"]):
        return "contest_recommend"
    if "代码" in question or "python" in text:
        return "material"
    return "general"


def is_greeting(question: str) -> bool:
    compact = re.sub(r"[\s，,。！!？?~～]+", "", question or "")
    return compact in {"你好", "您好", "hello", "hi", "嗨", "在吗", "在不在", "谢谢", "感谢"}


def _contest_score(item: dict, question: str, profile: dict) -> int:
    query_terms = _split_query(question)
    profile_terms = _profile_terms(profile)
    haystack = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("category", "")),
            str(item.get("tag", "")),
            str(item.get("desc", "")),
            str(item.get("conditions", "")),
            str(item.get("bonus_summary", "")),
            " ".join(str(word) for word in item.get("keywords", [])),
        ]
    ).lower()
    score = 0
    for term in query_terms:
        if term and term.lower() in haystack:
            score += 12
    for term in profile_terms:
        if term and term.lower() in haystack:
            score += 8
    if item.get("is_hit_recognized"):
        score += 10
    if item.get("status") == "报名中":
        score += 9
    if item.get("has_deadline"):
        score += 4
    score += min(int(item.get("click_count", 0) or 0), 8)
    major_text = " ".join(_profile_terms(profile) + _split_query(question)).lower()
    category = str(item.get("category", ""))
    name = str(item.get("name", ""))
    if any(word in major_text for word in ["ai", "人工智能", "计算机", "软件", "编程", "数据"]):
        if any(word in category + name for word in ["编程", "软件", "人工智能", "数学建模", "服务外包", "机器人", "智能制造", "电子", "挑战杯", "互联网"]):
            score += 18
        if any(word in category + name for word in ["外语", "建筑", "车辆", "海洋", "材料"]):
            score -= 12
    if any(word in major_text for word in ["材料", "焊接", "化学"]):
        if any(word in category + name for word in ["材料", "化学", "挑战杯", "互联网", "工程训练"]):
            score += 18
    if any(word in major_text for word in ["机器人", "机械", "智能制造", "自动化"]):
        if any(word in category + name for word in ["机器人", "机械", "智能制造", "电子", "工程训练", "西门子"]):
            score += 18
    return score


def retrieve_contests(question: str, profile: dict, contests: list[dict], limit: int = 6) -> list[dict]:
    enriched = attach_metrics(contests)
    ranked = sorted(enriched, key=lambda item: _contest_score(item, question, profile), reverse=True)
    return [item for item in ranked if _contest_score(item, question, profile) > 0][:limit] or ranked[:limit]


def retrieve_posts(question: str, profile: dict, limit: int = 4) -> list[dict]:
    terms = _split_query(question) + _profile_terms(profile)
    posts = list_posts(profile)

    def score(post: dict) -> int:
        haystack = " ".join(
            [
                str(post.get("title", "")),
                str(post.get("contest_name", "")),
                str(post.get("description", "")),
                str(post.get("tags_text", "")),
                " ".join(role.get("name", "") + " " + role.get("direction", "") for role in post.get("roles", [])),
            ]
        ).lower()
        value = sum(8 for term in terms if term and term.lower() in haystack)
        value += 10 if post.get("remaining", 0) else 0
        value += int(post.get("match_score", 0) or 0) // 10
        return value

    return sorted(posts, key=score, reverse=True)[:limit]


def retrieve_mentors(question: str, profile: dict, limit: int = 5) -> list[dict]:
    terms = _split_query(question) + _profile_terms(profile)
    mentors = crawl_hit_mentors(force_refresh=False).get("items", [])

    def score(mentor: dict) -> int:
        haystack = " ".join(
            [
                str(mentor.get("name", "")),
                str(mentor.get("campus", "")),
                str(mentor.get("college", "")),
                str(mentor.get("direction", "")),
                " ".join(str(tag) for tag in mentor.get("tags", [])),
            ]
        ).lower()
        return sum(8 for term in terms if term and term.lower() in haystack)

    ranked = sorted(mentors, key=score, reverse=True)
    return [item for item in ranked if score(item) > 0][:limit] or ranked[:limit]


def _contest_line(item: dict, index: int) -> str:
    deadline = item.get("deadline") or item.get("registration_end_time") or "暂无明确截止"
    status = item.get("status") or "待确认"
    bonus = item.get("bonus_summary") or "加分以学院和本科生院认定为准"
    return (
        f"{index}. {item.get('name')}（{item.get('category', '综合')}，{status}，截止：{deadline}）\n"
        f"   适合点：{item.get('fit') or item.get('conditions') or item.get('desc', '')[:70]}\n"
        f"   加分/价值：{bonus[:90]}\n"
        f"   官网：{item.get('official_link') or item.get('latest_notice_link') or '暂无'}"
    )


def _post_line(item: dict, index: int) -> str:
    roles = []
    for role in item.get("roles", []):
        remaining = max(0, int(role.get("needed", 0) or 0) - int(role.get("filled", 0) or 0))
        roles.append(f"{role.get('name')}还需{remaining}人")
    publisher = item.get("publisher_profile", {})
    return (
        f"{index}. {item.get('title')} / {item.get('contest_name') or '未填竞赛'}\n"
        f"   发布者：{publisher.get('name', '同学')}，学号：{publisher.get('studentId', '未公开')}\n"
        f"   岗位：{'；'.join(roles) or '未拆分'}\n"
        f"   当前适配度：{item.get('match_score', '需完善资料后计算')}"
    )


def _mentor_line(item: dict, index: int) -> str:
    contact = item.get("contact_email") or item.get("contact_phone") or "官方页未公开"
    return (
        f"{index}. {item.get('name')}（{item.get('campus')} / {item.get('college')} / {item.get('title')}）\n"
        f"   方向：{item.get('direction') or '官方页暂未提取'}\n"
        f"   联系：{contact}\n"
        f"   官方页：{item.get('homepage') or item.get('source_url') or '暂无'}"
    )


def build_context(question: str, profile: dict | None, contests: list[dict]) -> dict:
    profile = profile or {}
    sections = get_contest_sections(contests)
    relevant = retrieve_contests(question, profile, contests)
    return {
        "today": _today_text(),
        "profile": profile,
        "intent": detect_intent(question),
        "contests": relevant,
        "recent": sections.get("recent", [])[:5],
        "hot": sections.get("hot", [])[:5],
        "my_contests": get_my_contests()[:8],
        "posts": retrieve_posts(question, profile),
        "mentors": retrieve_mentors(question, profile),
        "my_recruitment": get_user_recruitment(profile) if profile.get("studentId") else {},
    }


def _profile_summary(profile: dict) -> str:
    if not profile:
        return "你还没有填写个人信息，建议先补齐校区、学院、专业、年级、意向和学分绩。"
    bits = [
        profile.get("grade"),
        profile.get("campus"),
        profile.get("college"),
        profile.get("major"),
    ]
    if profile.get("gpa"):
        bits.append(f"学分绩{profile.get('gpa')}")
    interests = profile.get("interests") if isinstance(profile.get("interests"), list) else []
    if interests:
        bits.append("意向：" + "、".join(interests[:4]))
    elif profile.get("target"):
        bits.append("意向：" + str(profile.get("target")))
    return "；".join(str(bit) for bit in bits if bit) or "个人信息尚不完整。"


def _deadline_answer(context: dict) -> str:
    today = dt.date.today()
    contests = []
    for item in context["my_contests"] or context["recent"]:
        deadline = _date_value(str(item.get("deadline", "")))
        if deadline:
            days = (deadline - today).days
            contests.append((days, item))
    contests.sort(key=lambda pair: pair[0])
    if not contests:
        return "我没有在你的“我的竞赛”或近期竞赛里找到明确截止时间。建议先把关注的竞赛加入“我的竞赛”，系统才能做报名提醒。"
    lines = ["按当前数据，优先关注这些截止节点："]
    for days, item in contests[:5]:
        status = "今天截止" if days == 0 else (f"{days}天后截止" if days > 0 else f"已截止{abs(days)}天")
        lines.append(f"- {item.get('name')}：{status}，截止日期 {item.get('deadline')}")
    lines.append("建议：截止前至少预留2天检查报名资格、队伍信息、材料命名和校内备案。")
    return "\n".join(lines)


def _career_plan_answer(context: dict) -> str:
    profile = context["profile"]
    grade = profile.get("grade", "")
    contests = context["contests"][:3]
    stage = "当前阶段"
    if grade in ("大一", "大二"):
        stage = "打基础和试错阶段"
    elif grade in ("大三", "研一"):
        stage = "冲成果和沉淀作品阶段"
    elif grade in ("大四", "研二", "研三", "博士"):
        stage = "成果收口和简历证明阶段"

    lines = [
        f"基于你的资料：{_profile_summary(profile)}",
        f"我建议把竞赛规划定为：{stage}。",
        "",
        "1. 近期1个月：选1个主赛道，不要同时铺太多。先确认报名截止、参赛资格、队伍人数和加分认定。",
        "2. 1-3个月：围绕主赛道补齐一个可展示作品，至少形成代码/实验记录/调研文档/PPT中的两类材料。",
        "3. 3-6个月：冲一次高价值比赛，同时保留校内报名、获奖证书、队伍贡献证明，方便后续学分绩、推免或简历使用。",
    ]
    if contests:
        lines.append("")
        lines.append("可以优先考虑：")
        lines.extend(_contest_line(item, idx) for idx, item in enumerate(contests, start=1))
    lines.append("")
    lines.append("匹配建议：先在“匹配-招募大厅”找已有队伍；如果没有合适岗位，就发布招募并写清楚目标竞赛、缺口角色和每周投入时间。")
    return "\n".join(lines)


TEAM_JUDGEMENT_WORDS = [
    "靠谱",
    "可靠",
    "判断",
    "辨别",
    "避坑",
    "风险",
    "跑路",
    "消极",
    "怠工",
    "划水",
    "退出",
    "解绑",
    "投诉",
    "怎么选",
    "如何选",
    "是否值得",
]


def _is_team_judgement_question(question: str) -> bool:
    return any(word in (question or "") for word in TEAM_JUDGEMENT_WORDS)


def _team_answer(context: dict, question: str = "") -> str:
    if _is_team_judgement_question(question):
        lines = [
            "判断一个队伍是否靠谱，建议不要只看匹配分数，而是看“目标、分工、投入、沟通、记录、退出机制”六件事：",
            "",
            "1. 目标是否一致：确认大家是想练手、冲校奖、省奖，还是冲国奖；目标差太多后期最容易分裂。",
            "2. 分工是否具体：靠谱队伍会写清楚缺什么角色、每个角色交付什么，而不是只说“缺技术/缺文书”。",
            "3. 时间投入是否可验证：询问每周可投入时间、近期课程/考试压力、是否能参加固定例会。",
            "4. 已有基础是否真实：看是否有项目文档、代码仓库、调研记录、往届作品或初版方案，而不是只有口头想法。",
            "5. 沟通是否稳定：观察发布者回复速度、表达是否清楚、是否愿意把规则、材料和时间节点公开给所有成员。",
            "6. 风险机制是否提前说清：包括任务延期怎么办、队友退出怎么办、成果署名和材料提交由谁负责。",
            "",
            "在小程序里建议你优先看：发布者学号和资料是否完整、岗位需求是否明确、申请门槛是否合理、队伍剩余人数是否真实变化、是否愿意让你写申请说明并沟通细节。",
        ]
        posts = context.get("posts") or []
        if posts:
            lines.append("")
            lines.append("如果要结合当前招募判断，可以重点追问这些队伍：")
            lines.extend(_post_line(item, idx) for idx, item in enumerate(posts[:3], start=1))
        lines.append("")
        lines.append("比较稳妥的做法：申请前先问一句“我们每周怎么同步进度、每个人最近两周交付什么、如果有人掉线怎么处理”。能清楚回答的队伍通常更可靠。")
        return "\n".join(lines)

    posts = context["posts"]
    lines = [
        "队伍匹配不是靠一次测评分数决定，而是按“发布者门槛 -> 你的资料 -> 岗位关键词 -> 申请说明”形成适配度。",
        f"你的资料概况：{_profile_summary(context['profile'])}",
    ]
    if posts:
        lines.append("")
        lines.append("当前可关注的招募：")
        lines.extend(_post_line(item, idx) for idx, item in enumerate(posts, start=1))
    else:
        lines.append("")
        lines.append("当前没有合适招募。你可以自己发布招募，至少写清：目标竞赛、已有成员、缺少角色、每周投入、是否限制学院/年级。")
    lines.append("")
    lines.append("申请建议：申请说明用三句话即可：我会什么、做过什么、每周能投入多久。")
    return "\n".join(lines)


def _mentor_answer(context: dict) -> str:
    mentors = context["mentors"]
    if not mentors:
        return "导师库暂时没有可用数据。可以先点击导师库刷新，系统会从哈工大三个校区官方页面抓取导师方向和联系方式。"
    lines = [
        "导师选择建议：先看研究方向是否能支撑你的竞赛作品，再看是否有课题组资源和可沟通的联系方式。",
        "",
        "当前匹配到的官方导师信息：",
    ]
    lines.extend(_mentor_line(item, idx) for idx, item in enumerate(mentors[:5], start=1))
    lines.append("")
    lines.append("联系前建议准备：个人简介、目标竞赛、已有基础、希望导师帮助的问题、可投入时间。")
    return "\n".join(lines)


def _material_answer(context: dict, question: str) -> str:
    contests = context["contests"][:2]
    lines = [
        "材料准备可以按“目标-规则-分工-证据-风险”来写，不要只写想法。",
        "",
        "通用模板：",
        "1. 项目目标：解决什么问题，面向哪个竞赛赛题或赛道。",
        "2. 技术/方案路线：核心方法、工具、实验或数据来源。",
        "3. 队伍分工：每个人负责的模块和交付物。",
        "4. 时间表：报名、初稿、测试、答辩、提交节点。",
        "5. 风险检查：资格、材料格式、原创性、数据来源、校内备案。",
    ]
    if contests:
        lines.append("")
        lines.append("结合你问题里相关的竞赛，先核对：")
        for item in contests:
            lines.append(f"- {item.get('name')}：材料 {('、'.join(item.get('materials', [])) or '以官网为准')}；条件：{item.get('conditions', '以官网为准')[:80]}")
    return "\n".join(lines)


def _contest_answer(context: dict) -> str:
    contests = context["contests"]
    if not contests:
        return "我暂时没有找到匹配的竞赛。可以补充你的专业、年级、意向方向，或换成具体关键词，例如“机器人”“数模”“材料实验”。"
    lines = [
        f"基于你的资料：{_profile_summary(context['profile'])}",
        "我优先推荐这些竞赛：",
    ]
    lines.extend(_contest_line(item, idx) for idx, item in enumerate(contests[:5], start=1))
    lines.append("")
    lines.append("下一步：把最想参加的1-2个加入“我的竞赛”，再去匹配页找队伍或发布招募。")
    return "\n".join(lines)


def local_answer(question: str, context: dict) -> str:
    intent = context["intent"]
    if intent == "deadline":
        return _deadline_answer(context)
    if intent == "career_plan":
        return _career_plan_answer(context)
    if intent == "team_match":
        return _team_answer(context, question)
    if intent == "mentor":
        return _mentor_answer(context)
    if intent == "material":
        return _material_answer(context, question)
    if intent in ("contest_recommend", "contest_detail", "general"):
        return _contest_answer(context)
    return _contest_answer(context)


def _compact_contest(item: dict) -> dict:
    return {
        "name": item.get("name"),
        "category": item.get("category"),
        "deadline": item.get("deadline"),
        "status": item.get("status"),
        "conditions": str(item.get("conditions", ""))[:160],
        "bonus": str(item.get("bonus_summary", ""))[:160],
        "official_link": item.get("official_link") or item.get("latest_notice_link"),
    }


def _compact_post(item: dict) -> dict:
    return {
        "title": item.get("title"),
        "contest_name": item.get("contest_name"),
        "remaining": item.get("remaining"),
        "match_score": item.get("match_score"),
    }


def _compact_mentor(item: dict) -> dict:
    return {
        "name": item.get("name"),
        "campus": item.get("campus"),
        "college": item.get("college"),
        "direction": item.get("direction"),
        "contact": item.get("contact_email") or item.get("contact_phone"),
        "homepage": item.get("homepage") or item.get("source_url"),
    }


COMPLEX_QUESTION_WORDS = [
    "详细",
    "深入",
    "完整",
    "综合",
    "分析",
    "比较",
    "评估",
    "规划",
    "路线",
    "策略",
    "方案",
    "生成",
    "撰写",
    "润色",
    "模板",
    "怎么",
    "如何",
    "判断",
    "为什么",
    "如果",
    "能否",
    "优缺点",
    "风险",
    "答辩",
    "商业计划书",
]

UNCERTAIN_ANSWER_WORDS = [
    "暂时没有",
    "没有找到",
    "未找到",
    "未提取",
    "待确认",
    "待官网",
    "以官网通知为准",
    "暂无明确",
    "不确定",
]


OPEN_GUIDANCE_INTENTS = {"team_match", "career_plan", "material", "mentor", "prestige"}


def _needs_cloud_reason(question: str, intent: str) -> str:
    question = question or ""
    if intent == "team_match" and _is_team_judgement_question(question):
        return "队伍可靠性/避坑判断需要开放式推理，必须使用 DeepSeek 云端增强"
    if intent in OPEN_GUIDANCE_INTENTS and any(word in question for word in COMPLEX_QUESTION_WORDS):
        return "问题需要开放式推理和表达增强"
    if len(question) >= 36 and any(word in question for word in COMPLEX_QUESTION_WORDS):
        return "问题较长且包含复杂任务"
    return ""


def _self_answer_is_contest_dump(answer_text: str, intent: str) -> bool:
    if intent not in OPEN_GUIDANCE_INTENTS | {"general"}:
        return False
    text = answer_text or ""
    contest_like = any(word in text for word in ["属于", "报名截止", "官网：", "竞赛章程", "参赛规则"])
    guidance_like = any(word in text for word in ["建议", "判断", "步骤", "风险", "清单", "分工", "投入"])
    return contest_like and not guidance_like


def should_use_cloud(question: str, context: dict, self_answer: dict[str, Any] | None) -> tuple[bool, str]:
    question = question or ""
    answer_text = str((self_answer or {}).get("answer", ""))
    confidence = float((self_answer or {}).get("confidence", 0) or 0)
    intent = context.get("intent", "general")

    if not self_answer:
        return True, "自训练模型没有形成可用答案"
    cloud_reason = _needs_cloud_reason(question, intent)
    if cloud_reason:
        return True, cloud_reason
    if confidence < 0.32:
        return True, f"自训练模型置信度较低（{confidence:.2f}）"
    if _self_answer_is_contest_dump(answer_text, intent):
        return True, "自训练答案疑似错把开放式问题路由到具体竞赛条目"
    if any(word in answer_text for word in UNCERTAIN_ANSWER_WORDS) and confidence < 0.55:
        return True, "自训练答案存在不确定信息"
    return False, "自训练模型置信度充足"


def answer_with_model(
    client: Any,
    question: str,
    context: dict,
    model: str,
    self_answer: dict[str, Any] | None = None,
    route_reason: str = "",
) -> str:
    system = (
        "你是“智竞工大”微信小程序里的竞赛智能体。"
        "你只能围绕大学生竞赛、哈工大竞赛加分、队伍匹配、导师方向、材料准备和竞赛生涯规划回答。"
        "回答必须优先基于给定上下文和自训练模型初稿；可用常识补充方法论，但不得编造官网日期、报名条件、导师联系方式或加分政策。"
        "如果上下文没有某项官方信息，必须明确说“当前未从官网提取到”，再给用户核验路径。"
        "输出中文，结构清晰，给出可执行建议。"
    )
    data = {
        "today": context["today"],
        "profile": context["profile"],
        "intent": INTENT_LABELS.get(context["intent"], context["intent"]),
        "route_reason": route_reason,
        "self_trained_draft": (self_answer or {}).get("answer", ""),
        "self_trained_confidence": (self_answer or {}).get("confidence", 0),
        "contests": [_compact_contest(item) for item in context["contests"][:6]],
        "recent": [_compact_contest(item) for item in context["recent"][:4]],
        "hot": [_compact_contest(item) for item in context["hot"][:4]],
        "my_contests": [_compact_contest(item) for item in context["my_contests"][:5]],
        "posts": [_compact_post(item) for item in context["posts"][:4]],
        "mentors": [_compact_mentor(item) for item in context["mentors"][:5]],
    }
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": f"上下文：{data}\n\n用户问题：{question}"},
        ],
        temperature=0.45,
    )
    return completion.choices[0].message.content


def build_sources(context: dict) -> list[dict]:
    sources = []
    for item in context["contests"][:3]:
        sources.append(
            {
                "type": "contest",
                "title": item.get("name", "竞赛"),
                "subtitle": f"{item.get('status', '')} / 截止 {item.get('deadline') or '待确认'}",
                "url": item.get("official_link") or item.get("latest_notice_link") or "",
            }
        )
    for item in context["posts"][:2]:
        sources.append(
            {
                "type": "post",
                "title": item.get("title", "队伍招募"),
                "subtitle": f"{item.get('contest_name') or '目标竞赛待补充'} / 剩余 {item.get('remaining', 0)} 人",
                "url": "",
            }
        )
    for item in context["mentors"][:2]:
        sources.append(
            {
                "type": "mentor",
                "title": item.get("name", "导师"),
                "subtitle": f"{item.get('campus', '')} / {item.get('college', '')}",
                "url": item.get("homepage") or item.get("source_url") or "",
            }
        )
    return sources[:6]


def build_suggestions(intent: str) -> list[str]:
    mapping = {
        "contest_recommend": ["帮我把这些竞赛排个优先级", "根据我的年级做三个月备赛计划", "帮我找适合的队友招募"],
        "deadline": ["哪些竞赛本周最紧急", "帮我列报名材料清单", "如何设置我的竞赛提醒"],
        "team_match": ["帮我写一段申请说明", "帮我润色招募帖", "怎么判断一个队伍是否靠谱"],
        "mentor": ["帮我写联系导师的话术", "哪些导师方向适合AI竞赛", "导师沟通前要准备什么"],
        "career_plan": ["按保研目标规划竞赛路线", "按就业目标规划项目经历", "大一应该先打哪些比赛"],
        "bonus": ["哪些竞赛校内认定价值高", "帮我比较两个竞赛加分", "推免加分材料要保留什么"],
        "material": ["帮我生成答辩提纲", "帮我检查报名材料风险", "帮我写项目计划书结构"],
        "prestige": ["含金量最高的竞赛有哪些", "这个比赛主办单位靠谱吗", "哪些竞赛适合保研加分"],
    }
    return mapping.get(intent, ["帮我推荐竞赛", "帮我做竞赛规划", "帮我找队友"])


def answer_question(
    question: str,
    profile: dict | None,
    contests: list[dict],
    client: Any = None,
    model: str = "deepseek-v4-flash",
    provider_label: str = "DeepSeek V4 云端增强",
) -> dict:
    question = (question or "").strip()
    if not question:
        return {"answer": "你还没有输入问题。", "intent": "general", "sources": [], "suggestions": build_suggestions("general")}
    if is_greeting(question):
        return {
            "answer": "你好，我是智竞工大竞赛智能体。你可以问我竞赛报名截止、校内认定加分、队伍是否靠谱、招募申请怎么写、导师方向匹配或竞赛规划。我会先用自训练模型检索，复杂问题会自动用 DeepSeek V4 增强。",
            "intent": "general",
            "intent_label": "综合咨询",
            "mode": "self_trained_fallback",
            "provider": "自训练竞赛模型",
            "model": "",
            "confidence": 1,
            "route_reason": "问候语直接回复",
            "sources": [],
            "suggestions": build_suggestions("general"),
        }

    context = build_context(question, profile or {}, contests)
    self_answer = answer_with_self_model(
        question,
        profile or {},
        contests,
        intent=context["intent"],
        context=context,
    )
    use_cloud, route_reason = should_use_cloud(question, context, self_answer)
    if self_answer and not use_cloud:
        return {
            "answer": self_answer["answer"],
            "intent": context["intent"],
            "intent_label": INTENT_LABELS.get(context["intent"], "综合咨询"),
            "mode": "self_trained",
            "provider": self_answer["provider"],
            "model": self_answer["model"],
            "confidence": self_answer["confidence"],
            "route_reason": route_reason,
            "sources": self_answer.get("sources") or build_sources(context),
            "suggestions": build_suggestions(context["intent"]),
        }

    mode = "self_trained_fallback"
    try:
        if client:
            answer = answer_with_model(client, question, context, model, self_answer=self_answer, route_reason=route_reason)
            mode = "self_trained_cloud"
        elif self_answer:
            if (
                route_reason.startswith("自训练模型置信度较低")
                or "开放式" in route_reason
                or "错把开放式问题" in route_reason
                or context["intent"] in OPEN_GUIDANCE_INTENTS
            ):
                answer = (
                    f"{local_answer(question, context)}\n\n"
                    f"注：该问题已触发云端增强条件（{route_reason}），但 DeepSeek V4 当前不可用，已使用本地规则模板兜底，未采用低置信度竞赛条目硬答。"
                )
            else:
                answer = (
                    f"{self_answer['answer']}\n\n"
                    f"注：该问题已触发云端增强条件（{route_reason}），但 DeepSeek V4 当前不可用，已返回自训练模型结果。"
                )
            mode = "self_trained_fallback"
        else:
            answer = local_answer(question, context)
            mode = "self_trained_fallback"
    except Exception as exc:
        if "开放式" in route_reason or "错把开放式问题" in route_reason or context["intent"] in OPEN_GUIDANCE_INTENTS:
            fallback = local_answer(question, context)
        else:
            fallback = self_answer["answer"] if self_answer else local_answer(question, context)
        answer = f"{fallback}\n\n注：DeepSeek V4 云端增强调用失败，以上为自训练竞赛模型和本地检索规则生成的回答。错误信息：{exc}"
        mode = "self_trained_fallback"

    return {
        "answer": answer,
        "intent": context["intent"],
        "intent_label": INTENT_LABELS.get(context["intent"], "综合咨询"),
        "mode": mode,
        "provider": f"{MODEL_LABEL} + {provider_label}" if client and mode == "self_trained_cloud" else ("自训练竞赛模型" if not client else provider_label),
        "model": model if client else "",
        "confidence": (self_answer or {}).get("confidence", 0),
        "route_reason": route_reason,
        "sources": build_sources(context),
        "suggestions": build_suggestions(context["intent"]),
    }
