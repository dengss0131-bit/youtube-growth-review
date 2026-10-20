from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app import normalize, analyze, detect_platform, PLATFORMS


def test_sample_csv_parses():
    text = (ROOT / "examples" / "sample_youtube_analytics.csv").read_text(encoding="utf-8")
    data, meta = normalize(text)
    assert len(data) == 8
    assert meta["platform"] == "youtube"
    assert data[0]["title"] == "I tested 5 AI note apps for creators"
    assert data[0]["views"] == 42800
    assert data[0]["ctr"] == 7.8


def test_total_row_is_skipped():
    text = "Content,Video title,Views,Subscribers,Thumbnail impressions,Thumbnail click-through rate (%)\nTotal,,100,5,1000,10\nabc123,Example video,50,2,500,8\n"
    data, meta = normalize(text)
    assert len(data) == 1
    assert data[0]["title"] == "Example video"


def test_analysis_contains_core_groups():
    text = (ROOT / "examples" / "sample_youtube_analytics.csv").read_text(encoding="utf-8")
    data, meta = normalize(text)
    result = analyze(data)
    assert "growth_engines" in result
    assert "traffic_traps" in result
    assert "topics" in result
    assert result["base"]["ctr"] > 0


def test_douyin_detection_and_parse():
    text = "作品标题,发布时间,播放量,完播率,平均播放时长,点赞数,评论数,分享数,涨粉数\n测试视频,2026-10-01,10000,50,40,100,20,5,30\n"
    data, meta = normalize(text)
    assert meta["platform"] == "douyin"
    assert len(data) == 1
    assert data[0]["views"] == 10000
    assert data[0]["retention"] == 50
    assert data[0]["subscribers_gained"] == 30


def test_xiaohongshu_detection_and_parse():
    text = "笔记标题,发布时间,曝光量,点击率,阅读量,点赞,收藏,评论,分享,涨粉数,平均阅读时长\n笔记1,2026-10-01,100000,8.5,8500,500,400,50,20,60,45\n"
    data, meta = normalize(text)
    assert meta["platform"] == "xiaohongshu"
    assert len(data) == 1
    assert data[0]["views"] == 8500
    assert data[0]["ctr"] == 8.5
    assert data[0]["likes"] == 500
    assert data[0]["favorites"] == 400


def test_bilibili_detection_and_parse():
    text = "稿件标题,发布时间,播放量,完播率,平均播放时长,点赞,投币,收藏,分享,评论,新增关注\n稿件1,2026-10-01,50000,60,200,1000,500,800,50,40,200\n"
    data, meta = normalize(text)
    assert meta["platform"] == "bilibili"
    assert len(data) == 1
    assert data[0]["views"] == 50000
    assert data[0]["subscribers_gained"] == 200


def test_tiktok_detection_and_parse():
    text = "Title,Date,Views,Likes,Comments,Shares,Followers gained,Average watch time,Retention rate\nVideo 1,2026-10-01,20000,3000,100,50,120,18,55\n"
    data, meta = normalize(text)
    assert meta["platform"] == "tiktok"
    assert len(data) == 1
    assert data[0]["views"] == 20000
    assert data[0]["subscribers_gained"] == 120


def test_detect_platform_all():
    assert detect_platform(["作品标题", "播放量", "完播率", "涨粉数"]) == "douyin"
    assert detect_platform(["笔记标题", "阅读量", "收藏", "涨粉数"]) == "xiaohongshu"
    assert detect_platform(["稿件标题", "播放量", "新增关注"]) == "bilibili"
    assert detect_platform(["Video title", "Views", "Subscribers"]) == "youtube"
