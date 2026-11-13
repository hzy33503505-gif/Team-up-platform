from __future__ import annotations

import hashlib
import io
import json
import re
import time
from copy import deepcopy
from dataclasses import dataclass
from datetime import date, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from handbook_competitions import (
    HANDBOOK_CONTESTS,
    find_handbook_competition,
    normalize_competition_name,
)


BASE_DIR = Path(__file__).resolve().parent
SOURCE_FILE = BASE_DIR / "contest_sources.json"
CACHE_FILE = BASE_DIR / "data" / "contest_cache.json"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

KEYWORDS = [
    "竞赛",
    "比赛",
    "大赛",
    "挑战杯",
    "数学建模",
    "电子设计",
    "计算机设计",
    "创新创业",
    "蓝桥杯",
    "机器人",
    "RoboMaster",
    "报名",
    "通知",
    "赛题",
]

NEGATIVE_KEYWORDS = [
    "新闻",
    "动态",
    "历程",
    "关于",
    "联系我们",
    "课程中心",
    "赞助商",
    "获奖名单",
    "结果公示",
    "我与大赛",
    "风采",
    "攻略",
    "启动会",
    "研讨会",
    "顺利召开",
    "决赛区",
    "公告",
    "资源中心",
    "资料下载",
    "培训",
    "研讨会",
    "会议",
    "论坛",
    "年会",
    "讲座",
    "报告会",
    "获奖名单",
    "结果公示",
    "资助结果",
    "通报",
    "暑期学校",
    "夏令营",
    "招生",
    "招聘",
]

STRONG_KEYWORDS = [
    "通知",
    "报名",
    "参赛",
    "章程",
    "规程",
    "赛项",
    "赛题",
    "指南",
    "启动",
    "征集",
    "办法",
    "安排",
]

CORE_COMPETITION_WORDS = [
    "竞赛",
    "比赛",
    "大赛",
    "报名",
    "参赛",
    "赛项",
    "章程",
    "规程",
]

FULL_DATE_RE = re.compile(
    r"(20\d{2})\s*[年./-]\s*(\d{1,2})\s*[月./-]\s*(\d{1,2})\s*日?"
)
DATE_RE = FULL_DATE_RE
SHORT_DATE_RE = re.compile(r"(?<!\d)(\d{1,2})\s*(?:月|[./-])\s*(\d{1,2})\s*日?")
YEAR_RE = re.compile(r"20\d{2}")
DATE_EXPR = r"(?:20\d{2}\s*[年./-]\s*)?\d{1,2}\s*(?:月|[./-])\s*\d{1,2}\s*日?"
UNKNOWN_MARKERS = ["以官网通知为准", "以官网", "官网通知", "官网公告", "待官网更新"]
HARD_LOW_VALUE_TITLE_WORDS = [
    "培训",
    "研讨会",
    "会议",
    "论坛",
    "讲座",
    "报告会",
    "获奖名单",
    "结果公示",
    "资助结果",
    "相似度",
    "通报",
    "暑期学校",
    "夏令营",
    "招生",
    "招聘",
]
REGISTRATION_WORDS = ["报名", "注册", "参赛报名", "网上报名", "校内报名"]
DEADLINE_WORDS = ["截止", "截至", "结束", "止", "逾期", "最后", "之前", "前"]
NON_REGISTRATION_CONTEXT_WORDS = [
    "获奖",
    "公示",
    "名单",
    "结果",
    "研讨会",
    "培训",
    "会议",
    "年会",
    "论坛",
    "讲座",
    "论文相似度",
    "资助",
]


FALLBACK_CONTESTS = [
    {
        "id": "fallback-mcm",
        "name": "全国大学生数学建模竞赛",
        "category": "数学建模",
        "tag": "数学建模 / 团队赛",
        "keywords": ["数学建模", "算法", "论文"],
        "registration_start_time": "",
        "registration_end_time": "",
        "deadline": "以官网通知为准",
        "status": "待官网更新",
        "location": "线上/各赛区",
        "is_free": None,
        "source_name": "全国大学生数学建模竞赛官网",
        "official_link": "https://www.mcm.edu.cn/index.moma",
        "desc": "面向高校学生的数学建模竞赛，通常以团队形式完成建模、编程、论文写作等任务。",
        "description": "面向高校学生的数学建模竞赛，通常以团队形式完成建模、编程、论文写作等任务。",
        "target_audience": "在校大学生，适合数学、计算机、统计、工程等方向学生。",
        "conditions": "参赛对象、报名时间、组队要求以官网当年通知为准。",
        "materials": ["报名信息", "参赛论文", "模型代码", "附件数据"],
        "schedule": [{"title": "报名/竞赛安排", "time": "以官网通知为准"}],
        "rules": "竞赛规则、赛题发布、论文提交和评审要求以官网公告为准。",
        "level": "高",
        "value": {"study": 5, "job": 4, "bonus": 5},
        "fit": "适合具备数学建模、编程实现、数据分析和论文写作能力的学生。",
        "advice": "建议提前准备常用建模方法、Python/MATLAB 工具链和论文模板。",
        "source_type": "fallback",
        "last_crawled_at": "",
    },
    {
        "id": "fallback-4c",
        "name": "中国大学生计算机设计大赛",
        "category": "编程",
        "tag": "计算机 / 作品赛",
        "keywords": ["计算机设计", "AI", "软件", "作品"],
        "registration_start_time": "",
        "registration_end_time": "",
        "deadline": "以官网通知为准",
        "status": "待官网更新",
        "location": "各省赛区/国赛赛区",
        "is_free": None,
        "source_name": "中国大学生计算机设计大赛官网",
        "official_link": "https://jsjds.blcu.edu.cn/index.htm",
        "desc": "面向高校本科生的计算机作品类竞赛，覆盖软件应用、人工智能、数据可视化、数字媒体等方向。",
        "description": "面向高校本科生的计算机作品类竞赛，覆盖软件应用、人工智能、数据可视化、数字媒体等方向。",
        "target_audience": "本科生团队，适合计算机、软件、数字媒体、人工智能等方向。",
        "conditions": "参赛对象、作品类别、报名材料和赛区安排以官网当年通知为准。",
        "materials": ["作品说明", "源代码", "演示视频", "答辩材料"],
        "schedule": [{"title": "报名/省赛/国赛", "time": "以官网通知为准"}],
        "rules": "作品类别、原创性要求、提交规范和评审标准以官网公告为准。",
        "level": "高",
        "value": {"study": 5, "job": 5, "bonus": 5},
        "fit": "适合有软件开发、AI 应用、交互设计或数据展示作品的学生团队。",
        "advice": "建议先明确赛道和作品形态，尽早准备演示视频与答辩材料。",
        "source_type": "fallback",
        "last_crawled_at": "",
    },
    {
        "id": "fallback-lanqiao",
        "name": "蓝桥杯全国软件和信息技术专业人才大赛",
        "category": "编程",
        "tag": "编程 / 算法 / 个人赛",
        "keywords": ["蓝桥杯", "算法", "程序设计"],
        "registration_start_time": "",
        "registration_end_time": "",
        "deadline": "以官网通知为准",
        "status": "待官网更新",
        "location": "线上/线下赛点",
        "is_free": None,
        "source_name": "蓝桥杯官网",
        "official_link": "https://dasai.lanqiao.cn/",
        "desc": "覆盖软件、电子、数字科技等方向的高校竞赛，常见赛项包括 C/C++、Java、Python、Web 等。",
        "description": "覆盖软件、电子、数字科技等方向的高校竞赛，常见赛项包括 C/C++、Java、Python、Web 等。",
        "target_audience": "高校学生，适合算法、软件开发、电子信息等方向。",
        "conditions": "参赛组别、科目、报名费用和赛程以官网当年通知为准。",
        "materials": ["报名信息", "身份证明", "参赛账号"],
        "schedule": [{"title": "报名/省赛/决赛", "time": "以官网通知为准"}],
        "rules": "具体科目规则、考试环境和晋级方式以官网通知为准。",
        "level": "中高",
        "value": {"study": 4, "job": 5, "bonus": 4},
        "fit": "适合希望用算法和编程能力获得竞赛经历的学生。",
        "advice": "建议按科目刷历年题，提前熟悉竞赛环境和输入输出规范。",
        "source_type": "fallback",
        "last_crawled_at": "",
    },
]


@dataclass
class Source:
    name: str
    url: str
    category: str = "综合"
    source_type: str = "official"
    official_link: str = ""
    max_links: int = 8
    keywords: list[str] | None = None


class LinkExtractor(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.links: list[dict] = []
        self._href = ""
        self._text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        attrs_dict = {key.lower(): value for key, value in attrs}
        href = attrs_dict.get("href")
        if href:
            self._href = urljoin(self.base_url, href)
            self._text_parts = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            text = clean_text("".join(self._text_parts))
            if text:
                self.links.append({"text": text, "url": self._href})
            self._href = ""
            self._text_parts = []


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.title = ""
        self.h1 = ""
        self.text_parts: list[str] = []
        self._tag_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag_stack.append(tag.lower())

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index] == tag:
                self._tag_stack.pop(index)
                break

    def handle_data(self, data: str) -> None:
        text = clean_text(data)
        if not text:
            return
        current = self._tag_stack[-1] if self._tag_stack else ""
        if current == "title" and not self.title:
            self.title = text
        if current == "h1" and not self.h1:
            self.h1 = text
        if current not in {"script", "style"}:
            self.text_parts.append(text)

    @property
    def text(self) -> str:
        return clean_text(" ".join(self.text_parts))


def clean_text(value: str) -> str:
    value = re.sub(r"\s+", " ", value or "")
    return value.strip(" \t\r\n\u3000")


def clamp_text(value: str, limit: int = 180) -> str:
    value = clean_text(value)
    return value if len(value) <= limit else value[: limit - 1] + "…"


def clean_competition_name(value: str) -> str:
    name = clean_text(value)
    # Some platform pages append article ids and years to <title>, e.g. "... 17978 2026".
    name = re.sub(r"\s+\d{3,}\s+20\d{2}\s*$", "", name)
    name = re.sub(r"\s+\d{3,}\s*$", "", name)
    name = re.sub(r"\s*[|_]\s*大学生竞赛.*$", "", name)
    return clamp_text(name, 80)


def fetch_html(url: str, timeout: int = 5) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        raw = response.read()
        charset = response.headers.get_content_charset()
    for encoding in [charset, "utf-8", "gb18030"]:
        if not encoding:
            continue
        try:
            return raw.decode(encoding, errors="ignore")
        except LookupError:
            continue
    return raw.decode("utf-8", errors="ignore")


def fetch_bytes(url: str, timeout: int = 8) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        return response.read()


def extract_pdf_text(url: str, max_pages: int = 8) -> str:
    if not url.lower().split("?", 1)[0].endswith(".pdf"):
        return ""
    try:
        from pypdf import PdfReader
    except Exception:
        return ""
    try:
        reader = PdfReader(io.BytesIO(fetch_bytes(url)))
    except Exception:
        return ""
    parts: list[str] = []
    for page in reader.pages[:max_pages]:
        try:
            parts.append(page.extract_text() or "")
        except Exception:
            continue
    return clean_text(" ".join(parts))


def extract_pdf_links(html: str, base_url: str) -> list[dict]:
    result = []
    for link in extract_links(html, base_url):
        url = link.get("url", "")
        if url.lower().split("?", 1)[0].endswith(".pdf"):
            result.append(link)
    return result


def load_sources(path: Path = SOURCE_FILE) -> list[Source]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    sources = [
        Source(
            name=item["name"],
            url=item["url"],
            category=item.get("category", "综合"),
            source_type=item.get("source_type", "official"),
            official_link=item.get("official_link") or item["url"],
            max_links=int(item.get("max_links", 8)),
            keywords=item.get("keywords") or [],
        )
        for item in data
    ]
    seen_urls = {source.url.rstrip("/") for source in sources}
    for item in HANDBOOK_CONTESTS:
        official_link = item.get("official_link") or ""
        if not official_link.startswith(("http://", "https://")):
            continue
        key = official_link.rstrip("/")
        if key in seen_urls:
            continue
        sources.append(
            Source(
                name=f"{item['name']}官网",
                url=official_link,
                category=item.get("category", "综合"),
                source_type="handbook",
                official_link=official_link,
                max_links=4,
                keywords=item.get("keywords", [])[:8],
            )
        )
        seen_urls.add(key)
    return sources


def extract_links(html: str, base_url: str) -> list[dict]:
    parser = LinkExtractor(base_url)
    parser.feed(html)
    return parser.links


def extract_text(html: str) -> tuple[str, str]:
    parser = TextExtractor()
    parser.feed(html)
    title = parser.h1 or parser.title
    return clean_text(title), parser.text


def is_valid_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def looks_like_competition(text: str, url: str, extra_keywords: Iterable[str] = ()) -> bool:
    haystack = f"{text} {url}".lower()
    words = KEYWORDS + list(extra_keywords)
    return any(word.lower() in haystack for word in words)


def is_good_candidate(text: str, url: str, extra_keywords: Iterable[str] = ()) -> bool:
    if not looks_like_competition(text, url, extra_keywords):
        return False

    normalized_text = clean_text(text).lower()
    normalized_url = url.lower()
    has_negative = any(word.lower() in normalized_text for word in NEGATIVE_KEYWORDS)
    has_strong = any(word.lower() in normalized_text for word in STRONG_KEYWORDS)

    if has_negative and not has_strong:
        return False
    if any(part in normalized_url for part in ["/news/index", "/about", "/gyds", "/history"]):
        return False
    return True


def link_candidate_score(link: dict, source: Source) -> int:
    text = clean_text(str(link.get("text", "")))
    url = str(link.get("url", ""))
    haystack = f"{text} {url}".lower()
    score = 0

    current_year = str(date.today().year)
    next_year = str(date.today().year + 1)
    if current_year in haystack:
        score += 45
    if next_year in haystack:
        score += 20
    if any(word.lower() in haystack for word in ["报名", "参赛报名", "网上报名", "注册"]):
        score += 55
    if any(word.lower() in haystack for word in ["通知", "公告"]):
        score += 35
    if any(word.lower() in haystack for word in ["章程", "规程", "规则", "参赛指南", "参赛要求"]):
        score += 32
    if any(word.lower() in haystack for word in ["一号通知", "第一次通知", "正式通知", "竞赛通知", "赛事通知"]):
        score += 24
    if source.category and source.category.lower() in haystack:
        score += 10
    for word in source.keywords or []:
        if str(word).lower() in haystack:
            score += 4

    if any(part in url.lower() for part in ["/node/", "/info/", "/c/"]):
        score += 12
    if any(part in url.lower() for part in ["/section/", "/list", "/index"]):
        score -= 18
    if url.lower().split("?", 1)[0].endswith(".pdf"):
        score -= 45
    if any(word.lower() in haystack for word in HARD_LOW_VALUE_TITLE_WORDS):
        score -= 90
    if any(word.lower() in haystack for word in ["启动会", "培训", "研讨会", "获奖", "公示", "名单", "结果"]):
        score -= 60
    if len(text) < 6:
        score -= 12
    if url.rstrip("/") == source.url.rstrip("/"):
        path = urlparse(url).path.strip("/").lower()
        if path and not path.endswith(("index.htm", "index.html", "index.moma")):
            score += 60
        else:
            score -= 25
    return score


def is_low_value_page(name: str, text: str, url: str) -> bool:
    normalized_name = clean_text(name).lower()
    normalized_text = clean_text(text[:800]).lower()
    normalized_url = url.lower()
    if any(word.lower() in normalized_name for word in HARD_LOW_VALUE_TITLE_WORDS):
        return True
    title_negative = any(word.lower() in normalized_name for word in NEGATIVE_KEYWORDS)
    has_core = any(word.lower() in normalized_name for word in CORE_COMPETITION_WORDS)
    if title_negative and not has_core:
        return True
    if any(part in normalized_url for part in ["/news/", "/resource/announcement", "/gsjs", "/article/"]):
        if not any(word.lower() in normalized_name for word in ["报名", "通知", "章程", "规程", "参赛"]):
            return True
    if any(word.lower() in normalized_name for word in ["启动会", "研讨会", "顺利召开", "决赛区"]):
        return True
    if any(word.lower() in normalized_name for word in ["暑期学校", "夏令营", "招生", "招聘"]):
        return True
    if len(normalized_text) < 80 and not has_core:
        return True
    return False


def normalize_date_parts(year: int | str, month: int | str, day: int | str) -> str:
    year, month, day = int(year), int(month), int(day)
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return ""


def normalize_date(match: tuple[str, str, str]) -> str:
    return normalize_date_parts(*match)


def infer_year_from_context(text: str, start: int, end: int) -> int:
    nearby = text[max(0, start - 80): min(len(text), end + 80)]
    years = [int(year) for year in YEAR_RE.findall(nearby)]
    if years:
        return years[-1]
    return date.today().year


def parse_date_phrase(phrase: str, default_year: int | None = None) -> str:
    full = FULL_DATE_RE.search(phrase)
    if full:
        return normalize_date(full.groups())
    short = SHORT_DATE_RE.search(phrase)
    if short:
        return normalize_date_parts(default_year or date.today().year, short.group(1), short.group(2))
    return ""


def iter_date_matches(text: str) -> list[tuple[str, int, int]]:
    matches: list[tuple[str, int, int]] = []
    occupied: list[tuple[int, int]] = []
    for match in FULL_DATE_RE.finditer(text):
        normalized = normalize_date(match.groups())
        if normalized:
            matches.append((normalized, match.start(), match.end()))
            occupied.append((match.start(), match.end()))
    for match in SHORT_DATE_RE.finditer(text):
        if any(start <= match.start() < end for start, end in occupied):
            continue
        year = infer_year_from_context(text, match.start(), match.end())
        normalized = normalize_date_parts(year, match.group(1), match.group(2))
        if normalized:
            matches.append((normalized, match.start(), match.end()))
    matches.sort(key=lambda item: item[1])
    return matches


def extract_dates(text: str) -> list[str]:
    dates: list[str] = []
    for normalized, _, _ in iter_date_matches(text):
        if normalized and normalized not in dates:
            dates.append(normalized)
    return dates


def _has_any(text: str, words: Iterable[str]) -> bool:
    return any(word in text for word in words)


def _date_context(text: str, start_pos: int, end_pos: int, radius: int = 72) -> str:
    return text[max(0, start_pos - radius): min(len(text), end_pos + radius)]


def _is_registration_deadline_context(context: str) -> bool:
    if _has_any(context, NON_REGISTRATION_CONTEXT_WORDS) and not _has_any(context, REGISTRATION_WORDS):
        return False
    if _has_any(context, REGISTRATION_WORDS) and _has_any(context, DEADLINE_WORDS):
        return True
    if _has_any(context, ["报名时间", "报名日期", "网上报名", "参赛报名", "注册时间", "报名阶段"]):
        return True
    return False


def extract_registration_range(text: str, dates: list[str]) -> tuple[str, str]:
    patterns = [
        rf"(?:报名时间|报名日期|报名阶段|报名系统|网上报名|参赛报名|注册时间|校内报名)[^。；;\n]{{0,100}}?"
        rf"({DATE_EXPR})"
        r"[^。；;]{0,20}?(?:至|到|-|—|--)"
        r"[^。；;]{0,20}?"
        rf"({DATE_EXPR})",
        rf"({DATE_EXPR})"
        r"[^。；;]{0,20}?(?:至|到|-|—|--)"
        r"[^。；;]{0,20}?"
        rf"({DATE_EXPR})"
        r"[^。；;]{0,40}?(?:报名|注册|参赛报名|网上报名)",
    ]
    for pattern in patterns:
        found = re.search(pattern, text)
        if found:
            context = text[max(0, found.start() - 30): min(len(text), found.end() + 30)]
            if not _is_registration_deadline_context(context):
                continue
            default_year = infer_year_from_context(text, found.start(), found.end())
            start = parse_date_phrase(found.group(1), default_year)
            end = parse_date_phrase(found.group(2), default_year)
            if start and end:
                if end < start:
                    end = normalize_date_parts(int(start[:4]) + 1, end[5:7], end[8:10])
                return start, end

    explicit_deadline_patterns = [
        rf"(?:报名|注册|参赛报名|网上报名|校内报名)[^。；;\n]{{0,80}}?(?:截止|截至|结束|止|逾期)[^。；;\n]{{0,30}}?({DATE_EXPR})",
        rf"({DATE_EXPR})[^。；;\n]{{0,35}}?(?:报名|注册|参赛报名|网上报名)[^。；;\n]{{0,20}}?(?:截止|截至|结束|止|逾期)",
        rf"({DATE_EXPR})[^。；;\n]{{0,12}}?(?:前|之前)[^。；;\n]{{0,24}}?(?:完成|进行|提交)?(?:报名|注册|参赛报名|网上报名)",
    ]
    for pattern in explicit_deadline_patterns:
        found = re.search(pattern, text)
        if not found:
            continue
        context = text[max(0, found.start() - 30): min(len(text), found.end() + 30)]
        if not _is_registration_deadline_context(context):
            continue
        default_year = infer_year_from_context(text, found.start(), found.end())
        end = parse_date_phrase(found.group(1), default_year)
        if end:
            return "", end
    return "", pick_deadline(text, dates)


def pick_deadline(text: str, dates: list[str]) -> str:
    if not dates:
        return ""
    best = ""
    best_score = -1
    for normalized, start_pos, end_pos in iter_date_matches(text):
        if not normalized:
            continue
        context = _date_context(text, start_pos, end_pos)
        if not _is_registration_deadline_context(context):
            continue
        score = 0
        if _has_any(context, REGISTRATION_WORDS):
            score += 5
        if _has_any(context, DEADLINE_WORDS):
            score += 5
        if any(word in context for word in ["缴费", "确认", "校赛", "省赛报名"]):
            score += 2
        if any(word in context for word in ["作品提交", "材料提交", "决赛", "公布", "颁奖"]):
            score -= 4
        if normalized > best:
            score += 1
        if score > best_score:
            best = normalized
            best_score = score
    return best if best_score >= 8 else ""


def extract_sentence(text: str, words: Iterable[str], limit: int = 140) -> str:
    parts = re.split(r"[。；;\n\r]", text)
    for part in parts:
        cleaned = clean_text(part)
        if len(cleaned) > 260:
            continue
        if any(word in cleaned for word in words):
            return clamp_text(cleaned, limit)
    return ""


def extract_conditions(text: str) -> str:
    preferred_words = ["参赛对象", "报名条件", "参赛条件", "参赛资格", "报名资格", "参赛要求"]
    student_words = ["高校", "院校", "大学生", "学生", "本科", "研究生", "在校"]
    action_words = ["参赛", "报名", "组队", "队伍", "团队", "资格", "对象", "条件"]
    candidates: list[tuple[int, str]] = []
    parts = re.split(r"[。；;\n\r]", text)
    for part in parts:
        cleaned = clean_text(part)
        if len(cleaned) < 8 or len(cleaned) > 220:
            continue
        if any(marker in cleaned for marker in ["copyright", "Copyright", "联系我们", "以官网"]):
            continue
        if "首页" in cleaned and not any(word in cleaned for word in preferred_words):
            continue
        if "是由" in cleaned and not any(word in cleaned for word in preferred_words):
            continue
        for word in preferred_words:
            index = cleaned.find(word)
            if index > 0:
                cleaned = cleaned[index:]
                break
        preferred_hit = any(word in cleaned for word in preferred_words)
        student_hit = any(word in cleaned for word in student_words)
        action_hit = any(word in cleaned for word in action_words)
        if not preferred_hit and not (student_hit and action_hit):
            continue
        score = 0
        if preferred_hit:
            score += 6
        if student_hit:
            score += 2
        if action_hit:
            score += 2
        if any(word in cleaned for word in ["不得", "限制", "指导教师"]):
            score += 1
        if score:
            candidates.append((score, clamp_text(cleaned, 180)))
    if not candidates:
        return ""
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


BAD_LOCATION_MARKERS = [
    "下一次",
    "举办一届",
    "学霸笔记",
    "小说阅读器",
    "在线缴费",
    "线下对公转账",
    "缴费状态",
    "参赛作品",
    "上推",
    "协办",
    "承办，",
    "由中国",
    "选拔冠军队",
    "作者:",
    "Copyright",
    "copyright",
]


def normalize_location(value: str) -> str:
    location = clean_text(value)
    if not location:
        return ""
    if any(marker in location for marker in BAD_LOCATION_MARKERS):
        return ""
    if any(word in location.lower() for word in ["email", "http", "copyright", "联系我们"]):
        return ""
    if len(location) > 90:
        return ""
    concrete_words = [
        "线上",
        "线下",
        "校区",
        "赛区",
        "赛点",
        "赛场",
        "会场",
        "中心",
        "大学",
        "学院",
        "基地",
        "馆",
        "楼",
        "室",
        "省",
        "市",
        "区",
        "县",
    ]
    if not any(word in location for word in concrete_words):
        return ""
    if location in {"地点", "赛区", "举办", "承办", "线下"}:
        return ""
    return clamp_text(location, 80)


def extract_location(text: str) -> str:
    sentence = extract_sentence(text, ["比赛地点", "竞赛地点", "决赛地点", "举办地点", "地点", "赛点", "赛场", "线下"], 120)
    if not sentence:
        return ""
    sentence = re.sub(r"^.*?(比赛地点|竞赛地点|决赛地点|举办地点|地点|赛点|赛场)", r"\1", sentence)
    sentence = re.sub(r"^(比赛地点|竞赛地点|决赛地点|举办地点|地点)\s*[:：]?\s*", "", sentence)
    return normalize_location(sentence)


def extract_materials(text: str) -> list[str]:
    mapping = [
        ("报名表", ["报名表", "报名信息"]),
        ("作品说明", ["作品说明", "说明书"]),
        ("项目计划书", ["计划书", "商业计划书"]),
        ("论文", ["论文", "竞赛论文"]),
        ("源代码", ["源代码", "代码"]),
        ("演示视频", ["视频", "演示"]),
        ("PPT/答辩材料", ["PPT", "答辩"]),
        ("身份证明", ["学生证", "身份证", "学籍"]),
    ]
    result = []
    for label, words in mapping:
        if any(word in text for word in words):
            result.append(label)
    return result or ["报名信息", "官网要求材料"]


def infer_category(text: str, default: str = "综合") -> str:
    category_words = [
        ("AI", ["人工智能", "AI", "机器学习", "大模型"]),
        ("编程", ["计算机", "软件", "程序", "编程", "算法", "蓝桥杯"]),
        ("数学建模", ["数学建模", "建模", "模型"]),
        ("电子", ["电子设计", "电路", "芯片", "嵌入式", "单片机"]),
        ("机器人", ["机器人", "RoboMaster", "Robocon", "机甲大师"]),
        ("创新创业", ["创新创业", "互联网+", "挑战杯", "创业"]),
        ("设计", ["设计", "数字媒体", "视觉", "工业设计"]),
    ]
    for category, words in category_words:
        if any(word in text for word in words):
            return category
    return default


def score_level(text: str) -> str:
    if any(word in text for word in ["全国", "国家级", "国赛", "教育部", "共青团中央"]):
        return "高"
    if any(word in text for word in ["省级", "赛区", "区域赛"]):
        return "中高"
    return "中"


def build_schedule(text: str, dates: list[str]) -> list[dict]:
    if not dates:
        return []
    schedule = []
    for found_date in dates[:6]:
        index = text.find(found_date[:4])
        context = ""
        if index >= 0:
            context = clamp_text(text[max(0, index - 24): min(len(text), index + 50)], 80)
        title = "关键时间"
        if "报名" in context:
            title = "报名"
        elif "提交" in context or "作品" in context:
            title = "作品提交"
        elif "初赛" in context:
            title = "初赛"
        elif "复赛" in context:
            title = "复赛"
        elif "决赛" in context:
            title = "决赛"
        schedule.append({"title": title, "time": found_date, "desc": context})
    return schedule


def fallback_audience(category: str) -> str:
    mapping = {
        "编程": "适合计算机、软件、人工智能、数据科学等方向学生，可按个人赛或团队作品赛准备。",
        "AI": "适合人工智能、软件工程、数据分析等方向学生，通常需要算法、模型训练或应用开发能力。",
        "数学建模": "适合数学、统计、计算机、工程等方向学生，通常需要团队协作完成建模与论文。",
        "电子": "适合电子信息、自动化、通信、嵌入式等方向学生，通常需要电路设计、调试和报告撰写能力。",
        "机器人": "适合机械、自动化、计算机、控制等方向学生，通常需要跨专业团队协作。",
        "创新创业": "适合有创新项目、科研成果转化或创业计划的学生团队。",
        "设计": "适合视觉设计、工业设计、数字媒体、交互设计等方向学生。",
    }
    return mapping.get(category, "适合关注该方向的高校学生，可结合专业方向、项目经历和组队需求准备。")


def fallback_description(name: str, category: str, source_name: str) -> str:
    return f"{name} 来源于 {source_name}，属于{category}类竞赛/通知。平台会优先整理报名时间、地点、材料和规则等关键信息。"


def calc_status(start: str, end: str) -> str:
    today = date.today().isoformat()
    if start and today < start:
        return "即将开始"
    if end:
        if today <= end:
            return "报名中"
        return "已结束"
    return "待官网更新"


def stable_id(url: str, title: str) -> str:
    key = f"{url}|{title}".encode("utf-8", errors="ignore")
    return "contest-" + hashlib.md5(key).hexdigest()[:12]


def is_iso_date(value: str) -> bool:
    try:
        datetime.strptime(value or "", "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_unknown_text(value: str) -> bool:
    return not clean_text(value) or any(marker in value for marker in UNKNOWN_MARKERS)


def prepare_display_fields(item: dict) -> dict:
    result = deepcopy(item)
    if (
        result.get("deadline")
        and result.get("source_type") not in {"handbook", "fallback"}
        and not result.get("deadline_source")
    ):
        result["deadline"] = ""
        result["registration_end_time"] = ""
        result["status"] = "待官网更新"
    if not is_iso_date(str(result.get("deadline", ""))):
        result["deadline"] = ""
        if result.get("status") == "待官网更新":
            result["status"] = "待发布"
    if not is_iso_date(str(result.get("registration_start_time", ""))):
        result["registration_start_time"] = ""
    result["location"] = normalize_location(str(result.get("location", "")))
    if is_unknown_text(str(result.get("location", ""))):
        result["location"] = ""

    conditions = clean_text(str(result.get("conditions", "")))
    if is_unknown_text(conditions):
        conditions = fallback_audience(str(result.get("category", "综合")))
    result["conditions"] = conditions
    result["target_audience"] = conditions or result.get("target_audience", "")

    schedule = []
    for row in result.get("schedule") or []:
        if is_unknown_text(str(row.get("time", ""))):
            continue
        schedule.append(row)
    result["schedule"] = schedule

    materials = []
    for material in result.get("materials") or []:
        if is_unknown_text(str(material)) or str(material) == "官网要求材料":
            continue
        materials.append(material)
    result["materials"] = materials

    if is_unknown_text(str(result.get("rules", ""))):
        result["rules"] = ""

    result["has_deadline"] = is_iso_date(str(result.get("deadline", "")))
    result["has_start_time"] = is_iso_date(str(result.get("registration_start_time", "")))
    result["has_location"] = bool(clean_text(str(result.get("location", ""))))
    result["has_conditions"] = bool(clean_text(str(result.get("conditions", ""))))
    result["condition_label"] = "报名条件" if result.get("conditions_source") == "extracted" else "适合对象"
    result["has_schedule"] = bool(schedule)
    result["has_materials"] = bool(materials)
    result["has_rules"] = bool(clean_text(str(result.get("rules", ""))))
    result["name"] = clean_competition_name(str(result.get("name", "")))
    return result


def apply_handbook_bonus(item: dict) -> dict:
    result = deepcopy(item)
    match_text = " ".join(
        [
            str(result.get("name", "")),
            str(result.get("source_name", "")),
            str(result.get("desc", "")),
            str(result.get("description", "")),
            " ".join(result.get("keywords", [])),
        ]
    )
    handbook = find_handbook_competition(match_text)
    if not handbook:
        result.setdefault("is_hit_recognized", False)
        return prepare_display_fields(result)

    handbook_copy = deepcopy(handbook)
    crawled_link = result.get("official_link") or ""
    handbook_link = handbook_copy.get("official_link") or ""
    if crawled_link and crawled_link != handbook_link:
        result["latest_notice_link"] = crawled_link
    if result.get("deadline_source_url"):
        result["latest_notice_link"] = result["deadline_source_url"]

    result["id"] = handbook_copy["id"]
    result["name"] = handbook_copy["name"]
    result["category"] = handbook_copy["category"]
    result["tag"] = handbook_copy["tag"]
    result["official_link"] = handbook_link or crawled_link
    result["is_hit_recognized"] = True
    result["handbook_rank"] = handbook_copy["handbook_rank"]
    result["handbook_source"] = handbook_copy["handbook_source"]
    result["bonus_summary"] = handbook_copy["bonus_summary"]
    result["bonus_policy"] = handbook_copy["bonus_policy"]
    result["special_bonus_note"] = handbook_copy["special_bonus_note"]

    keywords = [
        result["category"],
        *result.get("keywords", []),
        *handbook_copy.get("keywords", []),
    ]
    result["keywords"] = list(dict.fromkeys([word for word in keywords if word]))[:10]

    value = deepcopy(result.get("value") or handbook_copy.get("value", {}))
    value["bonus"] = max(int(value.get("bonus", 0) or 0), 5)
    value["study"] = max(int(value.get("study", 0) or 0), 5)
    value.setdefault("job", handbook_copy.get("value", {}).get("job", 4))
    result["value"] = value

    if result.get("conditions_source") != "extracted":
        result["conditions"] = handbook_copy["conditions"]
        result["target_audience"] = handbook_copy["target_audience"]
    elif not result.get("conditions"):
        result["conditions"] = handbook_copy["conditions"]
    if not result.get("target_audience"):
        result["target_audience"] = handbook_copy["target_audience"]
    if not result.get("materials"):
        result["materials"] = handbook_copy["materials"]
    if not result.get("schedule"):
        result["schedule"] = handbook_copy["schedule"]
    if not result.get("rules"):
        result["rules"] = handbook_copy["rules"]
    if result.get("level") in {"", "中", None}:
        result["level"] = handbook_copy["level"]
    if not result.get("advice"):
        result["advice"] = handbook_copy["advice"]

    return prepare_display_fields(result)


def build_contest_item(source: Source, link: dict, html: str) -> dict | None:
    title, text = extract_text(html)
    link_text = clean_text(str(link.get("text") or ""))
    if link_text and (not title or title == source.name or len(link_text) > len(title) + 6):
        name = link_text
    else:
        name = title or link_text or source.name
    name = re.sub(r"[-_].*$", "", name).strip()
    if is_low_value_page(name, text, link["url"]):
        return None
    if not is_good_candidate(name + " " + text[:500], link["url"], source.keywords or []):
        return None
    if not looks_like_competition(name + " " + text[:300], link["url"], source.keywords or []):
        return None

    deadline_text = text
    deadline_source_url = ""
    deadline_source_text = ""
    for pdf_link in extract_pdf_links(html, link["url"])[:3]:
        pdf_text = extract_pdf_text(pdf_link.get("url", ""))
        if not pdf_text:
            continue
        pdf_dates = extract_dates(pdf_text)
        pdf_start, pdf_end = extract_registration_range(pdf_text, pdf_dates)
        if pdf_end:
            deadline_text = pdf_text
            deadline_source_url = pdf_link.get("url", "")
            deadline_source_text = clean_text(str(pdf_link.get("text") or "PDF附件"))
            break

    dates = extract_dates(deadline_text)
    start_time, end_time = extract_registration_range(deadline_text, dates)
    deadline = end_time
    category = infer_category(f"{name} {text}", source.category)
    conditions = extract_conditions(text)
    rules = extract_sentence(text, ["竞赛规则", "作品要求", "评审", "奖项", "提交", "要求"], 240)
    description = extract_sentence(text, ["竞赛", "大赛", "比赛", "旨在", "目的", "面向"], 200)
    if not description or len(description) < 18:
        description = fallback_description(name, category, source.name)

    link_url = link["url"]
    official_link = link_url if is_valid_http_url(link_url) else source.official_link
    status = calc_status(start_time, deadline)
    free_text = extract_sentence(text, ["免费", "不收取", "费用", "报名费"], 90)
    is_free = None
    if any(word in free_text for word in ["免费", "不收取"]):
        is_free = True
    elif any(word in free_text for word in ["费用", "报名费", "收费"]):
        is_free = False

    item = {
        "id": stable_id(link_url, name),
        "name": clean_competition_name(name),
        "category": category,
        "tag": f"{category} / {source.source_type}",
        "keywords": list(dict.fromkeys([category, *(source.keywords or [])]))[:6],
        "registration_start_time": start_time,
        "registration_end_time": end_time,
        "deadline": deadline,
        "deadline_source": f"官网PDF附件：{deadline_source_text}" if deadline and deadline_source_url else ("官网报名时间" if deadline else ""),
        "deadline_source_url": deadline_source_url,
        "deadline_confidence": "high" if deadline else "",
        "status": status,
        "location": extract_location(text),
        "is_free": is_free,
        "source_name": source.name,
        "official_link": official_link,
        "desc": description,
        "description": description,
        "target_audience": conditions or fallback_audience(category),
        "conditions": conditions or fallback_audience(category),
        "conditions_source": "extracted" if conditions else "fallback",
        "materials": extract_materials(text),
        "schedule": build_schedule(text, dates),
        "rules": rules or "竞赛规则、提交材料、评审标准和奖项设置以官网公告为准。",
        "level": score_level(text),
        "value": {
            "study": 5 if score_level(text) == "高" else 4,
            "job": 5 if category in {"编程", "AI", "电子", "机器人"} else 4,
            "bonus": 5 if score_level(text) == "高" else 4,
        },
        "fit": conditions or fallback_audience(category),
        "advice": "建议先阅读官网通知，确认报名截止、组队规则、作品要求和校内推荐流程。",
        "source_type": source.source_type,
        "last_crawled_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return apply_handbook_bonus(item)


def crawl_competitions(max_items: int = 220, max_seconds: int = 150) -> list[dict]:
    contests: list[dict] = []
    seen_urls: set[str] = set()
    sources = load_sources()
    started_at = time.time()

    for source in sources:
        if time.time() - started_at > max_seconds:
            break
        try:
            html = fetch_html(source.url)
        except (HTTPError, URLError, TimeoutError, OSError):
            continue

        source_links = [
            {"text": source.name, "url": source.url},
            *extract_links(html, source.url),
        ]

        candidates = []
        for link in source_links:
            url = link.get("url", "")
            if not is_valid_http_url(url) or url in seen_urls:
                continue
            if is_good_candidate(link.get("text", ""), url, source.keywords or []):
                candidates.append((link_candidate_score(link, source), link))

        candidates.sort(key=lambda row: row[0], reverse=True)
        candidates = candidates[: source.max_links]

        for _, link in candidates:
            if time.time() - started_at > max_seconds:
                break
            seen_urls.add(link["url"])
            try:
                detail_html = html if link["url"] == source.url else fetch_html(link["url"])
            except (HTTPError, URLError, TimeoutError, OSError, ValueError):
                continue
            item = build_contest_item(source, link, detail_html)
            if item:
                contests.append(item)
            if len(contests) >= max_items:
                return dedupe_contests(contests)

    return dedupe_contests(contests)


def dedupe_contests(items: list[dict]) -> list[dict]:
    result = []
    seen_links = set()
    seen_names = set()
    for item in sorted(items, key=lambda x: (x.get("status") != "报名中", x.get("deadline", "9999"))):
        item["name"] = clean_competition_name(str(item.get("name", "")))
        if is_low_value_page(str(item.get("name", "")), str(item.get("description") or item.get("desc") or ""), str(item.get("official_link", ""))):
            continue
        link_key = item.get("official_link") or ""
        name_key = normalize_competition_name(item.get("name", ""))[:36]
        use_link_dedupe = link_key and not item.get("is_hit_recognized")
        if (use_link_dedupe and link_key in seen_links) or (name_key and name_key in seen_names):
            continue
        if use_link_dedupe:
            seen_links.add(link_key)
        if name_key:
            seen_names.add(name_key)
        result.append(item)
    return result


def merge_handbook_contests(items: list[dict]) -> list[dict]:
    enriched = [apply_handbook_bonus(item) for item in items]
    return dedupe_contests(enriched + [deepcopy(item) for item in HANDBOOK_CONTESTS])


def read_cache(cache_file: Path = CACHE_FILE, max_age_seconds: int = 21600) -> list[dict]:
    if not cache_file.exists():
        return []
    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if time.time() - float(payload.get("updated_at", 0)) > max_age_seconds:
        return []
    return merge_handbook_contests(payload.get("items", []))


def write_cache(items: list[dict], cache_file: Path = CACHE_FILE) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": time.time(),
        "updated_text": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "items": items,
    }
    cache_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def get_contests(force_refresh: bool = False) -> list[dict]:
    if not force_refresh:
        cached = read_cache()
        if cached:
            return cached

    try:
        crawled = crawl_competitions()
    except Exception:
        crawled = []

    items = merge_handbook_contests(crawled + FALLBACK_CONTESTS)
    write_cache(items)
    return items


def load_cached_or_fallback() -> list[dict]:
    cached = read_cache(max_age_seconds=60 * 60 * 24 * 30)
    return cached or merge_handbook_contests(FALLBACK_CONTESTS)
