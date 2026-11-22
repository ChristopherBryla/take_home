import re

from newstracker.config import ALIASES, COMPANIES, IGNORED_PHRASES


def mentions_company(article, company):
    """True if the title or description names the company, an alias or a ticker.

    Names match case-insensitively. Tickers must be uppercase, so words like
    "well", "ge" and "lin" don't count as Welltower, GE Aerospace or Linde.
    Phrases in IGNORED_PHRASES are removed before matching.
    """
    text = f"{article.get('title') or ''} {article.get('description') or ''}"
    for phrase in IGNORED_PHRASES:
        text = re.sub(re.escape(phrase), " ", text, flags=re.IGNORECASE)

    for name in [company, *ALIASES.get(company, [])]:
        if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
            return True
    return any(re.search(rf"\b{re.escape(t)}\b", text) for t in COMPANIES[company])


def find_companies(text):
    """Return every company a question or argument refers to, in config order."""
    found = [c for c in COMPANIES if mentions_company({"title": text}, c)]
    if found:
        return found
    bare = text.strip().upper()
    return [c for c, tickers in COMPANIES.items() if bare in tickers]


def find_company(text):
    """Return the first company a question or argument refers to, or None."""
    found = find_companies(text)
    return found[0] if found else None
