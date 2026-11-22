import json
import sqlite3

from newstracker.config import COMPANIES, DB_PATH
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
    query         TEXT NOT NULL,
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


def save_articles(conn, articles):
    """Store articles; return how many were new to the database."""
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
    conn.commit()
    return new


def tag_articles(conn):
    """Rebuild the article-company links by scanning every stored article.

    Links depend only on the stored text and the current matching rules, so this
    is safe to re-run (for example after adding an alias). Returns the link count.
    """
    conn.execute("DELETE FROM article_companies")
    for row in conn.execute("SELECT article_id, title, description FROM articles").fetchall():
        article = dict(row)
        for company in COMPANIES:
            if mentions_company(article, company):
                conn.execute(
                    "INSERT INTO article_companies (article_id, company) VALUES (?, ?)",
                    (row["article_id"], company),
                )
    conn.commit()
    return conn.execute("SELECT COUNT(*) FROM article_companies").fetchone()[0]


def log_fetch(conn, query, status, total_results, new_articles):
    conn.execute(
        "INSERT INTO fetch_log (query, status, total_results, new_articles) VALUES (?, ?, ?, ?)",
        (query, status, total_results, new_articles),
    )
    conn.commit()
