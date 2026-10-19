from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.app import normalize, analyze


def test_sample_csv_parses():
    text = (ROOT / "examples" / "sample_youtube_analytics.csv").read_text(encoding="utf-8")
    data, meta = normalize(text)
    assert len(data) == 8
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
