import re

from newstracker.config import ALIASES, COMPANIES


def mentions_company(article, company):
    """True if the title or description names the company, an alias or a ticker.

    Names match case-insensitively. Tickers must be uppercase, so words like
    "well", "ge" and "lin" don't count as Welltower, GE Aerospace or Linde.
    """
    text = f"{article.get('title') or ''} {article.get('description') or ''}"

    for name in [company, *ALIASES.get(company, [])]:
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            return True
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in COMPANIES[company])


def find_company(text):
    """Return the company a question or argument refers to, or None."""
    for company in COMPANIES:
        if mentions_company({"title": text}, company):
            return company
    bare = text.strip().upper()
    for company, tickers in COMPANIES.items():
        if bare in tickers:
            return company
    return None
