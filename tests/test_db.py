import json
from pathlib import Path

import pytest

from newstracker import config, db

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

    new = db.save_articles(conn, articles)

    assert new == len(articles)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(articles)


def test_only_articles_mentioning_amazon_are_linked(conn, response):
    db.save_articles(conn, response["results"])
    db.tag_articles(conn)

    linked = conn.execute(
        "SELECT a.title FROM article_companies ac JOIN articles a USING (article_id) "
        "WHERE ac.company = 'Amazon'"
    ).fetchall()

    assert len(linked) == 2
    assert any("earbuds" in r["title"] for r in linked)
    assert any("Hanes" in r["title"] for r in linked)


def test_saving_twice_adds_no_duplicates(conn, response):
    db.save_articles(conn, response["results"])

    assert db.save_articles(conn, response["results"]) == 0
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == len(response["results"])


def test_raw_json_keeps_every_field(conn, response):
    db.save_articles(conn, response["results"])

    original = response["results"][0]
    row = conn.execute(
        "SELECT raw_json FROM articles WHERE article_id = ?", (original["article_id"],)
    ).fetchone()

    assert json.loads(row["raw_json"]) == original


def test_columns_match_the_response(conn, response):
    db.save_articles(conn, response["results"])

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
    db.save_articles(conn, response["results"])

    rows = conn.execute("SELECT content FROM articles").fetchall()

    assert all(r["content"] is None for r in rows)


def test_tagging_checks_every_company_not_just_the_one_searched_for(conn, response):
    # The earbuds article says "on sale at Amazon, Best Buy, and Walmart".
    earbuds = response["results"][0]

    db.save_articles(conn, [earbuds])
    db.tag_articles(conn)

    companies = {r["company"] for r in conn.execute("SELECT company FROM article_companies")}
    assert companies == {"Amazon", "Walmart"}


def test_tagging_twice_gives_the_same_links(conn, response):
    db.save_articles(conn, response["results"])

    assert db.tag_articles(conn) == db.tag_articles(conn)


def test_retagging_picks_up_a_new_company(conn, response, monkeypatch):
    db.save_articles(conn, response["results"])
    before = db.tag_articles(conn)

    # The earbuds description mentions Soundcore.
    monkeypatch.setitem(config.COMPANIES, "Soundcore", [])

    assert db.tag_articles(conn) == before + 1
