"""End-to-end flow with real_amzn.json standing in for the API (no credits used).

Run with output visible:  python -m pytest tests/test_flow.py -s
"""
import json
from pathlib import Path

import pytest

from newstracker import db
from newstracker.cli import main

SAMPLE = Path(__file__).parent.parent / "sample_data" / "real_amzn.json"


@pytest.fixture
def response():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def fake_fetch(response):
    calls = []

    def fetch(company):
        calls.append(company)
        return response

    fetch.calls = calls
    return fetch


def test_fetch_store_and_ask(tmp_path, capsys, fake_fetch, response):
    path = str(tmp_path / "flow.db")

    # 1. "API" -> database, through the CLI
    main(["--db", path, "fetch", "AMZN"], fetch=fake_fetch)
    assert fake_fetch.calls == ["Amazon"]
    assert "Amazon: 10 new articles stored." in capsys.readouterr().out

    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10
    log = conn.execute("SELECT * FROM fetch_log").fetchone()
    assert (log["company"], log["status"], log["total_results"], log["new_articles"]) == (
        "Amazon", "ok", response["totalResults"], 10,
    )

    # 2. database -> answer, through the CLI
    main(["--db", path, "ask", "What has the news said about AMZN?"])
    out = capsys.readouterr().out
    print("\n" + out)

    assert "Amazon: 2 articles collected" in out
    assert "Sentiment:" in out
    assert "Hanes" in out
    # Articles that never mention Amazon are stored but not part of the answer.
    assert "adidas" not in out


def test_fetching_again_stores_nothing_new(tmp_path, capsys, fake_fetch):
    path = str(tmp_path / "flow.db")

    main(["--db", path, "fetch", "Amazon"], fetch=fake_fetch)
    main(["--db", path, "fetch", "Amazon"], fetch=fake_fetch)

    assert "Amazon: 0 new articles stored." in capsys.readouterr().out.splitlines()[-1]
    assert db.connect(path).execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10


def test_ask_before_any_fetch(tmp_path, capsys):
    main(["--db", str(tmp_path / "empty.db"), "ask", "What has the news said about Amazon?"])

    assert "No articles about Amazon have been collected yet." in capsys.readouterr().out


def test_ask_about_unknown_company(tmp_path, capsys):
    main(["--db", str(tmp_path / "empty.db"), "ask", "How is Tesla doing?"])

    assert "couldn't tell which company" in capsys.readouterr().out
