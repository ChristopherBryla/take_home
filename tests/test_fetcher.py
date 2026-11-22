import pytest

from newstracker import config, db, fetcher


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    yield conn
    conn.close()


def empty_fetch(company):
    return {"status": "success", "totalResults": 0, "results": []}


def test_queries_fit_the_api_limit():
    for company in config.COMPANIES:
        assert len(fetcher.build_query(company)) <= 100


def test_query_format():
    assert fetcher.build_query("Amazon") == "Amazon OR AMZN"
    assert fetcher.build_query("Alphabet") == "Alphabet OR Google OR GOOGL OR GOOG"
    assert fetcher.build_query("ExxonMobil") == "ExxonMobil OR Exxon OR XOM"
    assert fetcher.build_query("Eli Lilly") == '"Eli Lilly" OR Lilly OR LLY'
    assert fetcher.build_query("NextEra Energy") == '"NextEra Energy" OR NextEra OR NEE'
    assert fetcher.build_query("Berkshire Hathaway") == '"Berkshire Hathaway" OR BRK.B'


def test_rotation_visits_every_company_before_repeating(conn):
    names = list(config.COMPANIES)
    seen = []
    for _ in range(6):  # 6 runs x 2 companies = 12 >= 11
        seen += [c for c, _ in fetcher.run_once(conn, empty_fetch)]

    assert seen[:11] == names
    assert seen[11] == names[0]


def test_daily_limit_stops_fetching(conn):
    results = fetcher.run_once(conn, empty_fetch, per_run=5, daily_limit=3)

    assert len(results) == 3
    assert fetcher.credits_used_today(conn) == 3
    assert fetcher.run_once(conn, empty_fetch, per_run=5, daily_limit=3) == []


def test_failed_request_is_logged_and_counts_as_a_credit(conn):
    def failing(company):
        raise fetcher.FetchError("HTTP 429")

    assert fetcher.fetch_and_store(conn, "Amazon", failing) == 0

    row = conn.execute("SELECT status FROM fetch_log").fetchone()
    assert row["status"] == "error: FetchError: HTTP 429"
    assert fetcher.credits_used_today(conn) == 1
