from __future__ import annotations

import hashlib
import re
from copy import deepcopy


HANDBOOK_SOURCE = "2025年《哈尔滨工业大学学生手册》"

GENERAL_BONUS_POLICY = {
    "source": HANDBOOK_SOURCE,
    "recommendation_bonus": [
        "推免综合考评优秀加分：学校认定的国际或国家级竞赛一等奖，个人项目获奖学生加5分。",
        "推免综合考评优秀加分：学校认定的国际或国家级竞赛二等奖，个人项目获奖学生加3分。",
        "推免综合考评优秀加分：学校认定的国际或国家级竞赛三等奖，个人项目获奖学生加1分。",
        "集体竞赛项目如证书或正式获奖文件无法区分排名，由校内竞赛牵头组织单位提供证明材料，本科生院复核确定排名顺序。",
    ],
    "innovation_credit": [
        "创新创业竞赛学分：互联网+大赛金奖、挑战杯特等奖、创青春金奖，团队负责人5学分，团队主要成员4学分。",
        "创新创业竞赛学分：国家特等奖、国家一等奖，团队负责人4学分，团队主要成员3学分。",
        "创新创业竞赛学分：国家二等奖、省部一等奖，团队负责人3学分，团队主要成员2学分。",
        "创新创业竞赛学分：省部二等奖、校一等奖，团队负责人2学分，团队主要成员1.5学分。",
        "创新创业竞赛学分：校二等奖、院系一等奖，团队负责人1.5学分，团队主要成员1学分。",
    ],
    "quality_points": [
        "大学生素质考评-创新与创造能力：获科研成果竞赛省级一/二/三等奖分别加2/1.5/1分，鼓励奖加0.5分；市、校级一/二/三等奖分别加1.5/1/0.5分。",
        "大学生素质考评-创新与创造能力：获学科竞赛省级一/二/三等奖分别加1.5/1/0.5分；市、校级一/二/三等奖分别加1/0.5/0.2分。",
        "同一成果多次获奖只按最高分认定，不重复加分；创新与创造能力项累计加分不超过3分。",
    ],
    "notes": [
        "学校认定推免加分项目和学校统一组织的竞赛，可按创新创业竞赛学分标准执行。",
        "除学校组织的与外校联合报名（含交流生）参加的竞赛外，未从学校报名参加的竞赛获奖不计入优秀加分。",
        "最终认定以学院、校区和本科生院当年通知及审核结果为准。",
    ],
}


SPECIAL_NOTES = {
    2: "特等奖和一等奖均按一等奖加分。",
    4: "年会获奖按国家一等奖加分；入围国年会决赛并参会按国家二等奖加分。",
    6: "特等奖和一等奖均按一等奖加分。",
    9: "一、二等奖降等加分，三等奖不加分。",
    11: "一、二等奖降等加分，三等奖不加分。",
    14: "特等奖和一等奖均按一等奖加分。",
    16: "特等奖和一等奖均按一等奖加分。",
    18: "特等奖和一等奖均按一等奖加分。",
    19: "特、一、二等奖降等加分。",
    20: "特等奖和一等奖均按一等奖加分。",
    21: "获个人类，一、二等奖降等加分，三等奖不加分。",
    22: "主赛道特等奖和一等奖均按一等奖加分；海洋与岛礁能源动力挑战赛一、二等奖降等加分，三等奖不加分；港澳台国际组金奖按二等奖、银奖按三等奖、铜奖不加分。",
    25: "特等奖和一等奖均按一等奖加分。",
    26: "特等奖和一等奖均按一等奖加分。",
    27: "一、二等奖降等加分，三等奖不加分；如有特等奖，特等奖按一等奖加分。",
    28: "特等奖和一等奖均按一等奖加分。",
    29: "特等奖和一等奖均按一等奖加分。",
    30: "特、一、二等奖降等加分，三等奖不加分。",
    31: "特、一、二等奖降等加分。",
    33: "一、二等奖降等加分，三等奖不加分。",
    34: "决赛获奖加分。",
    36: "特等奖按一等奖加分，提名特等奖按二等奖加分，一等奖按三等奖加分。",
    41: "特、一、二等奖降等加分，三等奖不加分。",
    45: "东南·中国建筑新人赛：Best2按一等奖加分，Best16按二等奖加分，Top100按三等奖加分。",
    47: "一、二等奖降等加分，三等奖不加分。",
    48: "特、一、二等奖降等加分，三等奖不加分。",
    53: "移动应用创新赛：一、二等奖降等加分，三等奖不加分；网络技术挑战赛：特、一、二等奖降等加分，三等奖不加分。",
    54: "一、二等奖降等加分，三等奖不加分。",
    55: "特等奖和一等奖均按一等奖加分。",
    56: "一、二等奖降等加分，三等奖不加分。",
    57: "仅限外国语学院。",
    60: "特等奖和一等奖均按一等奖加分。",
    61: "特等奖和一等奖均按一等奖加分。",
    62: "金奖按一等奖加分，银奖按二等奖加分，铜奖按三等奖加分。",
    63: "加分规则按照《哈尔滨工业大学（威海）关于校区推荐优秀应届本科毕业生免试攻读硕士学位研究生学科竞赛加分项目的补充说明》执行。",
}


RAW_HANDBOOK_COMPETITIONS = [
    (1, "中国国际大学生创新大赛", "创新创业", "https://cy.ncss.cn/", ["互联网+", "创新创业"]),
    (2, "“挑战杯”全国大学生课外学术科技作品竞赛", "创新创业", "https://www.tiaozhanbei.net/", ["挑战杯", "大挑"]),
    (3, "“挑战杯”中国大学生创业计划大赛", "创新创业", "https://www.tiaozhanbei.net/", ["创青春", "小挑", "创业计划"]),
    (4, "全国大学生创新年会", "创新创业", "https://gjcxcy.bjtu.edu.cn/", ["大创年会", "创新年会"]),
    (5, "全国航空航天模型锦标赛", "航空航天", "https://www.sport.gov.cn/hgzx/", ["航空航天模型"]),
    (6, "全国周培源大学生力学竞赛", "力学", "https://zpy.cstam.org.cn/", ["周培源", "力学竞赛"]),
    (7, "全国大学生集成电路创新创业大赛", "电子", "https://univ.ciciec.com/", ["集成电路", "芯片"]),
    (8, "iCAN大学生创新创业大赛", "创新创业", "https://www.g-ican.com/", ["iCAN"]),
    (9, "全国大学生物联网设计竞赛", "物联网", "https://iot.sjtu.edu.cn/", ["物联网设计"]),
    (10, "全国大学生嵌入式芯片与系统设计竞赛", "电子", "https://www.socchina.net/", ["嵌入式", "芯片与系统"]),
    (11, "“大唐杯”全国大学生新一代信息通信技术大赛", "通信", "https://dtcup.dtxg.org.cn/", ["大唐杯", "信息通信"]),
    (12, "全国大学生机械创新设计大赛", "机械", "http://umic.ckcest.cn/", ["机械创新"]),
    (13, "中国大学生工程实践与创新能力大赛", "工程实践", "http://www.gcxl.edu.cn/", ["工程实践"]),
    (14, "全国大学生机器人大赛", "机器人", "https://www.curc.cn/", ["RoboMaster", "RoboCon", "ABU RoboCon", "机器人大赛"]),
    (15, "全国大学生先进成图技术与产品信息建模创新大赛", "设计", "https://www.chengtudasai.com/", ["先进成图", "信息建模"]),
    (16, "全国三维数字化创新设计大赛", "设计", "https://www.3dds.org/", ["三维数字化", "3D大赛"]),
    (17, "中国大学生机械工程创新创意大赛", "机械", "https://www.cmes.org/", ["过程装备", "铸造工艺", "材料热处理", "起重机", "智能制造"]),
    (18, "中国高校智能机器人创意大赛", "机器人", "https://www.robotcontest.cn/", ["智能机器人创意"]),
    (19, "国际大学生智能农业装备创新大赛", "农业装备", "https://www.caae.org.cn/", ["智能农业装备"]),
    (20, "中美青年创客大赛", "创新创业", "https://www.chinaus-maker.org/", ["中美青年创客"]),
    (21, "全国大学生金相技能大赛", "材料", "https://www.cnmsec.com/", ["金相技能"]),
    (22, "全国大学生节能减排社会实践与科技竞赛", "能源环保", "https://www.jienengjianpai.org/", ["节能减排", "海洋与岛礁能源动力"]),
    (23, "全国大学生电子设计竞赛", "电子", "http://nuedc.xjtu.edu.cn/", ["电子设计", "电赛"]),
    (24, "全国大学生智能汽车竞赛", "智能车", "https://www.smartcarrace.com/", ["智能汽车"]),
    (25, "中国工业智能挑战赛", "AI", "https://ciic.ia.ac.cn/", ["工业智能"]),
    (26, "“西门子杯”中国智能制造挑战赛", "智能制造", "https://www.siemenscup-cimc.org.cn/", ["西门子杯", "智能制造"]),
    (27, "全国高校BIM毕业设计创新大赛", "BIM", "https://bisai.glodonedu.com/", ["BIM毕业设计"]),
    (28, "中国（国际）传感器创新创业大赛", "传感器", "https://www.sensorcontest.com/", ["传感器"]),
    (29, "全国大学生光电设计竞赛", "光电", "http://opt.zju.edu.cn/gdjs/", ["光电设计"]),
    (30, "全国大学生化工设计竞赛", "化工", "http://iche.zju.edu.cn/", ["化工设计"]),
    (31, "全国大学生化学实验创新设计大赛", "化学", "http://www.ncede.com.cn/", ["化学实验"]),
    (32, "中国大学生物理学术竞赛", "物理", "http://www.cupc.org.cn/", ["物理学术", "CUPT"]),
    (33, "全国大学生物理实验竞赛", "物理", "https://www.cupic.org.cn/", ["物理实验"]),
    (34, "全国大学生数学竞赛", "数学", "https://www.cms.org.cn/", ["数学竞赛"]),
    (35, "全国大学生数学建模竞赛", "数学建模", "https://www.mcm.edu.cn/index.moma", ["数学建模", "CUMCM"]),
    (36, "美国大学生数学建模竞赛", "数学建模", "https://www.contest.comap.com/undergraduate/contests/", ["美赛", "MCM", "ICM"]),
    (37, "全国大学生统计建模大赛", "统计", "https://tjjmds.ai-learning.net/", ["统计建模"]),
    (38, "全国大学生生命科学竞赛（CULSC）", "生命科学", "https://www.culsc.cn/", ["生命科学", "CULSC"]),
    (39, "全国高等院校数智化企业经营沙盘大赛", "经管", "https://www.xmcyjz.com/", ["企业经营沙盘", "数智化"]),
    (40, "全国大学生市场调查与分析大赛", "经管", "http://www.china-cssc.org/", ["市场调查", "市调大赛"]),
    (41, "全国大学生电子商务“创新、创意及创业”挑战赛", "电子商务", "https://www.3chuang.net/", ["三创赛", "电子商务"]),
    (42, "全国大学生物流设计大赛", "物流", "http://www.clpp.org.cn/", ["物流设计"]),
    (43, "中国大学生服务外包创新创业大赛", "服务外包", "https://www.fwwb.org.cn/", ["服务外包"]),
    (44, "全国大学生结构设计竞赛", "土木结构", "http://www.structurecontest.com/", ["结构设计"]),
    (45, "全国大学生建筑类竞赛", "建筑设计", "https://hypcup.uedmagazine.net/", ["UIA霍普杯", "HYP Cup", "天作奖", "东南·中国建筑新人赛", "城市设计", "风景园林", "新人杯"]),
    (46, "全国大学生广告艺术大赛", "广告设计", "https://www.sun-ada.net/", ["大广赛", "广告艺术"]),
    (47, "中国大学生计算机设计大赛", "编程", "https://jsjds.blcu.edu.cn/index.htm", ["4C", "计算机设计"]),
    (48, "全国大学生混凝土材料设计大赛", "材料", "https://www.cncmc.cn/", ["混凝土材料"]),
    (49, "全国大学生交通运输科技大赛", "交通", "http://www.nactrans.com/", ["交通运输科技"]),
    (50, "国际大学生程序设计竞赛（ICPC）", "编程", "https://icpc.global/", ["ACM", "ICPC"]),
    (51, "全国大学生信息安全竞赛", "信息安全", "https://www.ciscn.cn/", ["信息安全", "CISCN"]),
    (52, "全国大学生软件创新大赛", "软件", "https://www.cnsoftbei.com/", ["软件创新", "中国软件杯"]),
    (53, "中国高校计算机大赛", "计算机", "https://www.c4best.cn/", ["C4", "移动应用创新赛", "网络技术挑战赛", "人工智能创意赛"]),
    (54, "中国机器人及人工智能大赛", "AI", "http://www.caairobot.com/", ["机器人及人工智能"]),
    (55, "全国大学生计算机系统能力大赛", "计算机", "https://cscc.info/", ["计算机系统能力"]),
    (56, "全球校园人工智能算法精英大赛", "AI", "https://www.aicomp.cn/", ["AIC", "人工智能算法精英"]),
    (57, "全国大学生英语竞赛", "外语", "https://www.chinaneccs.cn/", ["NECCS", "英语竞赛"]),
    (58, "全国英语口译大赛", "外语", "https://www.catti.net.cn/", ["英语口译"]),
    (59, "“外研社·国才杯”“理解当代中国”全国大学生外语能力大赛", "外语", "https://ucc.fltrp.com/", ["外研社国才杯", "理解当代中国"]),
    (60, "“外研社·国才杯”全国大学生英语辩论赛", "外语", "https://debate.fltrp.com/", ["英语辩论"]),
    (61, "“21世纪杯”全国英语演讲比赛", "外语", "https://contest.i21st.cn/", ["21世纪杯", "英语演讲"]),
    (62, "全国大学生职业规划大赛（学生赛道）", "职业规划", "https://zgs.chsi.com.cn/", ["职业规划大赛"]),
    (63, "中国大学生方程式系列赛事", "车辆", "http://www.formulastudent.com.cn/", ["方程式", "FSC", "巴哈"]),
    (64, "全国海洋航行器设计与制作大赛", "海洋工程", "http://www.umv.com.cn/", ["海洋航行器"]),
]


def normalize_competition_name(value: str) -> str:
    value = value or ""
    value = value.lower()
    value = re.sub(r"[\s《》“”\"'（）()、,，:：;；.\-—_/]+", "", value)
    return value


def _stable_id(name: str) -> str:
    return "hit-" + hashlib.md5(name.encode("utf-8")).hexdigest()[:10]


def _entry(rank: int, name: str, category: str, link: str, aliases: list[str]) -> dict:
    special_note = SPECIAL_NOTES.get(rank, "按学校认定项目通用优秀加分规则执行。")
    policy = deepcopy(GENERAL_BONUS_POLICY)
    policy["special_note"] = special_note
    policy["handbook_rank"] = rank
    policy["recognized_project"] = name

    return {
        "id": _stable_id(name),
        "name": name,
        "category": category,
        "tag": f"{category} / 哈工大认定",
        "keywords": list(dict.fromkeys([category, *aliases, "哈工大认定", "推免加分", "创新创业学分"])),
        "registration_start_time": "",
        "registration_end_time": "",
        "deadline": "",
        "status": "校内认定",
        "location": "",
        "is_free": None,
        "source_name": HANDBOOK_SOURCE,
        "official_link": link,
        "desc": f"{name}已列入《哈尔滨工业大学本科生科技竞赛加分项目》，可作为推免综合考评优秀加分和创新创业学分认定参考。",
        "description": f"{name}为{HANDBOOK_SOURCE}附件1认定的本科生科技竞赛加分项目。平台将以手册清单为基础，结合竞赛官网持续补充报名时间、赛程与规则。",
        "target_audience": "普通高校在校学生可按赛项以个人或团队形式准备，具体组别通常由本科生、研究生或专业方向划分。",
        "conditions": "普通高校在校学生可按赛项以个人或团队报名；如需校内加分认定，应保留学校报名、推荐或备案材料。",
        "materials": ["获奖证书或正式获奖文件", "校内报名/推荐证明", "本科教学管理与服务系统认定材料"],
        "schedule": [],
        "rules": "校内加分和学分认定以学生手册、学院审核和本科生院审核结果为准。",
        "level": "校内认定",
        "value": {"study": 5, "job": 4, "bonus": 5},
        "fit": "适合需要竞赛经历、推免综合考评优秀加分或创新创业学分认定的学生重点关注。",
        "advice": "建议先确认是否从学校报名或由学校统一组织，再保存获奖证书、正式获奖文件和校内认定材料。",
        "source_type": "handbook",
        "is_hit_recognized": True,
        "handbook_rank": rank,
        "handbook_source": HANDBOOK_SOURCE,
        "bonus_summary": f"哈工大认定科技竞赛；推免优秀加分按国家级一/二/三等奖个人项目5/3/1分执行，创新创业竞赛学分最高负责人5分、主要成员4分。特殊规则：{special_note}",
        "bonus_policy": policy,
        "special_bonus_note": special_note,
        "aliases": aliases,
        "last_crawled_at": "",
    }


HANDBOOK_CONTESTS = [_entry(*item) for item in RAW_HANDBOOK_COMPETITIONS]

_MATCH_INDEX = []
for item in HANDBOOK_CONTESTS:
    names = [item["name"], *item.get("aliases", [])]
    for name in names:
        normalized = normalize_competition_name(name)
        if normalized:
            _MATCH_INDEX.append((normalized, item))
_MATCH_INDEX.sort(key=lambda pair: len(pair[0]), reverse=True)


def find_handbook_competition(name: str) -> dict | None:
    normalized_name = normalize_competition_name(name)
    if not normalized_name:
        return None
    for normalized, item in _MATCH_INDEX:
        if normalized in normalized_name or normalized_name in normalized:
            return item
    return None
