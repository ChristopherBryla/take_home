import json
from collections import Counter

from newstracker.config import COMPANIES
from newstracker.relevance import find_company


def _articles(conn, company):
    return conn.execute(
        """SELECT a.title, a.pub_date, a.source_name, a.sentiment, a.raw_json
           FROM article_companies ac JOIN articles a USING (article_id)
           WHERE ac.company = ? ORDER BY a.pub_date DESC""",
        (company,),
    ).fetchall()


def _tags(row):
    tags = json.loads(row["raw_json"]).get("ai_tag")
    return tags if isinstance(tags, list) else []


def summarize(conn, company, max_headlines=5):
    """Plain-text summary of what the stored articles say about a company."""
    rows = _articles(conn, company)
    if not rows:
        return f"No articles about {company} have been collected yet."

    n = len(rows)
    lines = [
        f"{company}: {n} article{'s' if n != 1 else ''} collected, "
        f"from {rows[-1]['pub_date']} to {rows[0]['pub_date']} UTC."
    ]

    sentiment = Counter(r["sentiment"] for r in rows if r["sentiment"])
    if sentiment:
        lines.append("Sentiment: " + ", ".join(f"{c} {s}" for s, c in sentiment.most_common()) + ".")

    tags = Counter(t for r in rows for t in _tags(r))
    if tags:
        lines.append("Topics: " + ", ".join(t for t, _ in tags.most_common(5)) + ".")

    sources = Counter(r["source_name"] for r in rows if r["source_name"])
    if sources:
        lines.append("Sources: " + ", ".join(s for s, _ in sources.most_common(3)) + ".")

    lines.append("Latest headlines:")
    seen = set()
    for r in rows:
        if r["title"] in seen:
            continue
        seen.add(r["title"])
        lines.append(f"  - {r['title']} ({r['source_name']}, {r['pub_date']}, {r['sentiment']})")
        if len(seen) == max_headlines:
            break
    return "\n".join(lines)


def answer(conn, question):
    """Answer a question like 'What has the news said about AMZN?'."""
    company = find_company(question)
    if company is None:
        return "I couldn't tell which company you mean. Try one of: " + ", ".join(COMPANIES) + "."
    return summarize(conn, company)
