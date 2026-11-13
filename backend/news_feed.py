from __future__ import annotations

from datetime import date, datetime
from typing import Any

from contest_metrics import attach_metrics, get_contest_sections
from user_store import get_my_contests, get_my_matches

NEWS_WINDOW_DAYS = 30
DEFAULT_ALL_LIMIT = 16
DASHBOARD_DEADLINE_DAYS = 15


def _today() -> date:
    return date.today()


def _date_value(value: str) -> date | None:
    try:
        return datetime.strptime(value or '', '%Y-%m-%d').date()
    except ValueError:
        return None


def _days_text(value: str) -> str:
    target = _date_value(value)
    if not target:
        return '时间以官网通知为准'
    days = (target - _today()).days
    if days > 0:
        return f'距离截止还有 {days} 天'
    if days == 0:
        return '今天截止'
    return '已过截止'


def _in_news_window(value: str, days: int = NEWS_WINDOW_DAYS) -> bool:
    item_date = _date_value(value)
    if not item_date:
        return False
    diff = (item_date - _today()).days
    return -days <= diff <= days


def _today_text() -> str:
    return _today().strftime('%Y-%m-%d')


def _item_url(item: dict[str, Any]) -> str:
    return str(item.get('latest_notice_link') or item.get('official_link') or '')


def _specific_notice_url(item: dict[str, Any]) -> str:
    latest = str(item.get('latest_notice_link') or '').strip()
    official = str(item.get('official_link') or '').strip()
    if not latest or latest == official:
        return ''
    lower = latest.lower()
    if any(mark in lower for mark in ['info/', 'show/', 'news/', 'detail', 'content', 'article', '.htm', '.html', 'node/']):
        return latest
    return ''


def _contest_target(item: dict[str, Any]) -> dict[str, Any]:
    url = _specific_notice_url(item)
    return {
        'url': url,
        'open_type': 'source' if url else 'contest_detail',
        'action_text': '打开原文' if url else '查看详情',
    }


def _compact_contest(item: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': item.get('id'),
        'title': item.get('name', '竞赛'),
        'tag': item.get('category') or item.get('tag') or '竞赛',
        'status': item.get('status') or '待官网更新',
        'deadline': item.get('deadline') or '',
        'url': _item_url(item),
        'global_click_count': int(item.get('global_click_count', item.get('click_count', 0)) or 0),
        'global_click_rate': item.get('global_click_rate', 0),
    }


def _deadline_news(items: list[dict[str, Any]], limit: int = 5) -> list[dict[str, Any]]:
    result = []
    for item in items:
        deadline = str(item.get('deadline') or '')
        if not _date_value(deadline):
            continue
        result.append(
            {
                'id': f"deadline-{item.get('id')}",
                'type': '竞赛动态',
                'level': '重要',
                'title': f"{item.get('name')} 报名节点更新",
                'summary': f"{item.get('status') or '待确认'}，{_days_text(deadline)}。建议进入详情核对报名条件、材料和官网通知。",
                'source': item.get('source_name') or '竞赛官网',
                'time': deadline,
                'contest_id': item.get('id'),
                **_contest_target(item),
            }
        )
    result.sort(key=lambda row: row.get('time', '9999-99-99'))
    return result[:limit]


def _rule_news(items: list[dict[str, Any]], limit: int = 4) -> list[dict[str, Any]]:
    result = []
    for item in items:
        text = ' '.join(
            [
                str(item.get('name', '')),
                str(item.get('desc', '')),
                str(item.get('rules', '')),
                str(item.get('latest_notice_link', '')),
            ]
        )
        if not any(word in text for word in ['规则', '规程', '章程', '赛项', '通知', '指南', '安排']):
            continue
        result.append(
            {
                'id': f"rule-{item.get('id')}",
                'type': '规则变化',
                'level': '跟踪',
                'title': f"{item.get('name')} 规则与赛程需关注",
                'summary': '已关联官网通知入口，参赛对象、提交材料、赛项安排和评审规则以当年官网发布为准。',
                'source': item.get('source_name') or '竞赛官网',
                'time': item.get('last_crawled_at') or item.get('deadline') or _today_text(),
                'contest_id': item.get('id'),
                **_contest_target(item),
            }
        )
    return result[:limit]


def _result_news(items: list[dict[str, Any]], limit: int = 3) -> list[dict[str, Any]]:
    result = []
    positive = ['获奖名单', '成绩公示', '结果公示', '拟获奖', '获奖结果', '评审结果', '晋级名单', '决赛名单', '名单公示']
    negative = ['取消评奖', '评奖资格', '评审规则', '评审标准', '违规', '章程', '承诺书']
    for item in items:
        text = ' '.join(
            [
                str(item.get('name', '')),
                str(item.get('desc', '')),
                str(item.get('description', '')),
                str(item.get('latest_notice_link', '')),
            ]
        )
        if not any(word in text for word in positive) or any(word in text for word in negative):
            continue
        if not _specific_notice_url(item):
            continue
        result.append(
            {
                'id': f"result-{item.get('id')}",
                'type': '成绩公示',
                'level': '公示',
                'title': f"{item.get('name')} 成绩/名单信息",
                'summary': '检测到官网文本中包含成绩、获奖名单或公示信息，建议进入竞赛详情查看来源与官网入口。',
                'source': item.get('source_name') or '竞赛官网',
                'time': item.get('last_crawled_at') or _today_text(),
                'contest_id': item.get('id'),
                **_contest_target(item),
            }
        )
    return result[:limit]


def _policy_news() -> list[dict[str, Any]]:
    return [
        {
            'id': 'policy-moe',
            'type': '政策动向',
            'level': '政策',
            'title': '教育部高等教育司政策动态',
            'summary': '跟踪创新人才培养、实践教学、学科竞赛与创新创业教育相关政策，辅助判断竞赛价值和长期规划。',
            'source': '教育部官网',
            'time': _today_text(),
            'url': 'http://www.moe.gov.cn/s78/A08/',
            'contest_id': '',
            'open_type': 'source',
            'action_text': '查看政策来源',
        },
        {
            'id': 'policy-ncss',
            'type': '政策动向',
            'level': '平台',
            'title': '全国大学生创业服务网赛事动态',
            'summary': '关注中国国际大学生创新大赛、创新创业项目和就业创业服务相关通知。',
            'source': '全国大学生创业服务网',
            'time': _today_text(),
            'url': 'https://cy.ncss.cn/',
            'contest_id': '',
            'open_type': 'source',
            'action_text': '查看平台动态',
        },
        {
            'id': 'policy-hit-handbook',
            'type': '政策动向',
            'level': '校内',
            'title': '哈工大学生手册竞赛加分规则',
            'summary': '竞赛学分、推优加分和学院认定口径以学校当年学生手册及学院通知为准。',
            'source': '哈尔滨工业大学学生手册',
            'time': _today_text(),
            'url': '',
            'contest_id': '',
            'open_type': 'watch',
            'action_text': '查看详情',
        },
    ]


def get_home_news(contests: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = attach_metrics(contests)
    sections = get_contest_sections(enriched, limit=10)
    deadline_items = _deadline_news(sections.get('recent', []), limit=10)
    rule_items = _rule_news(enriched, limit=8)
    result_items = _result_news(enriched, limit=6)
    policy_items = _policy_news()
    feed = deadline_items + result_items + rule_items + policy_items

    seen: set[str] = set()
    unique_feed = []
    for item in feed:
        key = str(item.get('id') or item.get('title'))
        if key in seen:
            continue
        seen.add(key)
        if not _date_value(str(item.get('time', ''))):
            item['time'] = _today_text()
        item['in_current_window'] = _in_news_window(str(item.get('time', '')))
        item['window_label'] = f'近 {NEWS_WINDOW_DAYS} 天'
        unique_feed.append(item)

    current_feed = [item for item in unique_feed if item.get('in_current_window')]
    if current_feed:
        type_order = {'竞赛动态': 0, '规则变化': 1, '成绩公示': 2, '政策动向': 3}
        current_feed.sort(
            key=lambda item: (
                item.get('open_type') == 'watch',
                type_order.get(str(item.get('type', '')), 9),
                abs(((_date_value(str(item.get('time', ''))) or _today()) - _today()).days),
            )
        )
    default_feed = current_feed[:DEFAULT_ALL_LIMIT] if current_feed else unique_feed[: min(DEFAULT_ALL_LIMIT, len(unique_feed))]

    live_count = sum(1 for item in contests if item.get('status') in {'报名中', '即将开始'})
    recognized_count = sum(1 for item in contests if item.get('is_hit_recognized'))
    headline = next((item for item in default_feed if item.get('open_type') != 'watch'), None)
    headline = headline or (default_feed[0] if default_feed else (unique_feed[0] if unique_feed else {}))

    return {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'headline': headline,
        'tabs': ['全部', '竞赛动态', '成绩公示', '规则变化', '政策动向'],
        'items': unique_feed,
        'default_items': default_feed,
        'news_window_days': NEWS_WINDOW_DAYS,
        'all_limit': DEFAULT_ALL_LIMIT,
        'stats': [
            {'label': '收录竞赛', 'value': len(contests)},
            {'label': '近期可报', 'value': live_count},
            {'label': '校内认定', 'value': recognized_count},
        ],
        'recent': [_compact_contest(item) for item in sections.get('recent', [])[:5]],
        'hot': [_compact_contest(item) for item in sections.get('hot', [])[:5]],
    }


def _upcoming_deadline_rows(items: list[dict[str, Any]], days_limit: int = DASHBOARD_DEADLINE_DAYS) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    today = _today()
    for item in items:
        deadline_text = str(item.get('deadline') or '')
        deadline_value = _date_value(deadline_text)
        if not deadline_value:
            continue
        diff = (deadline_value - today).days
        if 0 <= diff <= days_limit:
            rows.append((diff, item))
    rows.sort(key=lambda row: (row[0], str(row[1].get('deadline') or '9999-99-99'), str(row[1].get('name') or '')))
    return rows


def build_home_dashboard(contests: list[dict[str, Any]]) -> dict[str, Any]:
    enriched = attach_metrics(contests)
    my_contests = get_my_contests()
    my_matches = get_my_matches()
    my_contest_ids = {str(item.get('id') or '') for item in my_contests if item.get('id')}
    linked_contests = [item for item in enriched if str(item.get('id') or '') in my_contest_ids]
    linked_contests.sort(key=lambda item: str(item.get('deadline') or '9999-99-99'))
    personal_upcoming = _upcoming_deadline_rows(linked_contests, days_limit=DASHBOARD_DEADLINE_DAYS)
    public_upcoming = _upcoming_deadline_rows(enriched, days_limit=DASHBOARD_DEADLINE_DAYS)

    recommendations = [
        {
            'type': '专业匹配',
            'title': '优先看与你专业相关的竞赛',
            'desc': '先从校内认定、专业相关、准备周期合适的赛事入手，更容易形成持续积累。',
            'buttonText': '查看相关竞赛',
            'action': 'contest',
        },
        {
            'type': '能力提升',
            'title': '用 AI 助手梳理技能短板',
            'desc': '可以直接询问适合的赛道、组队角色、准备节奏和材料清单，先补最短的板。',
            'buttonText': '问问AI助手',
            'action': 'ai',
        },
        {
            'type': '低门槛尝试',
            'title': '先建立参赛经验，再逐步冲高奖项',
            'desc': '如果你还没有明确方向，可以先从报名条件友好、节奏清晰的比赛开始。',
            'buttonText': '去竞赛中心',
            'action': 'contest',
        },
    ]

    upcoming_count = len(personal_upcoming)
    stats = [
        {'label': '已收藏竞赛', 'value': len(my_contests)},
        {'label': '即将截止', 'value': upcoming_count},
        {'label': '匹配记录', 'value': len(my_matches)},
        {'label': 'AI问答次数', 'value': 0},
    ]

    if personal_upcoming:
        first_item = personal_upcoming[0][1]
        ai_tip = f"你最近最需要优先处理的是“{first_item.get('name')}”的报名节点，建议先核对报名条件、材料要求和官网通知。"
    elif len(my_contests) == 0:
        ai_tip = '你还没有加入“我的竞赛”，可以先去竞赛中心收藏近期感兴趣的比赛，再根据截止时间安排任务。'
    else:
        ai_tip = '你可以先从低门槛竞赛建立参赛经验，再逐步挑战高含金量赛事。'

    timeline: list[dict[str, Any]] = []
    for diff, item in public_upcoming[:6]:
        timeline.append(
            {
                'id': f"timeline-{item.get('id')}",
                'title': item.get('name'),
                'time': item.get('deadline') or item.get('status') or '待确认',
                'desc': item.get('conditions') or item.get('bonus_summary') or item.get('desc') or f'距离截止还有 {diff} 天，建议尽快查看详情。',
                'contest_id': item.get('id'),
            }
        )

    return {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'title': '智竞工大',
        'subtitle': '你的竞赛成长行动台',
        'recommendations': recommendations,
        'stats': stats,
        'ai_tip': ai_tip,
        'timeline': timeline,
        'deadlineSoon': upcoming_count,
        'days_limit': DASHBOARD_DEADLINE_DAYS,
    }
