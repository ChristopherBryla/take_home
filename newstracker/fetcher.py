import requests

from newstracker import config, db


class FetchError(Exception):
    pass


def build_query(companies):
    """Search terms for a group of companies, within the API's 100-character limit.

    Names and aliases always go in; tickers are added while they still fit.
    """
    names = []
    for company in companies:
        names += [company, *config.ALIASES.get(company, [])]
    # "Eli Lilly" is redundant next to "Lilly": the search matches either word.
    words = {n: set(n.lower().split()) for n in names}
    names = [n for n in names if not any(words[o] < words[n] for o in names)]

    terms = [f'"{n}"' if " " in n else n for n in names]
    for company in companies:
        for ticker in config.COMPANIES[company]:
            if ticker in config.SEARCH_SKIP_TICKERS:
                continue
            if len(" OR ".join(terms + [ticker])) <= config.MAX_QUERY_LENGTH:
                terms.append(ticker)
    return " OR ".join(terms)


def fetch_articles(query):
    """Make one API request (1 credit) and return the parsed response."""
    if not config.NEWSDATA_API_KEY:
        raise FetchError("NEWSDATA_API_KEY is not set")
    response = requests.get(
        config.NEWSDATA_URL,
        params={"apikey": config.NEWSDATA_API_KEY, "q": query, "language": "en"},
        timeout=30,
    )
    # Not raise_for_status(): its message contains the URL, which contains the key.
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}")
    try:
        data = response.json()
    except ValueError:
        raise FetchError("response was not JSON") from None
    if not isinstance(data, dict) or data.get("status") != "success":
        status = data.get("status") if isinstance(data, dict) else "unexpected body"
        raise FetchError(f"API status: {status}")
    return data


def fetch_and_store(conn, query, fetch=fetch_articles):
    """Run one query, save the articles, re-tag the whole database and log the call.

    Returns the number of new articles, or None if the request failed.
    """
    try:
        data = fetch(query)
    except FetchError as e:
        # A failed request may still have used a credit, so it is logged and counted.
        db.log_fetch(conn, query, f"error: {e}", None, 0)
        return None
    except requests.RequestException as e:
        # Only the type: the message contains the request URL, which contains the key.
        db.log_fetch(conn, query, f"error: {type(e).__name__}", None, 0)
        return None
    new = db.save_articles(conn, data["results"])
    db.tag_articles(conn)
    db.log_fetch(conn, query, "ok", data.get("totalResults"), new)
    return new


def credits_used_today(conn):
    row = conn.execute(
        "SELECT COUNT(*) FROM fetch_log WHERE date(fetched_at) = date('now')"
    ).fetchone()
    return row[0]


def next_rotating_group(conn):
    """The rotating group whose query was fetched longest ago (never-fetched first).

    Ordered by log row id, not time, so calls within the same second can't tie.
    """
    last = {
        r["query"]: r["last"]
        for r in conn.execute("SELECT query, MAX(id) AS last FROM fetch_log GROUP BY query")
    }
    return min(config.ROTATING_GROUPS, key=lambda g: last.get(build_query(g), 0))


def run_once(conn, fetch=fetch_articles, daily_limit=None):
    """One 15-minute tick: the every-tick queries plus the next rotating one."""
    daily_limit = daily_limit or config.CREDITS_PER_DAY
    results = []
    for group in [*config.EVERY_TICK_GROUPS, next_rotating_group(conn)]:
        if credits_used_today(conn) >= daily_limit:
            break
        query = build_query(group)
        results.append((query, fetch_and_store(conn, query, fetch)))
    return results
