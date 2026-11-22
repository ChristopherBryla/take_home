import pytest

from newstracker import config, db, fetcher


@pytest.fixture
def conn(tmp_path):
    conn = db.connect(str(tmp_path / "test.db"))
    yield conn
    conn.close()


def empty_fetch(query):
    return {"status": "success", "totalResults": 0, "results": []}


def test_queries_fit_the_api_limit():
    for group in config.QUERY_GROUPS:
        assert len(fetcher.build_query(group)) <= config.MAX_QUERY_LENGTH


def test_every_company_is_in_exactly_one_query_group():
    grouped = [c for group in config.QUERY_GROUPS for c in group]

    assert sorted(grouped) == sorted(config.COMPANIES)


def test_query_includes_names_aliases_and_tickers():
    query = fetcher.build_query(["Amazon", "Alphabet", "Berkshire Hathaway"])

    assert query == 'Amazon OR Alphabet OR Google OR "Berkshire Hathaway" OR AMZN OR GOOGL OR GOOG OR BRK.B'


def test_query_drops_names_that_a_shorter_alias_already_covers():
    assert fetcher.build_query(["Eli Lilly"]) == "Lilly OR LLY"
    assert fetcher.build_query(["NextEra Energy"]) == "NextEra OR NEE"


def test_query_keeps_exxonmobil_next_to_exxon():
    # Search matches whole words, so "Exxon" alone would miss "ExxonMobil".
    assert fetcher.build_query(["ExxonMobil"]) == "ExxonMobil OR Exxon OR XOM"


def test_a_tick_runs_every_query_group(conn):
    queries = []

    def fetch(query):
        queries.append(query)
        return empty_fetch(query)

    fetcher.run_once(conn, fetch)

    assert queries == [fetcher.build_query(g) for g in config.QUERY_GROUPS]
    assert fetcher.credits_used_today(conn) == len(config.QUERY_GROUPS)


def test_daily_limit_stops_fetching(conn):
    assert len(fetcher.run_once(conn, empty_fetch, daily_limit=1)) == 1
    assert fetcher.run_once(conn, empty_fetch, daily_limit=1) == []


def test_fetch_articles_sends_the_query_and_hides_the_key_in_errors(monkeypatch):
    sent = {}

    class FakeResponse:
        def __init__(self, status_code, body):
            self.status_code, self._body = status_code, body

        def json(self):
            return self._body

    def fake_get(url, params, timeout):
        sent.update(params)
        return FakeResponse(200, {"status": "success", "totalResults": 0, "results": []})

    monkeypatch.setattr(config, "NEWSDATA_API_KEY", "secret-key")
    monkeypatch.setattr(fetcher.requests, "get", fake_get)

    assert fetcher.fetch_articles("Amazon OR AMZN")["status"] == "success"
    assert sent["q"] == "Amazon OR AMZN"

    monkeypatch.setattr(fetcher.requests, "get", lambda *a, **k: FakeResponse(401, {}))
    with pytest.raises(fetcher.FetchError) as error:
        fetcher.fetch_articles("Amazon OR AMZN")
    assert "secret-key" not in str(error.value)


def test_failed_request_is_logged_and_counts_as_a_credit(conn):
    def failing(query):
        raise fetcher.FetchError("HTTP 429")

    assert fetcher.fetch_and_store(conn, "Amazon OR AMZN", failing) == 0

    row = conn.execute("SELECT query, status FROM fetch_log").fetchone()
    assert row["query"] == "Amazon OR AMZN"
    assert row["status"] == "error: FetchError: HTTP 429"
    assert fetcher.credits_used_today(conn) == 1
