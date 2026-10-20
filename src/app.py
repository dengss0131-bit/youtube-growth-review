"""Multi-platform new-media growth review tool.

Turns exported creator-backend CSV data (YouTube / Douyin / Xiaohongshu /
Bilibili / WeChat Channels / TikTok) into a strategic growth report.

Runs locally with only the Python standard library. No third-party deps.
No frontend JavaScript required: reports are rendered by this HTTP server.
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs
from html import escape
from email.parser import BytesParser
from email.policy import default
import csv
import io
import re
import statistics

HOST = "127.0.0.1"
PORT = 8765

# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------
# Each platform maps a canonical field name to the list of header aliases it
# may use in a backend export. Headers are normalized (lowercase, no %/()/space)
# before matching, so aliases can be written in any case/spacing.
#
# Canonical fields (the unified metric layer):
#   title, video_id, topic, series, thumbnail_type, hook_type,
#   views, ctr, impressions, avg_view_duration, watch_time_hours,
#   video_duration, retention, subscribers_gained,
#   likes, comments, shares, favorites, publish_date
# ---------------------------------------------------------------------------

PLATFORMS = {
    "youtube": {
        "label": "YouTube",
        "item": "视频",
        "signature": ["thumbnail", "thumbnail impressions", "impressions click-through rate", "watch time", "subscribers", "video title", "average percentage viewed"],
        "aliases": {
            "title": ["title", "video title", "标题", "视频标题"],
            "video_id": ["content", "video", "video id", "视频", "内容"],
            "topic": ["topic", "题材", "主题", "选题"],
            "series": ["series", "系列", "栏目"],
            "thumbnail_type": ["thumbnail_type", "thumbnail type", "缩略图类型", "封面类型", "thumbnail"],
            "hook_type": ["hook_type", "hook type", "开头类型", "钩子", "hook"],
            "views": ["views", "观看次数", "播放量", "观看", "views count"],
            "ctr": ["ctr", "impressions click-through rate", "impressions ctr", "thumbnail click-through rate", "thumbnail click-through rate %", "展示点击率", "缩略图点击率", "点击率"],
            "impressions": ["impressions", "thumbnail impressions", "展示次数", "缩略图展示次数", "曝光"],
            "avg_view_duration": ["avg_view_duration", "average view duration", "平均观看时长", "平均观看秒数", "avd"],
            "watch_time_hours": ["watch time hours", "watch time", "观看时长 小时", "观看时长"],
            "video_duration": ["video_duration", "duration", "视频时长", "总时长", "时长"],
            "retention": ["average percentage viewed", "average percentage viewed %", "平均观看百分比", "平均观看百分比 %", "完播率"],
            "subscribers_gained": ["subscribers_gained", "subscribers", "subscribers gained", "涨粉", "新增订阅", "订阅者", "订阅增加"],
            "likes": ["likes", "点赞"],
            "comments": ["comments", "评论"],
            "shares": ["shares", "分享"],
            "publish_date": ["publish_date", "published", "publish date", "video publish time", "发布日期", "发布时间", "date", "日期"],
        },
    },
    "douyin": {
        "label": "抖音",
        "item": "视频",
        "signature": ["作品标题", "作品id", "吸粉数"],
        "aliases": {
            "title": ["作品标题", "视频标题", "标题", "作品名称", "内容标题"],
            "video_id": ["作品id", "视频id", "作品链接", "视频链接"],
            "topic": ["题材", "主题", "分类", "标签"],
            "series": ["系列", "合集", "栏目"],
            "views": ["播放量", "播放次数", "播放", "浏览量", "观看次数"],
            "ctr": ["点击率", "播放点击率"],
            "impressions": ["展现量", "曝光量", "推荐量", "曝光"],
            "avg_view_duration": ["平均播放时长", "平均观看时长", "平均播放秒数", "平均观看秒数"],
            "video_duration": ["视频时长", "作品时长", "时长"],
            "retention": ["完播率", "播放完成率", "平均播放进度", "完播"],
            "subscribers_gained": ["涨粉数", "新增粉丝", "新增关注", "吸粉数", "涨粉"],
            "likes": ["点赞数", "点赞量", "点赞"],
            "comments": ["评论数", "评论量", "评论"],
            "shares": ["分享数", "分享量", "转发数", "转发"],
            "favorites": ["收藏数", "收藏量", "收藏"],
            "publish_date": ["发布时间", "发布日期", "时间", "日期"],
        },
    },
    "xiaohongshu": {
        "label": "小红书",
        "item": "笔记",
        "signature": ["笔记标题", "阅读量", "收藏", "完读率", "平均阅读时长", "笔记id"],
        "aliases": {
            "title": ["笔记标题", "标题", "内容标题", "正文标题"],
            "video_id": ["笔记id", "笔记链接", "内容链接"],
            "topic": ["题材", "主题", "分类", "标签", "赛道"],
            "series": ["系列", "合集", "栏目", "专题"],
            "views": ["阅读量", "阅读数", "浏览量", "曝光阅读", "阅读"],
            "ctr": ["点击率", "笔记点击率", "阅读率"],
            "impressions": ["曝光量", "展现量", "曝光数", "曝光"],
            "avg_view_duration": ["平均阅读时长", "平均停留时长", "平均阅读秒数"],
            "retention": ["完读率", "阅读完成率", "完播率"],
            "subscribers_gained": ["涨粉数", "新增粉丝", "新增关注", "涨粉"],
            "likes": ["点赞数", "点赞", "赞"],
            "comments": ["评论数", "评论"],
            "shares": ["分享数", "转发", "分享"],
            "favorites": ["收藏数", "收藏"],
            "publish_date": ["发布时间", "发布日期", "时间", "日期"],
        },
    },
    "bilibili": {
        "label": "B站",
        "item": "视频",
        "signature": ["稿件标题", "bvid", "投币", "新增关注", "稿件id", "av号"],
        "aliases": {
            "title": ["稿件标题", "视频标题", "标题"],
            "video_id": ["稿件id", "bvid", "av号", "视频链接"],
            "topic": ["题材", "主题", "分区", "分类", "标签"],
            "series": ["系列", "合集", "栏目"],
            "views": ["播放量", "播放", "播放次数", "观看次数"],
            "ctr": ["点击率", "播放点击率"],
            "impressions": ["曝光量", "展现量", "推荐曝光", "曝光"],
            "avg_view_duration": ["平均播放时长", "平均观看时长", "平均播放秒数"],
            "video_duration": ["视频时长", "稿件时长", "时长"],
            "retention": ["完播率", "播放完成率", "平均播放进度"],
            "subscribers_gained": ["新增关注", "涨粉", "新增粉丝", "涨粉数"],
            "likes": ["点赞", "点赞数"],
            "comments": ["评论", "评论数"],
            "shares": ["分享", "转发", "分享数"],
            "favorites": ["收藏", "收藏数"],
            "publish_date": ["发布时间", "发布日期", "时间", "日期"],
        },
    },
    "shipinhao": {
        "label": "视频号",
        "item": "视频",
        "signature": ["视频标题", "转发", "点赞", "关注数"],
        "aliases": {
            "title": ["视频标题", "标题", "作品标题", "内容标题"],
            "video_id": ["视频id", "作品id", "视频链接"],
            "topic": ["题材", "主题", "分类", "标签"],
            "series": ["系列", "合集", "栏目"],
            "views": ["播放量", "播放", "阅读量", "观看次数"],
            "ctr": ["点击率"],
            "impressions": ["曝光量", "展现量", "曝光"],
            "avg_view_duration": ["平均播放时长", "平均观看时长"],
            "video_duration": ["视频时长", "时长"],
            "retention": ["完播率", "播放完成率"],
            "subscribers_gained": ["涨粉", "新增关注", "关注数", "涨粉数"],
            "likes": ["点赞", "点赞数"],
            "comments": ["评论", "评论数"],
            "shares": ["转发", "分享", "转发数"],
            "favorites": ["收藏", "收藏数"],
            "publish_date": ["发布时间", "发布日期", "时间", "日期"],
        },
    },
    "tiktok": {
        "label": "TikTok",
        "item": "视频",
        "signature": ["followers", "reach", "video views", "average watch time", "retention rate"],
        "aliases": {
            "title": ["title", "video title", "标题", "视频标题"],
            "video_id": ["video id", "content", "video", "视频"],
            "topic": ["topic", "题材", "主题"],
            "series": ["series", "系列", "栏目"],
            "views": ["views", "video views", "播放量", "观看次数"],
            "ctr": ["ctr", "click-through rate", "点击率"],
            "impressions": ["impressions", "reach", "曝光", "展现量"],
            "avg_view_duration": ["average watch time", "avg watch time", "average view duration", "平均观看时长", "平均播放时长"],
            "watch_time_hours": ["watch time hours", "watch time", "观看时长"],
            "video_duration": ["duration", "video duration", "视频时长", "时长"],
            "retention": ["retention rate", "completion rate", "average percentage viewed", "完播率"],
            "subscribers_gained": ["followers gained", "followers", "new followers", "涨粉", "新增粉丝"],
            "likes": ["likes", "点赞"],
            "comments": ["comments", "评论"],
            "shares": ["shares", "分享"],
            "publish_date": ["publish date", "published", "date", "发布日期", "发布时间"],
        },
    },
}

PLATFORM_IDS = list(PLATFORMS.keys())


def _all_wanted_headers():
    wanted = set()
    for cfg in PLATFORMS.values():
        for aliases in cfg["aliases"].values():
            for a in aliases:
                wanted.add(clean_header(a))
    return wanted


# ---------------------------------------------------------------------------
# Fictional sample data (one per platform). Contains no real user data.
# ---------------------------------------------------------------------------

SAMPLE_CSV = {
    "youtube": """title,topic,series,thumbnail_type,hook_type,views,ctr,avg_view_duration,video_duration,retention,subscribers_gained,impressions,comments,likes,publish_date
I tested 5 AI note apps for creators,AI productivity,Tool reviews,comparison table,real test,42800,7.8,312,540,72,512,548000,286,1720,2026-10-12
Stop buying tools before checking these 7 features,SaaS buying guide,Decision guides,bold text + checklist,contrarian,61500,8.9,366,620,76,843,691000,412,2380,2026-10-10
How to build a weekly content system with AI,Creator workflow,Workflow tutorials,diagram + creator desk,step-by-step,23300,5.1,242,520,61,188,456000,129,840,2026-10-08
I let AI analyze 100 viewer comments,Audience research,Creator experiments,comments + insight map,experiment,38200,6.9,401,660,79,690,553000,344,1890,2026-10-06
A free open-source tool that replaced my spreadsheet,Open-source tools,Tool reviews,product screenshot,result first,18700,4.4,288,590,68,265,425000,96,710,2026-10-04
Can AI coding tools help non-programmers?,AI coding,Tool reviews,person + code screen,real project,72400,9.4,438,720,81,1260,770000,538,3260,2026-10-02
Why your tech videos get views but no subscribers,Channel strategy,Growth analysis,big warning + chart,problem diagnosis,30800,6.2,276,610,57,410,497000,251,1360,2026-09-30
Is it still worth starting a tech channel in 2026?,Channel strategy,Growth analysis,creator + trend chart,conclusion first,51900,7.1,344,680,70,980,731000,472,2510,2026-09-28
""",
    "douyin": """作品标题,发布时间,播放量,完播率,平均播放时长,点赞数,评论数,分享数,涨粉数
3个AI工具让效率翻倍,2026-10-12,126000,42,38,8600,520,1300,2100
别再被这些"免费"APP坑了,2026-10-10,83000,55,45,7200,690,2100,980
一分钟学会剪映自动字幕,2026-10-08,45000,68,52,5100,320,640,760
我实测了5款国产大模型,2026-10-06,210000,39,41,15400,980,2900,3600
手机相册整理保姆级教程,2026-10-04,32000,71,58,2900,180,310,420
为什么你的视频总没人看,2026-10-02,98000,47,50,8800,760,1900,1500
""",
    "xiaohongshu": """笔记标题,发布时间,曝光量,点击率,阅读量,点赞,收藏,评论,分享,涨粉数,平均阅读时长
打工人必装的5个效率APP,2026-10-12,580000,9.2,53400,4200,3800,210,900,320,48
我靠AI写周报涨薪了,2026-10-10,720000,11.5,82800,6100,5400,480,1500,610,52
新手学剪辑第3天,2026-10-08,310000,7.8,24200,1800,1600,120,420,180,44
这些护肤智商税别买,2026-10-06,910000,13.1,119200,8900,7600,690,2400,880,55
租房避坑指南（收藏版）,2026-10-04,460000,8.5,39100,2900,5200,230,700,340,49
周末在家做治愈系早餐,2026-10-02,250000,6.9,17250,1200,1100,90,260,150,39
""",
    "bilibili": """稿件标题,发布时间,播放量,完播率,平均播放时长,点赞,投币,收藏,分享,评论,新增关注
【教程】从零开始学Python,2026-10-12,156000,45,320,9800,4200,6100,900,680,2800
全网最全装机攻略,2026-10-10,240000,38,280,15000,6800,8900,1500,1200,2100
我用AI做了一个小游戏,2026-10-08,320000,52,360,24000,11000,14000,2600,1900,4800
为什么手机越用越卡,2026-10-06,98000,61,410,7200,2900,3800,540,480,1300
租房改造30天记录,2026-10-04,76000,57,300,4800,2100,2700,420,360,820
3分钟看懂显卡参数,2026-10-02,180000,49,270,13000,5900,7200,1300,980,1900
""",
    "shipinhao": """视频标题,发布时间,播放量,完播率,点赞,评论,转发,收藏,涨粉
一个动作缓解久坐腰痛,2026-10-12,88000,62,4200,180,560,320,190
3招搞定孩子不爱吃饭,2026-10-10,120000,58,6100,290,780,410,260
打工人午餐这样吃,2026-10-08,46000,71,2600,120,340,210,95
手机拍照小技巧合集,2026-10-06,95000,55,4900,210,620,380,170
为什么你总存不下钱,2026-10-04,67000,60,3500,160,430,250,120
""",
    "tiktok": """Title,Date,Views,Likes,Comments,Shares,Followers gained,Average watch time,Retention rate
3 AI tools that saved my week,2026-10-12,980000,120000,3400,8900,5200,18,44
Stop buying gadgets before this,2026-10-10,1450000,210000,6800,15400,9600,22,51
How I edit videos in 60 seconds,2026-10-08,560000,72000,2100,4300,2800,15,62
This phone hack changed everything,2026-10-06,2100000,340000,9800,22000,15000,24,49
Why your videos flop,2026-10-04,420000,41000,1600,2900,1800,17,58
Budget desk setup for students,2026-10-02,680000,85000,2700,5100,3400,16,53
""",
}


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def clean_header(s):
    return re.sub(r"[%()]", "", re.sub(r"\s+", " ", str(s or "").strip().lower().replace("\ufeff", "")))


def to_num(v):
    if v is None:
        return 0.0
    s = str(v).replace("%", "").replace(",", "").replace("，", "").strip()
    if not s:
        return 0.0
    mult = 1
    if s.lower().endswith("k"):
        mult, s = 1000, s[:-1]
    elif s.lower().endswith("m"):
        mult, s = 1000000, s[:-1]
    elif s.endswith("万"):
        mult, s = 10000, s[:-1]
    elif s.endswith("亿"):
        mult, s = 100000000, s[:-1]
    try:
        return float(s) * mult
    except ValueError:
        return 0.0


def to_seconds(v):
    s = str(v or "").strip()
    if not s:
        return 0.0
    if ":" in s:
        total = 0
        for part in s.split(":"):
            try:
                n = float(part)
            except ValueError:
                n = 0
            total = total * 60 + n
        return total
    # Chinese durations like "1分30秒", "45秒", "2分钟"
    m = re.search(r"(\d+(?:\.\d+)?)\s*分(?:钟)?", s)
    sec = re.search(r"(\d+(?:\.\d+)?)\s*秒", s)
    if m or sec:
        total = 0.0
        if m:
            total += float(m.group(1)) * 60
        if sec:
            total += float(sec.group(1))
        if total:
            return total
    low = s.lower()
    if low.endswith("min"):
        return to_num(s[:-3]) * 60
    if low.endswith("h"):
        return to_num(s[:-1]) * 3600
    if low.endswith("s") and not low.endswith("ms"):
        return to_num(s[:-1])
    return to_num(s)


def detect_delimiter(text):
    first = next((line for line in text.splitlines() if line.strip()), "")
    return max([",", "\t", ";"], key=lambda d: first.count(d))


def parse_rows(text):
    text = text.replace("\ufeff", "")
    delimiter = detect_delimiter(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    wanted = _all_wanted_headers()
    best_i, best_score = 0, -1
    for i, row in enumerate(rows[:30]):
        headers = [clean_header(x) for x in row]
        score = 0
        for h in headers:
            if h in wanted or any(w in h or h in w for w in wanted):
                score += 1
        if len(row) >= 3 and score > best_score:
            best_i, best_score = i, score
    return rows[best_i:], delimiter, best_i


def detect_platform(headers):
    cleaned = [clean_header(x) for x in headers]
    scores = {}
    for pid, cfg in PLATFORMS.items():
        score = 0
        # Strong, unique headers carry more weight.
        sig = [clean_header(x) for x in cfg.get("signature", [])]
        for h in cleaned:
            for s in sig:
                if h == s or s in h or h in s:
                    score += 3
        # Generic field matches carry less weight.
        for aliases in cfg["aliases"].values():
            wanted = [clean_header(x) for x in aliases]
            if any(h in wanted or any(w in h or h in w for w in wanted) for h in cleaned):
                score += 1
        scores[pid] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "youtube"


# ---------------------------------------------------------------------------
# Title / topic heuristics (generic across platforms)
# ---------------------------------------------------------------------------

def title_features(title):
    t = title.lower()
    features = []
    checks = [
        ("时间敏感", any(x in title for x in ["2026", "2025", "2024", "最新", "首发", "新版", "重磅", "今天", "今日", "刚刚", "9月", "10月", "11月", "12月"])),
        ("教程型", any(x in title for x in ["教程", "指南", "攻略", "干货", "方法", "技巧", "步骤", "入门", "教学", "怎么", "如何", "how to", "使用", "注册", "下载", "配置", "保姆级"])),
        ("问题解决", any(x in title for x in ["解决", "避坑", "踩坑", "翻车", "失败", "错误", "排查", "恢复", "收不到", "封号", "申诉", "别买", "别被", "为什么"])),
        ("对比测评", any(x in title for x in ["对比", "评测", "测评", "开箱", "怎么选", "哪款", "横评", "vs", "实测"])),
        ("强承诺", any(x in title for x in ["100%", "免费", "永久", "无需", "秒", "必看", "神器", "天花板", "全网", "翻倍"])),
        ("小白导向", any(x in title for x in ["小白", "零基础", "新手", "入门", "保姆级", "第1天", "第一天"])),
        ("清单合集", any(x in title for x in ["清单", "合集", "盘点", "推荐", "好物", "TOP", "Top", "必备"])),
    ]
    for name, ok in checks:
        if ok:
            features.append(name)
    return features or ["普通标题"]


def guess_topic(title):
    low = title.lower()
    rules = [
        (["telegram", "电报", "tg", "claude", "chatgpt", "openai", "gpt", "midjourney", "大模型", "人工智能"], "AI与工具"),
        (["代理", "小火箭", "shadowrocket", "clash", "surge", "vpn", "翻墙", "科学上网"], "网络工具"),
        (["google", "gmail", "谷歌", "youtube", "tiktok", "小红书", "抖音", "b站", "bilibili", "视频号"], "平台玩法"),
        (["教程", "指南", "攻略", "干货", "方法", "技巧", "步骤", "入门", "怎么", "如何", "how to", "保姆级"], "教程干货"),
        (["测评", "评测", "开箱", "对比", "怎么选", "哪款", "review", "实测"], "测评对比"),
        (["最新", "首发", "新闻", "热点", "重磅", "发布", "曝光", "今天", "今日"], "热点资讯"),
        (["为什么", "复盘", "分析", "解读", "真相", "争议", "观点", "思考"], "观点复盘"),
        (["案例", "故事", "经历", "记录", "vlog", "日常", "改造", "第一天"], "故事记录"),
        (["种草", "推荐", "好物", "清单", "合集", "必备", "省钱", "避坑"], "种草推荐"),
    ]
    for keys, val in rules:
        if any(k in low for k in keys):
            return val
    return "未分类"


def guess_series(title):
    if any(x in title for x in ["教程", "指南", "攻略", "干货", "方法", "技巧", "入门", "怎么", "如何", "保姆级"]):
        return "教程系列"
    if any(x in title for x in ["测评", "评测", "开箱", "对比", "怎么选", "哪款", "实测"]):
        return "测评系列"
    if any(x in title for x in ["最新", "首发", "新闻", "热点", "重磅", "发布"]):
        return "热点系列"
    if any(x in title for x in ["为什么", "复盘", "分析", "解读", "真相", "观点"]):
        return "观点系列"
    return "未归属系列"


def guess_thumb(title):
    if any(x in title for x in ["最新", "首发", "重磅", "今天", "今日"]):
        return "时效大字型"
    if any(x in title for x in ["对比", "怎么选", "哪款", "合集", "清单", "盘点"]):
        return "对比清单型"
    if any(x in title for x in ["避坑", "别买", "别被", "为什么", "翻车", "智商税"]):
        return "风险警示型"
    if any(x in title for x in ["100%", "免费", "永久", "无需", "神器", "翻倍"]):
        return "强利益型"
    return "未标注封面"


def guess_hook(title):
    if any(x in title for x in ["解决", "问题", "收不到", "封号", "申诉", "避坑", "别买", "为什么"]):
        return "痛点解决"
    if any(x in title for x in ["最新", "首发", "重磅", "今天", "今日"]):
        return "时间敏感"
    if any(x in title for x in ["对比", "怎么选", "哪款", "合集", "清单"]):
        return "选择困难"
    if any(x in title for x in ["100%", "免费", "永久", "无需", "神器", "翻倍"]):
        return "强承诺"
    return "未标注开头"


# ---------------------------------------------------------------------------
# Normalization: platform detection -> canonical fields
# ---------------------------------------------------------------------------

def normalize(text, platform=""):
    rows, delimiter, skipped = parse_rows(text)
    if len(rows) < 2:
        return [], {"error": "没有识别到有效表格数据。"}
    headers = [clean_header(x) for x in rows[0]]
    if platform not in PLATFORMS:
        platform = detect_platform(rows[0])
    aliases = PLATFORMS[platform]["aliases"]

    mapping = {}
    for key, alist in aliases.items():
        wanted = [clean_header(x) for x in alist]
        idx = -1
        for i, h in enumerate(headers):
            if h in wanted or any(w in h or h in w for w in wanted):
                idx = i
                break
        mapping[key] = idx

    data = []
    for row in rows[1:]:
        obj = {}
        for key in aliases:
            idx = mapping[key]
            obj[key] = row[idx].strip() if idx >= 0 and idx < len(row) else ""
        first_cell = str(obj.get("video_id", "")).lower().strip()
        if first_cell in ("total", "合计", "总计", "汇总"):
            continue
        obj["views"] = to_num(obj.get("views"))
        obj["ctr"] = to_num(obj.get("ctr"))
        obj["impressions"] = to_num(obj.get("impressions"))
        obj["watch_time_hours"] = to_num(obj.get("watch_time_hours"))
        obj["avg_view_duration"] = to_seconds(obj.get("avg_view_duration"))
        obj["video_duration"] = to_seconds(obj.get("video_duration"))
        if not obj["avg_view_duration"] and obj["watch_time_hours"] and obj["views"]:
            obj["avg_view_duration"] = obj["watch_time_hours"] * 3600 / obj["views"]
        obj["retention"] = to_num(obj.get("retention"))
        obj["subscribers_gained"] = to_num(obj.get("subscribers_gained"))
        obj["likes"] = to_num(obj.get("likes"))
        obj["comments"] = to_num(obj.get("comments"))
        obj["shares"] = to_num(obj.get("shares"))
        obj["favorites"] = to_num(obj.get("favorites"))
        obj["title"] = obj.get("title") or ("未命名内容 " + obj.get("video_id") if obj.get("video_id") else "未命名内容")
        obj["topic"] = obj.get("topic") or guess_topic(obj["title"])
        obj["series"] = obj.get("series") or guess_series(obj["title"])
        obj["thumbnail_type"] = obj.get("thumbnail_type") or guess_thumb(obj["title"])
        obj["hook_type"] = obj.get("hook_type") or guess_hook(obj["title"])
        obj["features"] = title_features(obj["title"])
        # Unified derived metrics
        obj["avgRetention"] = obj["retention"] or (obj["avg_view_duration"] / obj["video_duration"] * 100 if obj["video_duration"] else 0)
        obj["subRate"] = obj["subscribers_gained"] / obj["views"] * 1000 if obj["views"] else 0
        obj["viewPerImpression"] = obj["views"] / obj["impressions"] * 100 if obj["impressions"] else 0
        interactions = obj["likes"] + obj["comments"] + obj["shares"] + obj["favorites"]
        obj["engagement"] = interactions / obj["views"] * 100 if obj["views"] else 0
        if obj["views"] or obj["ctr"] or obj["subscribers_gained"] or obj["impressions"] or obj["likes"]:
            data.append(obj)

    meta = {
        "delimiter": "Tab" if delimiter == "\t" else delimiter,
        "skipped": skipped,
        "headers": rows[0],
        "platform": platform,
        "platform_label": PLATFORMS[platform]["label"],
        "item": PLATFORMS[platform]["item"],
    }
    return data, meta


# ---------------------------------------------------------------------------
# Aggregation + analysis (platform-agnostic)
# ---------------------------------------------------------------------------

def avg(items, key):
    return sum(x.get(key, 0) for x in items) / len(items) if items else 0


def med(vals):
    vals = [v for v in vals if v is not None]
    return statistics.median(vals) if vals else 0


def group_by(data, key):
    groups = {}
    for item in data:
        groups.setdefault(item.get(key) or "未分类", []).append(item)
    result = []
    for name, items in groups.items():
        views = sum(x["views"] for x in items)
        subs = sum(x["subscribers_gained"] for x in items)
        impressions = sum(x["impressions"] for x in items)
        result.append({
            "name": name, "count": len(items), "items": items,
            "views": views,
            "impressions": impressions,
            "ctr": avg(items, "ctr"),
            "avgRetention": avg(items, "avgRetention"),
            "subs": subs,
            "subRate": subs / views * 1000 if views else 0,
            "avgViewDuration": avg(items, "avg_view_duration"),
            "engagement": avg(items, "engagement"),
            "viewShare": 0,
            "subShare": 0,
        })
    total_views = sum(g["views"] for g in result) or 1
    total_subs = sum(g["subs"] for g in result) or 1
    for g in result:
        g["viewShare"] = g["views"] / total_views * 100
        g["subShare"] = g["subs"] / total_subs * 100
    return sorted(result, key=lambda x: x["views"], reverse=True)


def _packaging_metric(x):
    """Return the packaging 'click' proxy: CTR when present, else engagement."""
    if x.get("ctr"):
        return x["ctr"]
    return x.get("engagement", 0) * 10  # scale engagement (~0-10%) to CTR-like range


def analyze(data):
    total_views = sum(x["views"] for x in data)
    total_subs = sum(x["subscribers_gained"] for x in data)
    base = {
        "ctr": avg(data, "ctr"), "median_ctr": med([x["ctr"] for x in data]),
        "views": avg(data, "views"), "median_views": med([x["views"] for x in data]),
        "avgRetention": avg(data, "avgRetention"), "avgViewDuration": avg(data, "avg_view_duration"),
        "subRate": total_subs / total_views * 1000 if total_views else 0,
        "impressions": sum(x["impressions"] for x in data),
        "engagement": avg(data, "engagement"),
        "has_ctr": any(x["ctr"] > 0 for x in data),
    }
    topics = group_by(data, "topic")
    thumbs = group_by(data, "thumbnail_type")
    hooks = group_by(data, "hook_type")
    series = group_by(data, "series")
    features = []
    for v in data:
        for f in v["features"]:
            features.append({**v, "feature_name": f})
    feature_groups = group_by(features, "feature_name") if features else []

    base_pkg = _packaging_metric({"ctr": base["ctr"], "engagement": base["engagement"]})
    growth_engines = sorted(
        [x for x in data if x["views"] >= base["views"] and x["subRate"] >= base["subRate"]],
        key=lambda x: x["views"] * max(x["subRate"], 0.1), reverse=True)
    traffic_traps = sorted(
        [x for x in data if x["views"] >= base["views"] and x["subRate"] < base["subRate"] * 0.75],
        key=lambda x: x["views"], reverse=True)
    hidden_gems = sorted(
        [x for x in data if x["views"] < base["views"] and x["subRate"] >= base["subRate"] * 1.3 and _packaging_metric(x) >= base_pkg * 0.8],
        key=lambda x: x["subRate"], reverse=True)
    packaging_wins = sorted(data, key=lambda x: _packaging_metric(x), reverse=True)[:8]
    weak_packaging = sorted(
        [x for x in data if _packaging_metric(x) < base_pkg * 0.75 and x["subRate"] >= base["subRate"]],
        key=lambda x: x["subRate"], reverse=True)
    remake_candidates = sorted(hidden_gems + weak_packaging, key=lambda x: x["subRate"] + x["avgRetention"] / 10, reverse=True)
    return {
        "base": base,
        "topics": topics,
        "thumbs": sorted(thumbs, key=lambda x: x["ctr"] or x["engagement"], reverse=True),
        "hooks": sorted(hooks, key=lambda x: x["subRate"], reverse=True),
        "series": sorted(series, key=lambda x: (x["subRate"] * 2 + (x["ctr"] or x["engagement"] * 10) + x["count"]), reverse=True),
        "features": sorted(feature_groups, key=lambda x: x["ctr"] or x["engagement"], reverse=True),
        "top_ctr": sorted(data, key=lambda x: _packaging_metric(x), reverse=True)[:10],
        "growth_engines": growth_engines[:8],
        "traffic_traps": traffic_traps[:8],
        "hidden_gems": hidden_gems[:8],
        "packaging_wins": packaging_wins,
        "weak_packaging": weak_packaging[:8],
        "remake_candidates": remake_candidates[:10],
        "continue_topics": [g for g in topics if (g["ctr"] or g["engagement"] * 10) >= (base["ctr"] or base["engagement"] * 10) * 0.9 and g["subRate"] >= base["subRate"]][:8],
        "columns": [g for g in series if g["count"] >= 2 and (g["subRate"] >= base["subRate"] * 0.8 or g["viewShare"] >= 15)][:8],
    }


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def fmt(n, d=1):
    if n is None:
        return "0"
    if abs(n - round(n)) < 0.0001:
        return f"{int(round(n)):,}"
    return f"{n:,.{d}f}"


def pct(n):
    return f"{n:.1f}%"


def short_title(title, n=58):
    return title if len(title) <= n else title[:n] + "..."


def packaging_label(v):
    return f"CTR {pct(v['ctr'])}" if v.get("ctr") else f"互动率 {pct(v.get('engagement', 0))}"


def video_line(v):
    return (
        f"<b>{escape(short_title(v['title']))}</b><br>"
        f"<span class='muted'>播放 {fmt(v['views'])} / {packaging_label(v)} / 涨粉 {fmt(v['subscribers_gained'])}"
        f" / 每千播放涨粉 {fmt(v['subRate'], 1)} / 平均观看 {fmt(v['avg_view_duration'], 1)} 秒</span>"
    )


def lis(items, fn):
    return "<ul>" + "".join(f"<li>{fn(x)}</li>" for x in items) + "</ul>" if items else "<p class='muted'>暂无明显样本。</p>"


def badge(text, cls="info"):
    return f"<span class='badge {cls}'>{escape(text)}</span>"


# ---------------------------------------------------------------------------
# Report building
# ---------------------------------------------------------------------------

def insight_text(data, res, meta):
    base = res["base"]
    item = meta["item"]
    top_topic = res["topics"][0] if res["topics"] else None
    fan_topic = max(res["topics"], key=lambda g: g["subRate"]) if res["topics"] else None
    best_feature = res["features"][0] if res["features"] else None
    traps = res["traffic_traps"]
    pkg_word = "CTR" if base["has_ctr"] else "互动率"
    lines = []
    if top_topic:
        lines.append(f"账号当前最大的流量来源是 <b>{escape(top_topic['name'])}</b>，贡献 {pct(top_topic['viewShare'])} 播放；但真正要看它是否也贡献涨粉。")
    if fan_topic:
        lines.append(f"最像长期增长资产的题材是 <b>{escape(fan_topic['name'])}</b>，每千播放涨粉 {fmt(fan_topic['subRate'], 1)}，高于全账号基准 {fmt(base['subRate'], 1)}。")
    if best_feature:
        lines.append(f"标题包装里最有效的模式是 <b>{escape(best_feature['name'])}</b>，平均 {pkg_word} {pct(best_feature['ctr'] or best_feature['engagement'] * 10)}。这类表达应该沉淀成固定标题公式。")
    if traps:
        lines.append(f"有 {len(traps)} 条{escape(item)}属于“播放不低但涨粉偏弱”，说明部分选题可能带来泛流量，但没有强化账号定位。")
    if base["has_ctr"]:
        if base["ctr"] >= 10:
            lines.append(f"整体 {pkg_word} 已经很强，短板更可能在题材承接、内容内信任建立和结尾关注理由，而不是单纯换封面。")
        elif base["ctr"] < 6:
            lines.append(f"整体 {pkg_word} 偏低，优先优化标题/封面，而不是急着扩大选题范围。")
        else:
            lines.append(f"整体 {pkg_word} 中等偏可用，下一步应该比较“高 {pkg_word} 但低涨粉”和“低 {pkg_word} 但高涨粉”，找到包装与定位的交集。")
    else:
        if base["engagement"] >= 8:
            lines.append("该平台数据未提供 CTR，但互动率较高，说明内容质量与受众共鸣不错，重点看选题和转粉效率。")
        else:
            lines.append("该平台数据未提供 CTR，建议优先提升互动率（点赞/评论/转发），再配合涨粉效率判断选题方向。")
    return lis(lines, lambda x: x)


def title_formula_examples(res):
    formulas = []
    features = {g["name"]: g for g in res["features"]}
    if "时间敏感" in features:
        formulas.append("【最新】+ 明确平台/工具 + 使用前先看 + 常见问题")
    if "问题解决" in features:
        formulas.append("具体失败场景 + 原因解释 + 排查清单 + 风险提醒")
    if "对比测评" in features:
        formulas.append("N 款对比 + 适合谁 + 怎么选 + 避坑")
    if "小白导向" in features:
        formulas.append("小白入门 + 5分钟上手 + 先讲限制 + 再讲流程")
    if "清单合集" in features:
        formulas.append("清单/合集 + 场景化 + 数量 + 保存提醒")
    if "强承诺" in features:
        formulas.append("强利益点可以保留，但建议从“100%/永久免费”改成“适用条件/实测结果”，降低信任风险")
    return lis(formulas[:6], lambda x: x)


def next_week_plan(res):
    topics = res["continue_topics"] or res["topics"][:3]
    ideas = []
    for g in topics[:4]:
        name = g["name"]
        ideas.append(f"{name}｜更新版：补最新变化、适用条件、失败原因，标题走“最新+问题排查”。")
        ideas.append(f"{name}｜对比版：把用户选择困难讲清楚，标题走“N款怎么选”。")
    ideas.append("复盘型内容｜把一条高播放低涨粉的内容拆成案例：为什么有人看但不关注？这类内容能强化你的专业判断。")
    return lis(ideas[:8], lambda x: x)


def strategic_actions(res, meta):
    item = meta["item"]
    actions = [
        "把内容分成三类管理：拉新题材、信任题材、转粉题材。不要只按播放量判断成败。",
        "对高点击低涨粉内容，保留包装方式，但把内容开头改成“适合谁/不适合谁”，减少泛流量误点。",
        "对高涨粉低播放内容，优先重做标题和封面，不要轻易放弃题材。",
        "每周固定做 1 条热点更新、1 条问题排查、1 条对比测评，连续四周看哪条线涨粉效率最高。",
        "标题里的强承诺表达要转成“实测/条件/限制”，长期更利于建立可信人设。",
    ]
    if res["traffic_traps"]:
        actions.insert(1, "本周先处理“播放高但不涨粉”的内容：检查标题是否吸引了非目标用户，结尾是否缺少关注理由。")
    if res["hidden_gems"]:
        actions.insert(2, "隐藏宝藏内容值得二次包装：它们播放不高但转粉强，说明题材对精准用户有价值。")
    return lis(actions, lambda x: x)


def render_topic_matrix(res):
    rows = []
    base = res["base"]
    for g in res["topics"]:
        if g["views"] >= base["views"] and g["subRate"] >= base["subRate"]:
            zone = badge("增长引擎", "good")
        elif g["views"] >= base["views"] and g["subRate"] < base["subRate"]:
            zone = badge("流量陷阱", "warn")
        elif g["views"] < base["views"] and g["subRate"] >= base["subRate"]:
            zone = badge("隐藏宝藏", "info")
        else:
            zone = badge("低优先级", "bad")
        pkg = pct(g["ctr"]) if g["ctr"] else pct(g["engagement"])
        rows.append(f"<tr><td>{escape(g['name'])}</td><td>{zone}</td><td>{fmt(g['views'])}</td><td>{pct(g['viewShare'])}</td><td>{fmt(g['subs'])}</td><td>{fmt(g['subRate'], 1)}</td><td>{pkg}</td><td>{g['count']}</td></tr>")
    return "<div class='tablewrap'><table><tr><th>题材</th><th>判断</th><th>播放</th><th>播放占比</th><th>涨粉</th><th>千播放涨粉</th><th>点击/互动</th><th>样本</th></tr>" + "".join(rows) + "</table></div>"


def render_report(data, meta):
    res = analyze(data)
    item = meta["item"]
    label = meta["platform_label"]
    total_views = sum(x["views"] for x in data)
    total_subs = sum(x["subscribers_gained"] for x in data)
    total_impressions = sum(x["impressions"] for x in data)
    pkg_word = "CTR" if res["base"]["has_ctr"] else "互动率"
    report = f"""
    <div class='status ok'>生成成功：识别平台 <b>{escape(label)}</b>，共 {len(data)} 条{escape(item)}，自动跳过 {meta.get('skipped', 0)} 行说明文字，分隔符 {escape(str(meta.get('delimiter')))}。</div>
    <div class='metrics'>
      <div class='metric'><div>内容数</div><b>{len(data)}</b><span>样本规模</span></div>
      <div class='metric'><div>总播放</div><b>{fmt(total_views)}</b><span>平均 {fmt(res['base']['views'])}/条</span></div>
      <div class='metric'><div>平均 {pkg_word}</div><b>{pct(res['base']['ctr']) if res['base']['has_ctr'] else pct(res['base']['engagement'])}</b><span>{'中位数 ' + pct(res['base']['median_ctr']) if res['base']['has_ctr'] else '互动率'}</span></div>
      <div class='metric'><div>总涨粉</div><b>{fmt(total_subs)}</b><span>{fmt(res['base']['subRate'], 1)}/千播放</span></div>
      <div class='metric'><div>总曝光</div><b>{fmt(total_impressions)}</b><span>系统推荐机会</span></div>
      <div class='metric'><div>平均观看</div><b>{fmt(res['base']['avgViewDuration'], 1)}s</b><span>由后台数据换算</span></div>
    </div>

    <section class='wide'><h2>一、账号增长结论，不只是数据</h2>{insight_text(data, res, meta)}</section>

    <div class='report'>
      <section><h2>二、真正的增长引擎</h2><p class='muted'>播放和涨粉效率都高，优先复制它们的题材、标题结构和内容承诺。</p>{lis(res['growth_engines'], video_line)}</section>
      <section><h2>三、播放高但不涨粉：流量陷阱</h2><p class='muted'>这类内容可能吸引了泛用户，或者内容没有把观众转化为账号认同。</p>{lis(res['traffic_traps'], video_line)}</section>
      <section><h2>四、隐藏宝藏：值得重做</h2><p class='muted'>播放不高但转粉强，说明题材对精准用户有价值，应该换标题/封面再打一遍。</p>{lis(res['hidden_gems'], video_line)}</section>
      <section><h2>五、包装胜利：高{pkg_word}内容</h2><p class='muted'>这些内容说明用户愿意点/愿意互动，重点拆标题承诺和封面信息密度。</p>{lis(res['packaging_wins'], video_line)}</section>
    </div>

    <section class='wide'><h2>六、题材四象限：以后拍什么，看这里</h2>{render_topic_matrix(res)}</section>

    <div class='report'>
      <section><h2>七、标题模式拆解</h2><p class='muted'>不是简单看哪个标题高，而是看哪些表达模式反复有效。</p>{lis(res['features'][:8], lambda g: f"<b>{escape(g['name'])}</b>：平均 {pkg_word} {pct(g['ctr']) if g['ctr'] else pct(g['engagement'])}，播放 {fmt(g['views'])}，涨粉 {fmt(g['subs'])}，样本 {g['count']} 条")}</section>
      <section><h2>八、可复用标题公式</h2>{title_formula_examples(res)}</section>
      <section><h2>九、栏目化建议</h2><p class='muted'>栏目不是播放高就做，而是要能持续解释同一种用户问题。</p>{lis(res['columns'], lambda g: f"<b>{escape(g['name'])}</b>：{g['count']} 条，播放占比 {pct(g['viewShare'])}，千播放涨粉 {fmt(g['subRate'], 1)}，建议固定封面模板和片头承诺。")}</section>
      <section><h2>十、下周具体选题方向</h2>{next_week_plan(res)}</section>
    </div>

    <section class='wide'><h2>十一、旧内容二次包装清单</h2><p class='muted'>这些内容建议优先改标题/封面，或做更新版。目标不是重复发布，而是复用已经验证过的用户需求。</p>{lis(res['remake_candidates'], lambda v: video_line(v) + f"<br><span class='advice'>建议：保留题材，改成更明确的适用人群 + 失败原因 + 实测结论。</span>")}</section>

    <section class='wide'><h2>十二、可执行动作</h2>{strategic_actions(res, meta)}</section>

    <h2>单条内容明细</h2>
    <div class='tablewrap'><table><tr><th>标题</th><th>播放</th><th>{pkg_word}</th><th>曝光</th><th>涨粉</th><th>千播放涨粉</th><th>平均观看</th><th>题材</th><th>系列</th><th>标题标签</th></tr>
    {''.join(f"<tr><td>{escape(v['title'])}</td><td>{fmt(v['views'])}</td><td>{pct(v['ctr']) if v['ctr'] else pct(v['engagement'])}</td><td>{fmt(v['impressions'])}</td><td>{fmt(v['subscribers_gained'])}</td><td>{fmt(v['subRate'], 1)}</td><td>{fmt(v['avg_view_duration'], 1)}s</td><td>{escape(v['topic'])}</td><td>{escape(v['series'])}</td><td>{''.join(badge(x) for x in v['features'])}</td></tr>" for v in sorted(data, key=lambda x: x['views'], reverse=True))}
    </table></div>
    """
    return report


# ---------------------------------------------------------------------------
# HTML page
# ---------------------------------------------------------------------------

CSS = """
body{margin:0;background:#f8fafc;color:#1f2937;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif}
.wrap{max-width:1220px;margin:0 auto;padding:24px}
.hero,.card,section,.metric{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px;margin-bottom:16px}
h1{margin:0 0 8px;font-size:28px}
h2{font-size:20px;margin:0 0 12px}
h3{font-size:16px}
p,li{line-height:1.75;color:#4b5563}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}
textarea{width:100%;height:220px;border:1px solid #d1d5db;border-radius:12px;padding:12px;font-family:Consolas,monospace;font-size:12px;box-sizing:border-box}
button,.btn{border:0;border-radius:10px;background:#2563eb;color:white;padding:10px 14px;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}
.secondary{background:#eef2ff;color:#3730a3}
input[type=file],select{border:1px solid #d1d5db;border-radius:10px;padding:8px;background:white;font-size:14px}
.formrow{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:8px 0}
.status{padding:10px 12px;border-radius:10px;margin:12px 0}
.ok{background:#dcfce7;color:#166534}
.err{background:#fee2e2;color:#991b1b}
.metrics{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:16px 0}
.metric b{display:block;font-size:24px;margin:4px 0}
.metric span{font-size:12px;color:#6b7280}
.report{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.wide{grid-column:1/-1}
.muted{color:#6b7280;font-size:13px}
.advice{color:#92400e;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;vertical-align:top}
th{background:#f9fafb;position:sticky;top:0}
.tablewrap{max-height:680px;overflow:auto;background:white;border:1px solid #e5e7eb;border-radius:12px}
.badge{display:inline-block;border-radius:999px;padding:3px 8px;margin:2px;background:#dbeafe;color:#1e40af;font-size:12px}
.badge.good{background:#dcfce7;color:#166534}
.badge.warn{background:#fef3c7;color:#92400e}
.badge.bad{background:#fee2e2;color:#991b1b}
.badge.info{background:#dbeafe;color:#1e40af}
ul{padding-left:20px;margin-top:6px}
@media(max-width:1000px){.grid,.report{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,1fr)}}
"""


def platform_options(selected=""):
    opts = ["<option value=''>自动检测</option>"]
    for pid in PLATFORM_IDS:
        label = PLATFORMS[pid]["label"]
        sel = " selected" if pid == selected else ""
        opts.append(f"<option value='{pid}'{sel}>{label}</option>")
    return "".join(opts)


def page(report="", textarea="", platform=""):
    return f"""<!doctype html><meta charset='utf-8'><title>全网新媒体增长深度复盘工具</title>
<style>{CSS}</style>
<div class='wrap'>
  <div class='hero'>
    <h1>全网新媒体增长深度复盘工具</h1>
    <p>上传或粘贴任意平台（YouTube / 抖音 / 小红书 / B站 / 视频号 / TikTok）的后台导出数据，自动生成账号增长诊断报告，帮助你分析选题表现、标题与封面包装、播放与涨粉效率、流量陷阱、栏目化机会以及下一步内容策略。</p>
  </div>
  <div class='grid'>
    <div class='card'>
      <h2>导入或粘贴数据</h2>
      <form method='post' enctype='multipart/form-data'>
        <div class='formrow'>
          <label>数据平台：</label>
          <select name='platform'>{platform_options(platform)}</select>
        </div>
        <textarea name='csv_text' placeholder='粘贴后台导出的 CSV / 表格内容（标题、播放量、涨粉数、点击率或完播率等列）'>{escape(textarea)}</textarea>
        <div class='formrow'>
          <input type='file' name='csv_file' accept='.csv,.tsv,.txt'>
          <button type='submit'>生成深度复盘报告</button>
          <button class='secondary' name='use_sample' value='1'>使用示例数据</button>
        </div>
      </form>
    </div>
    <div class='card'>
      <h2>这个工具可以深度分析什么</h2>
      <ul>
        <li>自动识别平台，并兼容各平台后台导出的不同字段名。</li>
        <li>分析哪些内容真正带来账号增长，哪些只是带来泛流量。</li>
        <li>分析标题、封面和开头钩子中哪些包装模式更容易获得点击（无 CTR 平台自动改用互动率）。</li>
        <li>分析不同题材、系列和内容类型的播放效率与涨粉效率。</li>
        <li>分析高播放低涨粉的内容，识别内容定位和受众匹配问题。</li>
        <li>分析哪些旧内容值得二次包装，哪些题材值得继续做成固定栏目。</li>
        <li>分析下周应该优先测试的选题方向和内容策略。</li>
      </ul>
    </div>
  </div>
  {report}
</div>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def send_html(self, html):
        data = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self.send_html(page("", ""))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")
        text = ""
        platform = ""
        if "multipart/form-data" in ctype:
            msg = BytesParser(policy=default).parsebytes(("Content-Type: " + ctype + "\r\n\r\n").encode() + raw)
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if name == "use_sample":
                    text = SAMPLE_CSV.get(platform, SAMPLE_CSV["youtube"])
                    break
                if name == "platform":
                    platform = (part.get_payload(decode=True) or b"").decode("utf-8", errors="replace").strip()
                if name == "csv_file" and part.get_filename():
                    payload = part.get_payload(decode=True) or b""
                    if payload:
                        text = payload.decode("utf-8-sig", errors="replace")
                elif name == "csv_text" and not text:
                    payload = part.get_payload(decode=True) or b""
                    text = payload.decode("utf-8-sig", errors="replace")
        else:
            form = parse_qs(raw.decode("utf-8", errors="replace"))
            text = form.get("csv_text", [""])[0]
            platform = form.get("platform", [""])[0]
            if "use_sample" in form:
                text = SAMPLE_CSV.get(platform, SAMPLE_CSV["youtube"])
        try:
            data, meta = normalize(text, platform)
            if data:
                report = render_report(data, meta)
                platform = meta["platform"]
            else:
                report = "<div class='status err'>没有识别到有效内容数据，请检查表头是否包含标题、播放量、涨粉数等列。</div>"
        except Exception as e:
            report = f"<div class='status err'>生成失败：{escape(str(e))}</div>"
        self.send_html(page(report, text[:20000], platform))


if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"New-media growth review server running at http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
