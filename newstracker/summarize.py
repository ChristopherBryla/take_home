import json
from collections import Counter

from newstracker.config import COMPANIES
from newstracker.relevance import find_company


def _articles(conn, company):
    return conn.execute(
        """SELECT a.article_id, a.title, a.description, a.pub_date, a.source_name, a.sentiment, a.raw_json
           FROM article_companies ac JOIN articles a USING (article_id)
           WHERE ac.company = ? ORDER BY a.pub_date DESC""",
        (company,),
    ).fetchall()


def _tags(row):
    tags = json.loads(row["raw_json"]).get("ai_tag")
    return tags if isinstance(tags, list) else []


def _stories(rows):
    """Group copies of the same story (same title, different outlet), newest first.

    Returns (row, copies) pairs, where row is the newest copy.
    """
    stories = {}
    for row in rows:
        key = " ".join((row["title"] or "").lower().split()) or row["article_id"]
        if key in stories:
            stories[key][1] += 1
        else:
            stories[key] = [row, 1]
    return [tuple(s) for s in stories.values()]


def company_stories(conn, company):
    """The company's stories, newest first, as (row, copies) pairs."""
    return _stories(_articles(conn, company))


def summarize(conn, company, max_headlines=5):
    """Plain-text summary of what the stored articles say about a company.

    Each story counts once, even if many outlets published it.
    """
    articles = _articles(conn, company)
    if not articles:
        return f"No articles about {company} have been collected yet."

    stories = _stories(articles)
    rows = [row for row, _ in stories]

    count = f"{len(stories)} {'story' if len(stories) == 1 else 'stories'}"
    if len(articles) != len(stories):
        count += f" ({len(articles)} articles including copies from other outlets)"
    lines = [
        f"{company}: {count} collected, "
        f"from {articles[-1]['pub_date']} to {articles[0]['pub_date']} UTC."
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
    for row, copies in stories[:max_headlines]:
        note = f", carried by {copies} outlets" if copies > 1 else ""
        lines.append(
            f"  - {row['title']} ({row['source_name']}, {row['pub_date']}, {row['sentiment']}{note})"
        )
    return "\n".join(lines)


def answer(conn, question):
    """Answer a question like 'What has the news said about AMZN?'."""
    company = find_company(question)
    if company is None:
        return "I couldn't tell which company you mean. Try one of: " + ", ".join(COMPANIES) + "."
    return summarize(conn, company)
