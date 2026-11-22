import json
from pathlib import Path

import pytest

from newstracker import db
from newstracker.summarize import summarize

SAMPLE = Path(__file__).parent.parent / "sample_data" / "real_amzn.json"


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    yield conn
    conn.close()


def copy_of(article, article_id, source_name):
    return {**article, "article_id": article_id, "source_name": source_name}


def test_a_syndicated_story_counts_once(conn):
    # Hanes sweatshirt article: Amazon is in the description.
    original = next(
        a for a in json.loads(SAMPLE.read_text(encoding="utf-8"))["results"] if "Hanes" in a["title"]
    )
    copies = [copy_of(original, f"copy-{i}", f"Paper {i}") for i in range(3)]
    db.save_articles(conn, [original, *copies])
    db.tag_articles(conn)

    out = summarize(conn, "Amazon")

    assert "Amazon: 1 story (4 articles including copies from other outlets)" in out
    assert "carried by 4 outlets" in out
    assert out.count("Hanes") == 1
    assert "Sentiment: 1 " in out


def test_titles_are_compared_ignoring_case_and_spacing(conn):
    a = {"article_id": "1", "title": "Amazon  raises prices", "description": "", "source_name": "A"}
    b = {"article_id": "2", "title": "amazon raises PRICES", "description": "", "source_name": "B"}
    db.save_articles(conn, [a, b])
    db.tag_articles(conn)

    assert "Amazon: 1 story (2 articles" in summarize(conn, "Amazon")


def test_different_stories_are_not_merged(conn):
    a = {"article_id": "1", "title": "Amazon raises prices", "description": "", "source_name": "A"}
    b = {"article_id": "2", "title": "Amazon opens a new hub", "description": "", "source_name": "B"}
    db.save_articles(conn, [a, b])
    db.tag_articles(conn)

    assert "Amazon: 2 stories collected" in summarize(conn, "Amazon")
