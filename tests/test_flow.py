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

    def fetch(query):
        calls.append(query)
        return response

    fetch.calls = calls
    return fetch


def test_fetch_store_and_ask(tmp_path, capsys, fake_fetch, response):
    path = str(tmp_path / "flow.db")

    # 1. One tick: both queries hit the "API" and land in the database.
    main(["--db", path, "fetch"], fetch=fake_fetch)
    assert len(fake_fetch.calls) == 2
    assert "10 new articles for:" in capsys.readouterr().out

    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10
    first, second = conn.execute("SELECT * FROM fetch_log ORDER BY id").fetchall()
    assert (first["status"], first["total_results"], first["new_articles"]) == (
        "ok", response["totalResults"], 10,
    )
    assert second["new_articles"] == 0  # the second query returned the same articles

    # 2. database -> answer, through the CLI
    main(["--db", path, "ask", "What has the news said about AMZN?"])
    out = capsys.readouterr().out
    print("\n" + out)

    assert "Amazon: 2 articles collected" in out
    assert "Sentiment:" in out
    assert "Hanes" in out
    # Articles that never mention Amazon are stored but not part of the answer.
    assert "adidas" not in out

    # 3. The whole database is checked: this Amazon-query result also mentions Walmart.
    main(["--db", path, "ask", "What has the news said about WMT?"])
    out = capsys.readouterr().out
    assert "Walmart: 1 article collected" in out
    assert "earbuds" in out


def test_fetching_again_stores_nothing_new(tmp_path, capsys, fake_fetch):
    path = str(tmp_path / "flow.db")

    main(["--db", path, "fetch"], fetch=fake_fetch)
    capsys.readouterr()
    main(["--db", path, "fetch"], fetch=fake_fetch)

    assert capsys.readouterr().out.count("0 new articles for:") == 2
    assert db.connect(path).execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10


def test_retag_command(tmp_path, capsys, fake_fetch):
    path = str(tmp_path / "flow.db")
    main(["--db", path, "fetch"], fetch=fake_fetch)
    capsys.readouterr()

    main(["--db", path, "retag"])

    assert "3 article-company links." in capsys.readouterr().out


def test_ask_before_any_fetch(tmp_path, capsys):
    main(["--db", str(tmp_path / "empty.db"), "ask", "What has the news said about Amazon?"])

    assert "No articles about Amazon have been collected yet." in capsys.readouterr().out


def test_ask_about_unknown_company(tmp_path, capsys):
    main(["--db", str(tmp_path / "empty.db"), "ask", "How is Tesla doing?"])

    assert "couldn't tell which company" in capsys.readouterr().out
