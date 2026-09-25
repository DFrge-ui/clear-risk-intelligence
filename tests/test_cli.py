import json

from clear.cli import main
from test_pipeline import BASE, csv_bytes


def test_cli_matches_app_pipeline_and_refuses_overwrite(tmp_path):
    source=tmp_path / "input.csv"
    source.write_bytes(csv_bytes([BASE]))
    target=tmp_path / "report.json"
    arguments=[str(source),"--as-of","2026-09-24","--output",str(target)]
    assert main(arguments) == 0
    report=json.loads(target.read_text(encoding="utf-8"))
    assert report["summary"]["metrics"]["total"] == 1
    assert report["summary"]["metrics"]["loss"] == 1250
    assert report["records"][0]["source_row"] == 2
    assert "Synthetic data" in report["disclosure"]
    original=target.read_bytes()
    assert main(arguments) == 2
    assert target.read_bytes() == original


def test_invalid_cli_input_creates_no_report(tmp_path):
    source=tmp_path / "bad.csv"
    source.write_text("wrong,header\n1,2")
    target=tmp_path / "report.json"
    assert main([str(source),"--as-of","2026-09-24","--output",str(target)]) == 2
    assert not target.exists()
