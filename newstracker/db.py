import json
import sqlite3

from newstracker.config import DB_PATH
from newstracker.relevance import mentions_company

SCHEMA = """
CREATE TABLE IF NOT EXISTS articles (
    article_id      TEXT PRIMARY KEY,
    title           TEXT,
    description     TEXT,
    content         TEXT,
    link            TEXT,
    pub_date        TEXT,
    language        TEXT,
    source_id       TEXT,
    source_name     TEXT,
    sentiment       TEXT,
    sentiment_stats TEXT,
    duplicate       INTEGER,
    raw_json        TEXT NOT NULL,
    first_seen_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- An article can match several companies, so the link is its own table.
CREATE TABLE IF NOT EXISTS article_companies (
    article_id TEXT NOT NULL REFERENCES articles(article_id),
    company    TEXT NOT NULL,
    PRIMARY KEY (article_id, company)
);

CREATE TABLE IF NOT EXISTS fetch_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    company       TEXT NOT NULL,
    fetched_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status        TEXT,
    total_results INTEGER,
    new_articles  INTEGER
);

CREATE INDEX IF NOT EXISTS idx_articles_pub_date ON articles(pub_date);
CREATE INDEX IF NOT EXISTS idx_article_companies_company ON article_companies(company);
"""


def connect(path=DB_PATH):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def _clean(value):
    """The free plan fills locked fields with 'ONLY AVAILABLE IN ...' instead of null."""
    if isinstance(value, str) and value.startswith("ONLY AVAILABLE IN"):
        return None
    return value


def save_articles(conn, company, articles):
    """Store every article, but link it to the company only if it mentions it.

    Returns how many articles were new to the database.
    """
    new = 0
    for a in articles:
        cur = conn.execute(
            """INSERT OR IGNORE INTO articles
               (article_id, title, description, content, link, pub_date, language,
                source_id, source_name, sentiment, sentiment_stats, duplicate, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                a["article_id"],
                a.get("title"),
                a.get("description"),
                _clean(a.get("content")),
                a.get("link"),
                a.get("pubDate"),
                a.get("language"),
                a.get("source_id"),
                a.get("source_name"),
                a.get("sentiment"),
                json.dumps(a.get("sentiment_stats")),
                int(bool(a.get("duplicate"))),
                json.dumps(a, ensure_ascii=False),
            ),
        )
        new += cur.rowcount
        if mentions_company(a, company):
            conn.execute(
                "INSERT OR IGNORE INTO article_companies (article_id, company) VALUES (?, ?)",
                (a["article_id"], company),
            )
    conn.commit()
    return new


def log_fetch(conn, company, status, total_results, new_articles):
    conn.execute(
        "INSERT INTO fetch_log (company, status, total_results, new_articles) VALUES (?, ?, ?, ?)",
        (company, status, total_results, new_articles),
    )
    conn.commit()
