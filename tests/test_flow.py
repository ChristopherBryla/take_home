"""End-to-end flow, using the saved API response in place of the real API (no credits used).

Press Run on this file, or:  python -m pytest -s
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))  # lets the Run button find newstracker

from newstracker import db
from newstracker.cli import main

SAMPLE = Path(__file__).parent.parent / "sample_data" / "sample_response.json"


def test_whole_flow(tmp_path, capsys):
    response = json.loads(SAMPLE.read_text(encoding="utf-8"))
    queries = []

    def fake_api(query):
        queries.append(query)
        return response

    path = str(tmp_path / "flow.db")

    # 1. One tick: the API response is fetched and stored.
    main(["--db", path, "fetch"], fetch=fake_api)
    assert len(queries) == 2  # the every-tick query plus one rotating query
    assert all(len(q) <= 100 for q in queries)  # NewsData.io's query limit

    conn = db.connect(path)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10
    logged = conn.execute("SELECT status, total_results, new_articles FROM fetch_log").fetchall()
    assert [tuple(r) for r in logged] == [("ok", 4241, 10), ("ok", 4241, 0)]

    # Every field of the response is kept, and locked free-plan fields become NULL.
    stored = conn.execute("SELECT raw_json, content FROM articles").fetchall()
    assert sorted(json.loads(r["raw_json"])["article_id"] for r in stored) == sorted(
        a["article_id"] for a in response["results"]
    )
    assert all(r["content"] is None for r in stored)

    # 2. Articles are linked to the companies they mention, across all 11 companies.
    links = {
        (r["company"], r["title"].split()[0])
        for r in conn.execute(
            "SELECT ac.company, a.title FROM article_companies ac JOIN articles a USING (article_id)"
        )
    }
    assert links == {("Amazon", "Our"), ("Amazon", "Hanes’"), ("Walmart", "Our")}

    # 3. The question is answered from what was stored.
    main(["--db", path, "ask", "What has the news said about AMZN?"])
    answer = capsys.readouterr().out.split("Amazon:", 1)[1]
    print("\nAmazon:" + answer)
    assert "2 stories" in answer
    assert "Sentiment:" in answer
    assert "earbuds" in answer and "Hanes" in answer
    assert "adidas" not in answer  # stored, but never mentions Amazon

    # 4. Fetching the same response again stores nothing new.
    main(["--db", path, "fetch"], fetch=fake_api)
    assert conn.execute("SELECT COUNT(*) FROM articles").fetchone()[0] == 10


if __name__ == "__main__":
    import pytest

    sys.exit(pytest.main([__file__, "-s", "-q"]))
