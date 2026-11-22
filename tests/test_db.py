import json
from pathlib import Path

import pytest

from newstracker import db

SAMPLE = Path(__file__).parent.parent / "sample_data" / "real_amzn.json"


@pytest.fixture
def response():
    return json.loads(SAMPLE.read_text(encoding="utf-8"))


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    yield conn
    conn.close()


def test_saves_real_response(conn, response):
    articles = response["results"]

    new = db.save_articles(conn, "Amazon", articles)

    assert new == len(articles)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(articles)
    assert conn.execute(
        "SELECT COUNT(*) FROM article_companies WHERE company = 'Amazon'"
    ).fetchone()[0] == len(articles)


def test_saving_twice_adds_no_duplicates(conn, response):
    db.save_articles(conn, "Amazon", response["results"])

    assert db.save_articles(conn, "Amazon", response["results"]) == 0
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(response["results"])


def test_raw_json_keeps_every_field(conn, response):
    db.save_articles(conn, "Amazon", response["results"])

    original = response["results"][0]
    row = conn.execute(
        "SELECT raw_json FROM articles WHERE article_id = ?", (original["article_id"],)
    ).fetchone()

    assert json.loads(row["raw_json"]) == original


def test_columns_match_the_response(conn, response):
    db.save_articles(conn, "Amazon", response["results"])

    original = response["results"][0]
    row = conn.execute(
        "SELECT * FROM articles WHERE article_id = ?", (original["article_id"],)
    ).fetchone()

    assert row["title"] == original["title"]
    assert row["pub_date"] == original["pubDate"]
    assert row["source_name"] == original["source_name"]
    assert row["sentiment"] == original["sentiment"]
    assert json.loads(row["sentiment_stats"]) == original["sentiment_stats"]
    assert row["duplicate"] == int(original["duplicate"])


def test_paid_plan_placeholders_become_null(conn, response):
    db.save_articles(conn, "Amazon", response["results"])

    rows = conn.execute("SELECT content FROM articles").fetchall()

    assert all(r["content"] is None for r in rows)


def test_same_article_can_belong_to_two_companies(conn, response):
    article = response["results"][0]

    db.save_articles(conn, "Amazon", [article])
    db.save_articles(conn, "Walmart", [article])

    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM article_companies").fetchone()[0] == 2
