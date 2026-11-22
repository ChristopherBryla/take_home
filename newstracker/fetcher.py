import requests

from newstracker import config, db


class FetchError(Exception):
    pass


def build_query(company):
    """Search for the company name or any of its tickers (API limit: 100 chars)."""
    name = f'"{company}"' if " " in company else company
    return " OR ".join([name, *config.COMPANIES[company]])


def fetch_articles(company):
    """Make one API request (1 credit) and return the parsed response."""
    if not config.NEWSDATA_API_KEY:
        raise FetchError("NEWSDATA_API_KEY is not set")
    response = requests.get(
        config.NEWSDATA_URL,
        params={
            "apikey": config.NEWSDATA_API_KEY,
            "q": build_query(company),
            "language": "en",
        },
        timeout=30,
    )
    # Not raise_for_status(): its message contains the URL, which contains the key.
    if response.status_code != 200:
        raise FetchError(f"HTTP {response.status_code}")
    data = response.json()
    if data.get("status") != "success":
        raise FetchError(f"API status: {data.get('status')}")
    return data


def fetch_and_store(conn, company, fetch=fetch_articles):
    """Fetch one company, save the articles and log the call. Returns new article count."""
    try:
        data = fetch(company)
    except (FetchError, requests.RequestException) as e:
        # A failed request may still have used a credit, so it is logged and counted.
        db.log_fetch(conn, company, f"error: {type(e).__name__}: {e}", None, 0)
        return 0
    new = db.save_articles(conn, company, data["results"])
    db.log_fetch(conn, company, "ok", data.get("totalResults"), new)
    return new


def credits_used_today(conn):
    row = conn.execute(
        "SELECT COUNT(*) FROM fetch_log WHERE date(fetched_at) = date('now')"
    ).fetchone()
    return row[0]


def companies_to_fetch(conn, count):
    """The companies fetched longest ago (never-fetched first, in config order)."""
    last = {
        r["company"]: r["last"]
        for r in conn.execute(
            "SELECT company, MAX(fetched_at) AS last FROM fetch_log GROUP BY company"
        )
    }
    return sorted(config.COMPANIES, key=lambda c: last.get(c) or "")[:count]


def run_once(conn, fetch=fetch_articles, per_run=None, daily_limit=None):
    """One 15-minute tick: fetch the next few companies, stopping at the daily budget."""
    per_run = per_run or config.COMPANIES_PER_RUN
    daily_limit = daily_limit or config.CREDITS_PER_DAY
    results = []
    for company in companies_to_fetch(conn, per_run):
        if credits_used_today(conn) >= daily_limit:
            break
        results.append((company, fetch_and_store(conn, company, fetch)))
    return results
