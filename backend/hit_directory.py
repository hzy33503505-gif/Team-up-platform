from __future__ import annotations

import datetime as dt
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ADMISSION_URL = "https://zsb.hit.edu.cn/article/read/d1204b286bff12cb83f433f67a32c8c6"
HIT_ORG_URL = "https://www.hit.edu.cn/zzjg/list.htm"
HIT_WH_COLLEGE_URL = "https://www.hitwh.edu.cn/6111/list.htm"
HIT_WH_ADMISSION_MAJOR_URL = "https://zsb.hitwh.edu.cn/home/major/index"
HIT_SZ_URL = "https://www.hitsz.edu.cn"
HIT_HOMEPAGE_BASE = "https://homepage.hit.edu.cn"
HIT_HOMEPAGE_DEPT_URL = f"{HIT_HOMEPAGE_BASE}/sysBrowseShow"
MENTOR_CACHE = DATA_DIR / "hit_mentor_cache.json"
CUSTOM_COLLEGE = "其他学院（自定义）"
CUSTOM_MAJOR = "其他专业（自定义）"
CUSTOM_CAMPUS = "其他校区（自定义）"


OFFICIAL_SOURCES = [
    {
        "name": "哈尔滨工业大学招生办 2025年本科招生专业",
        "url": ADMISSION_URL,
        "usage": "三校区招生专业、学院归属与校区区分",
    },
    {
        "name": "哈尔滨工业大学组织机构",
        "url": HIT_ORG_URL,
        "usage": "校本部学院与院系入口",
    },
    {
        "name": "哈尔滨工业大学（威海）学院设置",
        "url": HIT_WH_COLLEGE_URL,
        "usage": "威海校区学院入口",
    },
    {
        "name": "哈尔滨工业大学（威海）本科招生专业",
        "url": HIT_WH_ADMISSION_MAJOR_URL,
        "usage": "威海校区紫丁香书院与招生专业核对",
    },
    {
        "name": "哈尔滨工业大学（深圳）官网",
        "url": HIT_SZ_URL,
        "usage": "深圳校区学院与教师入口",
    },
]

HIT_HOMEPAGE_CAMPUS_SOURCES = [
    {
        "name": "哈尔滨校区",
        "root_id": "1",
        "campus_id": "",
        "dept_endpoint": "executeBrowseAllOfSchoolDepart.do",
    },
    {
        "name": "威海校区",
        "root_id": "2",
        "campus_id": "999950",
        "dept_endpoint": "executeBrowseAllOfSchoolDepartWh.do",
    },
    {
        "name": "深圳校区",
        "root_id": "3",
        "campus_id": "999960",
        "dept_endpoint": "executeBrowseAllOfSchoolDepartSz.do",
    },
    {
        "name": "地方研究院",
        "root_id": "4",
        "campus_id": "999970",
        "dept_endpoint": "executeBrowseAllOfSchoolDepartYjy.do",
    },
]


ACADEMIC_OPTIONS = [
    {
        "name": "哈尔滨校区",
        "colleges": [
            {
                "name": "未来技术学院",
                "majors": [
                    "自动化",
                    "人工智能",
                    "计算机科学与技术",
                    "通信工程",
                    "电子信息工程",
                    "飞行器设计与工程",
                    "机器人工程",
                    "焊接技术与工程",
                    "电气工程及其自动化",
                    "复合材料与工程",
                    "智能材料与结构",
                    "集成电路设计与集成系统",
                    "微电子科学与工程",
                    "智能视觉工程",
                    "探测制导与控制技术",
                    "智能装备与系统",
                    "信息对抗技术",
                    "智能科学与技术",
                    "机械设计制造及其自动化",
                    "飞行器制造工程",
                    "智能制造工程",
                    "仿生科学与工程",
                    "光电信息材料与器件",
                    "飞行器动力工程",
                    "精密仪器",
                    "智能感知工程",
                    "测控技术与仪器",
                    "建筑学",
                    "城乡规划",
                    "软件工程",
                ],
            },
            {"name": "航天学院", "majors": ["自动化", "工程力学", "智能装备与系统", "复合材料与工程"]},
            {"name": "电子与信息工程学院", "majors": ["通信工程", "电子信息工程", "信息对抗技术"]},
            {"name": "电气工程及自动化学院", "majors": ["电气工程及其自动化", "能源互联网工程"]},
            {"name": "计算学部", "majors": ["计算机科学与技术", "人工智能", "信息安全", "软件工程"]},
            {
                "name": "机电工程学院",
                "majors": ["机械设计制造及其自动化", "飞行器制造工程", "机器人工程", "智能制造工程", "仿生科学与工程"],
            },
            {
                "name": "材料科学与工程学院",
                "majors": ["材料科学与工程", "材料成型及控制工程", "焊接技术与工程", "光电信息材料与器件", "电子封装技术"],
            },
            {"name": "能源科学与工程学院", "majors": ["能源与动力工程", "飞行器动力工程", "核工程与核技术", "储能科学与工程"]},
            {"name": "仪器科学与工程学院", "majors": ["精密仪器", "智能感知工程", "测控技术与仪器"]},
            {"name": "土木工程学院", "majors": ["土木工程", "城市地下空间工程", "智能建造"]},
            {"name": "环境学院", "majors": ["环境工程", "环境科学", "给排水科学与工程", "城市水系统工程"]},
            {"name": "建筑与设计学院", "majors": ["建筑环境与能源应用工程", "建筑学", "城乡规划", "数字媒体艺术", "产品设计"]},
            {"name": "交通科学与工程学院", "majors": ["道路桥梁与渡河工程", "交通工程", "智慧交通"]},
            {"name": "化工与化学学院", "majors": ["化学工程与工艺", "高分子材料与工程", "应用化学", "化学"]},
            {"name": "经济与管理学院", "majors": ["信息管理与信息系统", "大数据管理与应用", "计算金融", "数字经济", "工商管理", "会计学"]},
            {"name": "生命科学和医学学部", "majors": ["生物技术", "生物工程", "生物信息学", "智能医学工程"]},
            {"name": "数学学院", "majors": ["统计学", "数学与应用数学", "信息与计算科学"]},
            {"name": "物理学院", "majors": ["应用物理学"]},
            {"name": "人文社科学部", "majors": ["社会学", "法学", "国际组织与全球治理", "俄语"]},
        ],
    },
    {
        "name": "威海校区",
        "colleges": [
            {
                "name": "紫丁香书院",
                "majors": [
                    "工科试验班（机器人与智能装备拔尖班）",
                    "机械设计制造及其自动化",
                    "飞行器制造工程",
                    "机器人工程",
                    "智能制造工程",
                    "仿生科学与工程",
                    "材料科学与工程",
                    "材料成型及控制工程",
                    "焊接技术与工程",
                    "光电信息材料与器件",
                    "电子封装技术",
                    "能源与动力工程",
                    "飞行器动力工程",
                    "核工程与核技术",
                    "储能科学与工程",
                    "精密仪器",
                    "智能感知工程",
                    "测控技术与仪器",
                ],
            },
            {"name": "计算机科学与技术学院", "majors": ["计算机科学与技术", "人工智能", "网络空间安全", "软件工程"]},
            {"name": "信息科学与工程学院", "majors": ["自动化", "通信工程", "电子信息工程", "集成电路设计与集成系统", "测控技术与仪器"]},
            {"name": "理学院", "majors": ["光电信息科学与工程", "数学与应用数学", "信息与计算科学"]},
            {"name": "新能源学院", "majors": ["电气工程及其自动化", "储能科学与工程"]},
            {"name": "经济管理学院", "majors": ["会计学", "大数据管理与应用", "信息管理与信息系统"]},
            {"name": "海洋工程学院", "majors": ["机器人工程", "机械设计制造及其自动化", "土木工程", "船舶与海洋工程"]},
            {"name": "材料科学与工程学院", "majors": ["材料科学与工程", "材料成型及控制工程", "焊接技术与工程"]},
            {"name": "汽车工程学院", "majors": ["车辆工程", "交通工程"]},
            {"name": "海洋科学与技术学院", "majors": ["环境工程", "生物工程", "化学工程与工艺"]},
        ],
    },
    {
        "name": "深圳校区",
        "colleges": [
            {"name": "计算机科学与技术学院", "majors": ["计算机科学与技术"]},
            {"name": "信息科学与技术学院", "majors": ["通信工程"]},
            {"name": "集成电路学院", "majors": ["集成电路设计与集成系统"]},
            {"name": "智能科学与工程学院", "majors": ["自动化"]},
            {"name": "机器人与先进制造学院", "majors": ["电气工程及其自动化", "能源与动力工程", "机器人工程"]},
            {"name": "材料科学与工程学院", "majors": ["材料科学与工程"]},
            {"name": "智能土木与海洋工程学院", "majors": ["土木工程"]},
            {"name": "生态环境学院", "majors": ["环境工程"]},
            {"name": "理学院", "majors": ["化学"]},
            {"name": "经济管理学院", "majors": ["会计学"]},
            {"name": "建筑学院", "majors": ["建筑学", "城乡规划"]},
            {"name": "未来设计学院", "majors": ["数字媒体艺术"]},
        ],
    },
]


def _with_custom_options() -> list[dict]:
    campuses = deepcopy_json(ACADEMIC_OPTIONS)
    for campus in campuses:
        colleges = campus.setdefault("colleges", [])
        for college in colleges:
            majors = college.setdefault("majors", [])
            if CUSTOM_MAJOR not in majors:
                majors.append(CUSTOM_MAJOR)
        if not any(college.get("name") == CUSTOM_COLLEGE for college in colleges):
            colleges.append({"name": CUSTOM_COLLEGE, "majors": [CUSTOM_MAJOR]})
    campuses.append({"name": CUSTOM_CAMPUS, "colleges": [{"name": CUSTOM_COLLEGE, "majors": [CUSTOM_MAJOR]}]})
    return campuses


def deepcopy_json(value):
    return json.loads(json.dumps(value, ensure_ascii=False))


PROFILE_SOURCES = [
    {"campus": "哈尔滨校区", "college": "机电工程学院", "url": "https://homepage.hit.edu.cn/tianlongli"},
    {"campus": "哈尔滨校区", "college": "能源科学与工程学院", "url": "https://homepage.hit.edu.cn/zhc"},
    {"campus": "深圳校区", "college": "人文与社会科学学院", "url": "https://faculty.hitsz.edu.cn/bixin"},
    {"campus": "深圳校区", "college": "材料科学与工程学院", "url": "https://faculty.hitsz.edu.cn/miaozibo"},
    {"campus": "深圳校区", "college": "建筑学院", "url": "https://faculty.hitsz.edu.cn/cuiaijiao"},
]


LIST_SOURCES = [
    {
        "campus": "威海校区",
        "college": "计算机科学与技术学院",
        "url": "https://cst.hitwh.edu.cn/344/list.htm",
    }
]


def _now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _fetch(url: str, timeout: int = 16) -> str:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    for encoding in ("utf-8", "gb18030"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def _post_json(url: str, payload: dict[str, Any], timeout: int = 20) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(payload).encode("utf-8"),
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Accept": "application/json, text/javascript, */*; q=0.01",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
    return json.loads(raw.decode("utf-8", errors="ignore"))


def _html_lines(markup: str) -> list[str]:
    markup = re.sub(r"<script[\s\S]*?</script>", "\n", markup, flags=re.I)
    markup = re.sub(r"<style[\s\S]*?</style>", "\n", markup, flags=re.I)
    text = re.sub(r"<[^>]+>", "\n", markup)
    text = html.unescape(text)
    return [line.strip() for line in text.splitlines() if line.strip()]


KNOWN_LABELS = {
    "目前就职",
    "学科",
    "研究方向",
    "主页地址",
    "复制地址",
    "更新日期",
    "人气",
    "联系方式",
    "电话",
    "传真",
    "邮箱",
    "地址",
    "学术网络",
}


def _line_after(lines: list[str], label: str) -> str:
    for index, line in enumerate(lines):
        if line == label and index + 1 < len(lines):
            value = lines[index + 1]
            return "" if value in KNOWN_LABELS else value
    return ""


def _normal_email(value: str) -> str:
    value = value.strip()
    if "@" not in value:
        return ""
    local = value.split("@", 1)[0]
    if "nc.ude.tih" in value or local.startswith(("nc.", "moc.", "ude.")):
        return value[::-1]
    return value


def _mentor_id(source: str, name: str) -> str:
    digest = hashlib.sha1(f"{source}:{name}".encode("utf-8")).hexdigest()[:10]
    return f"mentor-{digest}"


def _tags_from_direction(direction: str, college: str) -> list[str]:
    vocab = [
        "人工智能",
        "机器学习",
        "深度学习",
        "计算机视觉",
        "机器人",
        "机器视觉",
        "控制",
        "材料",
        "能源",
        "热处理",
        "结构",
        "建筑",
        "规划",
        "电子",
        "通信",
        "嵌入式",
        "网络安全",
        "数据挖掘",
        "物联网",
        "仿真",
        "实验",
    ]
    tags = [word for word in vocab if word in direction or word in college]
    if not tags and direction:
        tags = re.split(r"[，,；;、\s]+", direction)[:3]
    return [tag for tag in tags if tag][:6]


def _parse_profile(source: dict, markup: str) -> dict | None:
    lines = _html_lines(markup)
    title_match = re.search(r"<title>(.*?)</title>", markup, flags=re.I | re.S)
    page_title = html.unescape(title_match.group(1)).strip() if title_match else ""
    name = page_title.split(" - ")[0].strip() if " - " in page_title else ""
    if not name:
        for line in lines[:20]:
            if 2 <= len(line) <= 5 and not re.search(r"[a-zA-Z0-9]", line):
                name = line
                break
    if not name:
        return None

    college = _line_after(lines, "目前就职") or source.get("college", "")
    direction = _line_after(lines, "研究方向")
    homepage = _line_after(lines, "主页地址") or source["url"]
    phone = _line_after(lines, "电话")
    email_value = _line_after(lines, "邮箱")
    email = _normal_email(email_value)
    address = _line_after(lines, "地址")

    title = ""
    for line in lines:
        if line in ("教授", "副教授", "讲师", "研究员", "副研究员", "助理教授"):
            title = line
            break
    if "博士生导师" in lines:
        title = f"{title} / 博士生导师" if title else "博士生导师"
    elif "硕士生导师" in lines:
        title = f"{title} / 硕士生导师" if title else "硕士生导师"

    return {
        "id": _mentor_id(source["url"], name),
        "type": "mentor",
        "name": name,
        "title": title or "教师",
        "campus": source["campus"],
        "college": college,
        "department": "",
        "direction": direction,
        "requirements": "请以导师主页、学院通知或课题组公告为准，联系前建议准备竞赛方向、个人技能与可投入时间。",
        "contact_email": email,
        "contact_phone": phone,
        "address": address,
        "homepage": homepage,
        "source_url": source["url"],
        "source_name": "哈工大教师个人主页",
        "tags": _tags_from_direction(direction, college),
        "updated_at": _now(),
    }


def _parse_weihai_teacher_list(source: dict, markup: str, limit: int = 24) -> list[dict]:
    lines = _html_lines(markup)
    mentors: list[dict] = []
    try:
        start = lines.index("电子邮箱") + 1
    except ValueError:
        return mentors

    index = start
    while index + 6 < len(lines) and len(mentors) < limit:
        if not lines[index].isdigit():
            index += 1
            continue
        name = lines[index + 1]
        title = lines[index + 2]
        direction = lines[index + 3]
        department = lines[index + 5]
        email_value = lines[index + 6]
        if "@" in email_value and len(name) <= 8:
            mentors.append(
                {
                    "id": _mentor_id(source["url"], name),
                    "type": "mentor",
                    "name": name,
                    "title": title,
                    "campus": source["campus"],
                    "college": source["college"],
                    "department": department,
                    "direction": direction,
                    "requirements": "学院教师名录提供基础方向与邮箱，具体课题组要求以导师后续沟通为准。",
                    "contact_email": _normal_email(email_value),
                    "contact_phone": "",
                    "address": "",
                    "homepage": source["url"],
                    "source_url": source["url"],
                    "source_name": "哈工大（威海）计算机科学与技术学院教师名录",
                    "tags": _tags_from_direction(direction, source["college"]),
                    "updated_at": _now(),
                }
            )
            index += 7
        else:
            index += 1
    return mentors


def _normalize_college_name(name: str) -> str:
    return (name or "").replace("（威海）", "").replace("（深圳）", "").strip()


def _department_records(source: dict[str, Any]) -> list[dict[str, Any]]:
    payload = _post_json(
        f"{HIT_HOMEPAGE_DEPT_URL}/{source['dept_endpoint']}",
        {"id": source["root_id"], "campusId": source["campus_id"]},
    )
    records = payload.get("list") or []
    return records if isinstance(records, list) else []


def _flatten_departments(source: dict[str, Any], records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if source.get("campus_id") != "999960":
        return records

    top_levels = [row for row in records if str(row.get("parentid") or "") in {"0", "", "999960"}]
    children = [row for row in records if row not in top_levels]
    for parent in top_levels:
        parent["children"] = [row for row in children if str(row.get("parentid") or "") == str(parent.get("id") or "")]
    flattened: list[dict[str, Any]] = []
    for row in top_levels:
        flattened.append(row)
        flattened.extend(row.get("children") or [])
    return flattened


def _teacher_rows_by_dept(source: dict[str, Any], dept_id: str) -> list[dict[str, Any]]:
    payload = _post_json(
        f"{HIT_HOMEPAGE_DEPT_URL}/getUserInfoByDeptId.do",
        {"deptId": dept_id, "id": source["root_id"], "orderType": "1"},
    )
    records = payload.get("list") or []
    return records if isinstance(records, list) else []


def _mentor_from_homepage_row(source: dict[str, Any], department: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    slug = str(row.get("url") or "").strip()
    homepage = f"{HIT_HOMEPAGE_BASE}/{slug}?lang=zh" if slug and not slug.startswith("http") else slug
    college = _normalize_college_name(str(department.get("deptname") or row.get("department") or ""))
    research = str(row.get("shortDescription") or row.get("shortEnDescription") or "").strip()
    title = "教师"
    if "教授" in research:
        title = "教授"
    elif "副教授" in research:
        title = "副教授"
    elif "研究员" in research:
        title = "研究员"
    mentor_id = _mentor_id(homepage or str(row.get("id") or ""), str(row.get("userName") or ""))
    return {
        "id": mentor_id,
        "type": "mentor",
        "name": str(row.get("userName") or "").strip(),
        "title": title,
        "campus": source["name"],
        "college": college,
        "department": college,
        "direction": research,
        "research": research,
        "requirements": "请以教师主页、课题组公告和学院通知为准，联系前建议先准备个人方向、技能和可投入时间。",
        "contact_email": "",
        "contact_phone": "",
        "address": "",
        "homepage": homepage,
        "source_url": homepage,
        "source_name": "HIT 教师个人主页官网",
        "tags": _tags_from_direction(research, college),
        "updated_at": _now(),
    }


def _crawl_hit_homepage_mentors() -> dict[str, Any]:
    mentors: list[dict[str, Any]] = []
    source_status: list[dict[str, Any]] = []
    seen: set[str] = set()

    for source in HIT_HOMEPAGE_CAMPUS_SOURCES:
        try:
            raw_departments = _department_records(source)
            departments = _flatten_departments(source, raw_departments)
            campus_count = 0
            for department in departments:
                dept_id = str(department.get("id") or "").strip()
                dept_name = _normalize_college_name(str(department.get("deptname") or ""))
                if not dept_id or not dept_name:
                    continue
                try:
                    rows = _teacher_rows_by_dept(source, dept_id)
                except Exception:
                    rows = []
                for row in rows:
                    name = str(row.get("userName") or "").strip()
                    if not name:
                        continue
                    mentor = _mentor_from_homepage_row(source, department, row)
                    if mentor["id"] in seen:
                        continue
                    seen.add(mentor["id"])
                    mentors.append(mentor)
                    campus_count += 1
            source_status.append({**source, "ok": True, "department_count": len(departments), "count": campus_count})
        except Exception as exc:
            source_status.append({**source, "ok": False, "error": str(exc)})

    payload = {
        "items": mentors,
        "count": len(mentors),
        "sources": HIT_HOMEPAGE_CAMPUS_SOURCES,
        "source_status": source_status,
        "refreshed_at": _now(),
    }
    MENTOR_CACHE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _read_mentor_cache_items() -> list[dict[str, Any]]:
    payload = crawl_hit_mentors(force_refresh=False)
    items = payload.get("items") or []
    return items if isinstance(items, list) else []


def _light_mentor(item: dict[str, Any]) -> dict[str, Any]:
    research = str(item.get("research") or item.get("direction") or "").strip()
    if len(research) > 80:
        research = research[:80].rstrip() + "..."
    return {
        "id": item.get("id"),
        "name": item.get("name", ""),
        "college": item.get("college", ""),
        "department": item.get("department") or item.get("college", ""),
        "campus": item.get("campus", ""),
        "title": item.get("title", "教师"),
        "research": research,
        "homepage": item.get("homepage") or item.get("source_url") or "",
    }


def search_hit_mentors(
    keyword: str = "",
    college: str = "",
    campus: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    page = max(1, int(page or 1))
    page_size = max(1, min(50, int(page_size or 20)))
    keyword = keyword.strip().lower()
    college = college.strip()
    campus = campus.strip()
    items = _read_mentor_cache_items()

    def matched(item: dict[str, Any]) -> bool:
        if campus and item.get("campus") != campus:
            return False
        if college and (item.get("college") != college and item.get("department") != college):
            return False
        if keyword:
            haystack = " ".join(
                [
                    str(item.get("name", "")),
                    str(item.get("college", "")),
                    str(item.get("department", "")),
                    str(item.get("research", "")),
                    str(item.get("direction", "")),
                ]
            ).lower()
            if keyword not in haystack:
                return False
        return True

    filtered = [_light_mentor(item) for item in items if matched(item)]
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": filtered[start:end],
    }


def mentor_filter_options() -> dict[str, Any]:
    items = _read_mentor_cache_items()
    campuses = sorted({str(item.get("campus") or "").strip() for item in items if str(item.get("campus") or "").strip()})
    campus_colleges: dict[str, list[str]] = {}
    for campus in campuses:
        campus_colleges[campus] = sorted(
            {
                str(item.get("college") or item.get("department") or "").strip()
                for item in items
                if str(item.get("campus") or "").strip() == campus and str(item.get("college") or item.get("department") or "").strip()
            }
        )
    colleges = sorted({college for values in campus_colleges.values() for college in values})
    return {
        "campuses": campuses,
        "colleges": colleges,
        "campus_colleges": campus_colleges,
        "refreshed_at": crawl_hit_mentors(force_refresh=False).get("refreshed_at", ""),
    }


def get_hit_options(force_refresh: bool = False) -> dict:
    source_status = []
    if force_refresh:
        for source in OFFICIAL_SOURCES:
            try:
                _fetch(source["url"], timeout=12)
                source_status.append({**source, "ok": True})
            except Exception as exc:
                source_status.append({**source, "ok": False, "error": str(exc)})
    return {
        "campuses": _with_custom_options(),
        "sources": OFFICIAL_SOURCES,
        "source_status": source_status,
        "refreshed_at": _now(),
    }


def crawl_hit_mentors(force_refresh: bool = False) -> dict:
    if MENTOR_CACHE.exists() and not force_refresh:
        try:
            return json.loads(MENTOR_CACHE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return _crawl_hit_homepage_mentors()
