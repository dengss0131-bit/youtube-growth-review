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

ALIASES = {
    "title": ["title", "video title", "标题", "视频标题"],
    "video_id": ["content", "video", "video id", "视频", "内容"],
    "topic": ["topic", "题材", "主题", "选题"],
    "series": ["series", "系列", "栏目"],
    "thumbnail_type": ["thumbnail_type", "thumbnail type", "缩略图类型", "封面类型", "thumbnail"],
    "hook_type": ["hook_type", "hook type", "开头类型", "钩子", "hook"],
    "views": ["views", "观看次数", "播放量", "观看", "views count"],
    "ctr": ["ctr", "impressions click-through rate", "impressions ctr", "thumbnail click-through rate", "thumbnail click-through rate %", "展示点击率", "缩略图点击率", "点击率"],
    "avg_view_duration": ["avg_view_duration", "average view duration", "平均观看时长", "平均观看秒数", "avd"],
    "watch_time_hours": ["watch time hours", "watch time", "观看时长 小时", "观看时长"],
    "video_duration": ["video_duration", "duration", "视频时长", "总时长", "时长"],
    "avg_percentage_viewed": ["average percentage viewed", "average percentage viewed %", "平均观看百分比", "平均观看百分比 %"],
    "retention_30s": ["retention_30s", "30秒留存", "30s留存", "前30秒留存"],
    "subscribers_gained": ["subscribers_gained", "subscribers", "subscribers gained", "涨粉", "新增订阅", "订阅者", "订阅增加"],
    "impressions": ["impressions", "thumbnail impressions", "展示次数", "缩略图展示次数", "曝光"],
    "comments": ["comments", "评论"],
    "likes": ["likes", "点赞"],
    "publish_date": ["publish_date", "published", "publish date", "video publish time", "发布日期", "发布时间", "date", "日期"],
}

SAMPLE_CSV = """﻿title,topic,series,thumbnail_type,hook_type,views,ctr,avg_view_duration,video_duration,retention_30s,subscribers_gained,impressions,comments,likes,publish_date
I tested 5 AI note apps for creators,AI productivity,Tool reviews,comparison table,real test,42800,7.8,312,540,72,512,548000,286,1720,2026-10-12
Stop buying tools before checking these 7 features,SaaS buying guide,Decision guides,bold text + checklist,contrarian,61500,8.9,366,620,76,843,691000,412,2380,2026-10-10
How to build a weekly content system with AI,Creator workflow,Workflow tutorials,diagram + creator desk,step-by-step,23300,5.1,242,520,61,188,456000,129,840,2026-10-08
I let AI analyze 100 viewer comments,Audience research,Creator experiments,comments + insight map,experiment,38200,6.9,401,660,79,690,553000,344,1890,2026-10-06
A free open-source tool that replaced my spreadsheet,Open-source tools,Tool reviews,product screenshot,result first,18700,4.4,288,590,68,265,425000,96,710,2026-10-04
Can AI coding tools help non-programmers?,AI coding,Tool reviews,person + code screen,real project,72400,9.4,438,720,81,1260,770000,538,3260,2026-10-02
Why your tech videos get views but no subscribers,Channel strategy,Growth analysis,big warning + chart,problem diagnosis,30800,6.2,276,610,57,410,497000,251,1360,2026-09-30
Is it still worth starting a tech channel in 2026?,Channel strategy,Growth analysis,creator + trend chart,conclusion first,51900,7.1,344,680,70,980,731000,472,2510,2026-09-28
"""

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
    return to_num(s)

def detect_delimiter(text):
    first = next((line for line in text.splitlines() if line.strip()), "")
    return max([",", "\t", ";"], key=lambda d: first.count(d))

def parse_rows(text):
    text = text.replace("\ufeff", "")
    delimiter = detect_delimiter(text)
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [[cell.strip() for cell in row] for row in rows if any(cell.strip() for cell in row)]
    best_i, best_score = 0, -1
    for i, row in enumerate(rows[:30]):
        headers = [clean_header(x) for x in row]
        score = 0
        for aliases in ALIASES.values():
            wanted = [clean_header(x) for x in aliases]
            if any(h in wanted for h in headers):
                score += 1
        if len(row) >= 3 and score > best_score:
            best_i, best_score = i, score
    return rows[best_i:], delimiter, best_i

def title_features(title):
    t = title.lower()
    features = []
    checks = [
        ("时间敏感", any(x in title for x in ["2026", "2025", "最新", "首发", "最新版", "9月"])),
        ("教程型", any(x in title for x in ["教程", "使用", "注册", "登录", "下载", "配置", "入门"])),
        ("问题解决", any(x in title for x in ["解决", "收不到", "封号", "申诉", "恢复", "风控", "排查", "泄露"])),
        ("工具对比", any(x in title for x in ["对比", "怎么选", "哪款", "全解析", "最全"])),
        ("强承诺", any(x in title for x in ["100%", "免费", "永久", "无需", "秒", "完美"])),
        ("小白导向", any(x in title for x in ["小白", "零基础", "新手", "入门"])),
        ("平台明确", any(x.lower() in t for x in ["telegram", "claude", "clash", "google", "gmail", "twitter", "x（", "surge", "stash", "hiddify", "karing"])),
    ]
    for name, ok in checks:
        if ok:
            features.append(name)
    return features or ["普通标题"]

def guess_topic(title):
    rules = [
        (["telegram", "电报", "tg"], "Telegram/社交工具"),
        (["x（", "twitter", "推特"], "X/Twitter"),
        (["clash", "surge", "stash", "hiddify", "karing", "mihomo", "代理", "小火箭", "shadowrocket"], "代理工具"),
        (["住宅代理", "ip"], "代理/IP"),
        (["claude", "chatgpt", "ai", "code"], "AI工具"),
        (["google", "gmail", "谷歌"], "Google账号"),
        (["虚拟定位", "gps"], "手机工具"),
        (["yaml", "dns", "分流", "链式"], "进阶配置"),
    ]
    low = title.lower()
    for keys, val in rules:
        if any(k.lower() in low for k in keys):
            return val
    return "未分类"

def guess_series(title):
    if any(x in title for x in ["教程", "使用", "注册", "登录", "下载", "配置"]):
        return "小白教程"
    if any(x in title for x in ["对比", "怎么选", "哪款", "全解析", "最全"]):
        return "工具对比"
    if any(x in title for x in ["封号", "申诉", "恢复", "风控", "排查", "泄露"]):
        return "问题排查"
    if any(x in title for x in ["最新", "首发", "最新版"]):
        return "热点更新"
    return "未归属系列"

def guess_thumb(title):
    if any(x in title for x in ["最新", "首发", "最新版"]):
        return "年份最新+大字标题"
    if any(x in title for x in ["对比", "怎么选", "哪款", "全解析"]):
        return "工具对比型"
    if any(x in title for x in ["封号", "问题", "申诉", "风控", "泄露"]):
        return "风险警示型"
    if any(x in title for x in ["100%", "免费", "永久", "无需"]):
        return "强利益承诺型"
    return "未标注封面"

def guess_hook(title):
    if any(x in title for x in ["解决", "问题", "收不到", "封号", "申诉", "恢复"]):
        return "痛点解决"
    if any(x in title for x in ["最新", "首发", "最新版"]):
        return "时间敏感"
    if any(x in title for x in ["对比", "怎么选", "哪款"]):
        return "选择困难"
    if any(x in title for x in ["100%", "免费", "永久", "无需"]):
        return "强承诺"
    return "未标注开头"

def normalize(text):
    rows, delimiter, skipped = parse_rows(text)
    if len(rows) < 2:
        return [], {"error": "没有识别到有效表格数据。"}
    headers = [clean_header(x) for x in rows[0]]
    mapping = {}
    for key, aliases in ALIASES.items():
        wanted = [clean_header(x) for x in aliases]
        idx = -1
        for i, h in enumerate(headers):
            if h in wanted or any(w in h or h in w for w in wanted):
                idx = i
                break
        mapping[key] = idx
    data = []
    for row in rows[1:]:
        obj = {}
        for key in ALIASES:
            idx = mapping[key]
            obj[key] = row[idx].strip() if idx >= 0 and idx < len(row) else ""
        if str(obj.get("video_id", "")).lower() == "total" or str(obj.get("title", "")).lower() == "total":
            continue
        obj["views"] = to_num(obj["views"])
        obj["ctr"] = to_num(obj["ctr"])
        obj["impressions"] = to_num(obj["impressions"])
        obj["watch_time_hours"] = to_num(obj["watch_time_hours"])
        obj["avg_view_duration"] = to_seconds(obj["avg_view_duration"])
        obj["video_duration"] = to_seconds(obj["video_duration"])
        if not obj["avg_view_duration"] and obj["watch_time_hours"] and obj["views"]:
            obj["avg_view_duration"] = obj["watch_time_hours"] * 3600 / obj["views"]
        obj["retention_30s"] = to_num(obj["retention_30s"])
        obj["avg_percentage_viewed"] = to_num(obj["avg_percentage_viewed"])
        obj["subscribers_gained"] = to_num(obj["subscribers_gained"])
        obj["comments"] = to_num(obj["comments"])
        obj["likes"] = to_num(obj["likes"])
        obj["title"] = obj["title"] or ("未命名视频 " + obj["video_id"] if obj["video_id"] else "未命名视频")
        obj["topic"] = obj["topic"] or guess_topic(obj["title"])
        obj["series"] = obj["series"] or guess_series(obj["title"])
        obj["thumbnail_type"] = obj["thumbnail_type"] or guess_thumb(obj["title"])
        obj["hook_type"] = obj["hook_type"] or guess_hook(obj["title"])
        obj["features"] = title_features(obj["title"])
        obj["avgRetention"] = obj["avg_percentage_viewed"] or (obj["avg_view_duration"] / obj["video_duration"] * 100 if obj["video_duration"] else 0)
        obj["subRate"] = obj["subscribers_gained"] / obj["views"] * 1000 if obj["views"] else 0
        obj["viewPerImpression"] = obj["views"] / obj["impressions"] * 100 if obj["impressions"] else 0
        if obj["views"] or obj["ctr"] or obj["subscribers_gained"] or obj["impressions"]:
            data.append(obj)
    meta = {"delimiter": "Tab" if delimiter == "\t" else delimiter, "skipped": skipped, "headers": rows[0]}
    return data, meta

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
            "retention_30s": avg(items, "retention_30s"),
            "subs": subs,
            "subRate": subs / views * 1000 if views else 0,
            "avgViewDuration": avg(items, "avg_view_duration"),
            "viewShare": 0,
            "subShare": 0,
        })
    total_views = sum(g["views"] for g in result) or 1
    total_subs = sum(g["subs"] for g in result) or 1
    for g in result:
        g["viewShare"] = g["views"] / total_views * 100
        g["subShare"] = g["subs"] / total_subs * 100
    return sorted(result, key=lambda x: x["views"], reverse=True)

def analyze(data):
    total_views = sum(x["views"] for x in data)
    total_subs = sum(x["subscribers_gained"] for x in data)
    base = {
        "ctr": avg(data, "ctr"), "median_ctr": med([x["ctr"] for x in data]),
        "views": avg(data, "views"), "median_views": med([x["views"] for x in data]),
        "avgRetention": avg(data, "avgRetention"), "avgViewDuration": avg(data, "avg_view_duration"),
        "subRate": total_subs / total_views * 1000 if total_views else 0,
        "impressions": sum(x["impressions"] for x in data),
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
    growth_engines = sorted([x for x in data if x["views"] >= base["views"] and x["subRate"] >= base["subRate"]], key=lambda x: x["views"] * max(x["subRate"], 0.1), reverse=True)
    traffic_traps = sorted([x for x in data if x["views"] >= base["views"] and x["subRate"] < base["subRate"] * 0.75], key=lambda x: x["views"], reverse=True)
    hidden_gems = sorted([x for x in data if x["views"] < base["views"] and x["subRate"] >= base["subRate"] * 1.3 and x["ctr"] >= base["ctr"] * 0.8], key=lambda x: x["subRate"], reverse=True)
    packaging_wins = sorted([x for x in data if x["ctr"] >= base["ctr"] * 1.25], key=lambda x: x["ctr"], reverse=True)
    weak_packaging = sorted([x for x in data if x["ctr"] < base["ctr"] * 0.75 and x["subRate"] >= base["subRate"]], key=lambda x: x["subRate"], reverse=True)
    remake_candidates = sorted(hidden_gems + weak_packaging, key=lambda x: x["subRate"] + x["avgRetention"] / 10, reverse=True)
    return {
        "base": base,
        "topics": topics,
        "thumbs": sorted(thumbs, key=lambda x: x["ctr"], reverse=True),
        "hooks": sorted(hooks, key=lambda x: x["subRate"], reverse=True),
        "series": sorted(series, key=lambda x: (x["subRate"] * 2 + x["ctr"] + x["count"]), reverse=True),
        "features": sorted(feature_groups, key=lambda x: x["ctr"], reverse=True),
        "top_ctr": sorted(data, key=lambda x: x["ctr"], reverse=True)[:10],
        "growth_engines": growth_engines[:8],
        "traffic_traps": traffic_traps[:8],
        "hidden_gems": hidden_gems[:8],
        "packaging_wins": packaging_wins[:8],
        "weak_packaging": weak_packaging[:8],
        "remake_candidates": remake_candidates[:10],
        "continue_topics": [g for g in topics if g["ctr"] >= base["ctr"] * 0.9 and g["subRate"] >= base["subRate"]][:8],
        "columns": [g for g in series if g["count"] >= 2 and (g["subRate"] >= base["subRate"] * 0.8 or g["viewShare"] >= 15)][:8],
    }

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

def video_line(v):
    return f"<b>{escape(short_title(v['title']))}</b><br><span class='muted'>播放 {fmt(v['views'])} / CTR {pct(v['ctr'])} / 涨粉 {fmt(v['subscribers_gained'])} / 每千播放涨粉 {fmt(v['subRate'], 1)} / 平均观看 {fmt(v['avg_view_duration'], 1)} 秒</span>"

def lis(items, fn):
    return "<ul>" + "".join(f"<li>{fn(x)}</li>" for x in items) + "</ul>" if items else "<p class='muted'>暂无明显样本。</p>"

def badge(text, cls="info"):
    return f"<span class='badge {cls}'>{escape(text)}</span>"

def insight_text(data, res):
    base = res["base"]
    top_topic = res["topics"][0] if res["topics"] else None
    fan_topic = max(res["topics"], key=lambda g: g["subRate"]) if res["topics"] else None
    best_feature = res["features"][0] if res["features"] else None
    traps = res["traffic_traps"]
    lines = []
    if top_topic:
        lines.append(f"频道当前最大的流量来源是 <b>{escape(top_topic['name'])}</b>，贡献 {pct(top_topic['viewShare'])} 播放；但真正要看它是否也贡献订阅。")
    if fan_topic:
        lines.append(f"最像长期增长资产的题材是 <b>{escape(fan_topic['name'])}</b>，每千播放涨粉 {fmt(fan_topic['subRate'], 1)}，高于全站基准 {fmt(base['subRate'], 1)}。")
    if best_feature:
        lines.append(f"标题包装里最有效的模式是 <b>{escape(best_feature['name'])}</b>，平均 CTR {pct(best_feature['ctr'])}。这类表达应该沉淀成固定标题公式。")
    if traps:
        lines.append(f"有 {len(traps)} 条视频属于“播放不低但吸粉偏弱”，说明部分选题可能带来泛流量，但没有强化频道定位。")
    if base["ctr"] >= 10:
        lines.append("整体 CTR 已经很强，短板更可能在题材承接、视频内信任建立和结尾订阅理由，而不是单纯换封面。")
    elif base["ctr"] < 6:
        lines.append("整体 CTR 偏低，优先优化标题/缩略图，而不是急着扩大选题范围。")
    else:
        lines.append("整体 CTR 中等偏可用，下一步应该比较“高 CTR 但低涨粉”和“低 CTR 但高涨粉”，找到包装与定位的交集。")
    return lis(lines, lambda x: x)

def title_formula_examples(res):
    formulas = []
    features = {g["name"]: g for g in res["features"]}
    if "时间敏感" in features:
        formulas.append("【2026最新】+ 明确工具/平台 + 使用前先看 + 常见问题")
    if "问题解决" in features:
        formulas.append("具体失败场景 + 原因解释 + 排查清单 + 风险提醒")
    if "工具对比" in features:
        formulas.append("N款工具对比 + 适合谁 + 怎么选 + 避坑")
    if "小白导向" in features:
        formulas.append("小白入门 + 5分钟上手 + 先讲限制 + 再讲流程")
    if "强承诺" in features:
        formulas.append("强利益点可以保留，但建议从“100%/永久免费”改成“适用条件/实测结果”，降低信任风险")
    return lis(formulas[:6], lambda x: x)

def next_week_plan(res):
    topics = res["continue_topics"] or res["topics"][:3]
    ideas = []
    for g in topics[:4]:
        name = g["name"]
        ideas.append(f"{name}｜更新版：补最新变化、适用条件、失败原因，标题走“最新+问题排查”。")
        ideas.append(f"{name}｜对比版：把用户选择困难讲清楚，标题走“N款工具怎么选”。")
    ideas.append("复盘型内容｜把一条高播放低涨粉视频拆成案例：为什么有人看但不订阅？这类内容能强化你的专业判断。")
    return lis(ideas[:8], lambda x: x)

def strategic_actions(res):
    actions = [
        "把视频分成三类管理：拉新题材、信任题材、转粉题材。不要只按播放量判断成败。",
        "对高 CTR 低涨粉视频，保留包装方式，但把内容开头改成“适合谁/不适合谁”，减少泛流量误点。",
        "对高涨粉低播放视频，优先重做标题和封面，不要轻易放弃题材。",
        "每周固定做 1 条热点更新、1 条问题排查、1 条工具对比，连续四周看哪条线涨粉效率最高。",
        "标题里的强承诺表达要转成“实测/条件/限制”，长期更利于建立可信科技博主人设。",
    ]
    if res["traffic_traps"]:
        actions.insert(1, "本周先处理“播放高但不涨粉”的视频：检查标题是否吸引了非目标用户，结尾是否缺少频道价值承诺。")
    if res["hidden_gems"]:
        actions.insert(2, "隐藏宝藏视频值得二次包装：它们播放不高但转粉强，说明题材对精准用户有价值。")
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
        rows.append(f"<tr><td>{escape(g['name'])}</td><td>{zone}</td><td>{fmt(g['views'])}</td><td>{pct(g['viewShare'])}</td><td>{fmt(g['subs'])}</td><td>{fmt(g['subRate'], 1)}</td><td>{pct(g['ctr'])}</td><td>{g['count']}</td></tr>")
    return "<div class='tablewrap'><table><tr><th>题材</th><th>判断</th><th>播放</th><th>播放占比</th><th>涨粉</th><th>千播放涨粉</th><th>CTR</th><th>样本</th></tr>" + "".join(rows) + "</table></div>"

def render_report(data, meta):
    res = analyze(data)
    total_views = sum(x["views"] for x in data)
    total_subs = sum(x["subscribers_gained"] for x in data)
    total_impressions = sum(x["impressions"] for x in data)
    report = f"""
    <div class='status ok'>生成成功：识别 {len(data)} 条视频，自动跳过 {meta.get('skipped', 0)} 行说明文字，分隔符 {escape(str(meta.get('delimiter')))}。</div>
    <div class='metrics'>
      <div class='metric'><div>视频数</div><b>{len(data)}</b><span>样本规模</span></div>
      <div class='metric'><div>总播放</div><b>{fmt(total_views)}</b><span>平均 {fmt(res['base']['views'])}/条</span></div>
      <div class='metric'><div>平均 CTR</div><b>{pct(res['base']['ctr'])}</b><span>中位数 {pct(res['base']['median_ctr'])}</span></div>
      <div class='metric'><div>总涨粉</div><b>{fmt(total_subs)}</b><span>{fmt(res['base']['subRate'], 1)}/千播放</span></div>
      <div class='metric'><div>总曝光</div><b>{fmt(total_impressions)}</b><span>系统推荐机会</span></div>
      <div class='metric'><div>平均观看</div><b>{fmt(res['base']['avgViewDuration'], 1)}s</b><span>由观看时长反推</span></div>
    </div>

    <section class='wide'><h2>一、频道增长结论，不只是数据</h2>{insight_text(data, res)}</section>

    <div class='report'>
      <section><h2>二、真正的增长引擎</h2><p class='muted'>播放和涨粉效率都高，优先复制它们的题材、标题结构和视频承诺。</p>{lis(res['growth_engines'], video_line)}</section>
      <section><h2>三、播放高但不涨粉：流量陷阱</h2><p class='muted'>这类视频可能吸引了泛用户，或者内容没有把观众转化为频道认同。</p>{lis(res['traffic_traps'], video_line)}</section>
      <section><h2>四、隐藏宝藏：值得重做</h2><p class='muted'>播放不高但转粉强，说明题材对精准用户有价值，应该换标题/封面再打一遍。</p>{lis(res['hidden_gems'], video_line)}</section>
      <section><h2>五、包装胜利：高 CTR 标题</h2><p class='muted'>这些视频说明用户愿意点，重点拆标题承诺和封面信息密度。</p>{lis(res['packaging_wins'], video_line)}</section>
    </div>

    <section class='wide'><h2>六、题材四象限：以后拍什么，看这里</h2>{render_topic_matrix(res)}</section>

    <div class='report'>
      <section><h2>七、标题模式拆解</h2><p class='muted'>不是简单看哪个标题高，而是看哪些表达模式反复有效。</p>{lis(res['features'][:8], lambda g: f"<b>{escape(g['name'])}</b>：平均 CTR {pct(g['ctr'])}，播放 {fmt(g['views'])}，涨粉 {fmt(g['subs'])}，样本 {g['count']} 条")}</section>
      <section><h2>八、可复用标题公式</h2>{title_formula_examples(res)}</section>
      <section><h2>九、栏目化建议</h2><p class='muted'>栏目不是播放高就做，而是要能持续解释同一种用户问题。</p>{lis(res['columns'], lambda g: f"<b>{escape(g['name'])}</b>：{g['count']} 条，播放占比 {pct(g['viewShare'])}，千播放涨粉 {fmt(g['subRate'], 1)}，建议固定封面模板和片头承诺。")}</section>
      <section><h2>十、下周具体选题方向</h2>{next_week_plan(res)}</section>
    </div>

    <section class='wide'><h2>十一、旧视频二次包装清单</h2><p class='muted'>这些视频建议优先改标题/缩略图，或做更新版。目标不是重复发布，而是复用已经验证过的用户需求。</p>{lis(res['remake_candidates'], lambda v: video_line(v) + f"<br><span class='advice'>建议：保留题材，改成更明确的适用人群 + 失败原因 + 实测结论。</span>")}</section>

    <section class='wide'><h2>十二、可执行动作</h2>{strategic_actions(res)}</section>

    <h2>单视频明细</h2>
    <div class='tablewrap'><table><tr><th>标题</th><th>播放</th><th>CTR</th><th>曝光</th><th>涨粉</th><th>千播放涨粉</th><th>平均观看</th><th>题材</th><th>系列</th><th>标题标签</th></tr>
    {''.join(f"<tr><td>{escape(v['title'])}</td><td>{fmt(v['views'])}</td><td>{pct(v['ctr'])}</td><td>{fmt(v['impressions'])}</td><td>{fmt(v['subscribers_gained'])}</td><td>{fmt(v['subRate'], 1)}</td><td>{fmt(v['avg_view_duration'], 1)}s</td><td>{escape(v['topic'])}</td><td>{escape(v['series'])}</td><td>{''.join(badge(x) for x in v['features'])}</td></tr>" for v in sorted(data, key=lambda x: x['views'], reverse=True))}
    </table></div>
    """
    return report

def page(report="", textarea=""):
    return f"""<!doctype html><meta charset='utf-8'><title>YouTube 频道增长深度复盘工具</title>
<style>
body{{margin:0;background:#f8fafc;color:#1f2937;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Microsoft YaHei',sans-serif}}.wrap{{max-width:1220px;margin:0 auto;padding:24px}}.hero,.card,section,.metric{{background:white;border:1px solid #e5e7eb;border-radius:16px;padding:18px;margin-bottom:16px}}h1{{margin:0 0 8px;font-size:28px}}h2{{font-size:20px;margin:0 0 12px}}h3{{font-size:16px}}p,li{{line-height:1.75;color:#4b5563}}.grid{{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}}textarea{{width:100%;height:240px;border:1px solid #d1d5db;border-radius:12px;padding:12px;font-family:Consolas,monospace;font-size:12px;box-sizing:border-box}}button,.btn{{border:0;border-radius:10px;background:#2563eb;color:white;padding:10px 14px;font-size:14px;cursor:pointer;text-decoration:none;display:inline-block}}.secondary{{background:#eef2ff;color:#3730a3}}input[type=file]{{border:1px solid #d1d5db;border-radius:10px;padding:8px;background:white}}.status{{padding:10px 12px;border-radius:10px;margin:12px 0}}.ok{{background:#dcfce7;color:#166534}}.err{{background:#fee2e2;color:#991b1b}}.metrics{{display:grid;grid-template-columns:repeat(6,1fr);gap:12px;margin:16px 0}}.metric b{{display:block;font-size:24px;margin:4px 0}}.metric span{{font-size:12px;color:#6b7280}}.report{{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}}.wide{{grid-column:1/-1}}.muted{{color:#6b7280;font-size:13px}}.advice{{color:#92400e;font-size:13px}}table{{width:100%;border-collapse:collapse;font-size:13px}}th,td{{border-bottom:1px solid #e5e7eb;padding:8px;text-align:left;vertical-align:top}}th{{background:#f9fafb;position:sticky;top:0}}.tablewrap{{max-height:680px;overflow:auto;background:white;border:1px solid #e5e7eb;border-radius:12px}}.badge{{display:inline-block;border-radius:999px;padding:3px 8px;margin:2px;background:#dbeafe;color:#1e40af;font-size:12px}}.badge.good{{background:#dcfce7;color:#166534}}.badge.warn{{background:#fef3c7;color:#92400e}}.badge.bad{{background:#fee2e2;color:#991b1b}}.badge.info{{background:#dbeafe;color:#1e40af}}ul{{padding-left:20px;margin-top:6px}}@media(max-width:1000px){{.grid,.report{{grid-template-columns:1fr}}.metrics{{grid-template-columns:repeat(2,1fr)}}}}
</style><div class='wrap'><div class='hero'><h1>YouTube 频道增长深度复盘工具</h1><p>上传或粘贴 YouTube Analytics CSV 后，自动生成频道增长诊断报告，帮助创作者分析选题表现、标题和缩略图包装、播放与涨粉效率、流量陷阱、栏目化机会以及下一步内容策略。</p></div>
<div class='grid'><div class='card'><h2>导入或粘贴数据</h2><form method='post' enctype='multipart/form-data'><textarea name='csv_text' placeholder='粘贴 YouTube Analytics CSV 内容'>{escape(textarea)}</textarea><p><input type='file' name='csv_file' accept='.csv,.tsv,.txt'> <button type='submit'>生成深度复盘报告</button> <button class='secondary' name='use_sample' value='1'>使用示例数据</button></p></form></div><div class='card'><h2>这个工具可以深度分析什么</h2><ul><li>分析哪些视频真正带来频道增长，哪些只是带来泛流量。</li><li>分析标题、缩略图和开头钩子中哪些包装模式更容易获得点击。</li><li>分析不同题材、系列和内容类型的播放效率与涨粉效率。</li><li>分析高播放低涨粉的视频，识别内容定位和受众匹配问题。</li><li>分析哪些旧视频值得二次包装，哪些题材值得继续做成固定栏目。</li><li>分析下周应该优先测试的选题方向和内容策略。</li></ul></div></div>{report}</div>"""

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
        if "multipart/form-data" in ctype:
            msg = BytesParser(policy=default).parsebytes(("Content-Type: " + ctype + "\r\n\r\n").encode() + raw)
            for part in msg.iter_parts():
                name = part.get_param("name", header="content-disposition")
                if name == "use_sample":
                    text = SAMPLE_CSV
                    break
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
        try:
            data, meta = normalize(text)
            if data:
                report = render_report(data, meta)
            else:
                report = "<div class='status err'>没有识别到有效视频数据，请检查 CSV 表头。</div>"
        except Exception as e:
            report = f"<div class='status err'>生成失败：{escape(str(e))}</div>"
        self.send_html(page(report, text[:20000]))

if __name__ == "__main__":
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"YouTube growth review server running at http://{HOST}:{PORT}", flush=True)
    server.serve_forever()
