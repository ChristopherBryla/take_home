"""Optional language-model answers for `ask --llm` (OpenAI, via plain HTTP)."""
import requests

from newstracker import config
from newstracker.relevance import find_companies
from newstracker.summarize import answer, company_stories

MAX_STORIES = 40
MAX_DESCRIPTION = 300

INSTRUCTIONS = (
    "You answer questions about companies using only the news articles provided. "
    "Each article has a time in UTC, a source and a sentiment label from the news API. "
    "Do not use outside knowledge. If the articles do not cover the question, say so plainly. "
    "Ignore articles that only mention the company in passing (for example as a store where "
    "something is on sale), and say when most of the coverage is like that. "
    "Mention how many distinct stories you based the answer on. Be concise."
)


class LLMError(Exception):
    pass


def build_prompt(question, stories_by_company):
    lines = [f"Question: {question}", ""]
    for company, stories in stories_by_company.items():
        lines.append(f"Articles about {company} (newest first):")
        for i, (row, copies) in enumerate(stories[:MAX_STORIES], 1):
            note = f", carried by {copies} outlets" if copies > 1 else ""
            description = (row["description"] or "")[:MAX_DESCRIPTION]
            lines.append(
                f"{i}. [{row['pub_date']} UTC | {row['source_name']} | {row['sentiment']}{note}] "
                f"{row['title']} - {description}"
            )
        lines.append("")
    return "\n".join(lines)


def answer_with_llm(conn, question, post=None):
    """Ask the model about the companies in the question; raises LLMError on failure.

    With no company in the question, or no stored articles for it, no request is made
    and the normal rule-based answer is returned.
    """
    post = post or requests.post
    stories = {c: company_stories(conn, c) for c in find_companies(question)}
    stories = {c: s for c, s in stories.items() if s}
    if not stories:
        return answer(conn, question)

    if not config.OPENAI_API_KEY:
        raise LLMError("OPENAI_API_KEY is not set")
    try:
        response = post(
            config.OPENAI_URL,
            headers={"Authorization": f"Bearer {config.OPENAI_API_KEY}"},
            json={
                "model": config.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": INSTRUCTIONS},
                    {"role": "user", "content": build_prompt(question, stories)},
                ],
                "reasoning_effort": "none",
            },
            timeout=60,
        )
    except requests.RequestException as e:
        raise LLMError(type(e).__name__) from None

    if response.status_code != 200:
        raise LLMError(f"HTTP {response.status_code}{_error_detail(response)}")
    try:
        text = response.json()["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError):
        raise LLMError("unexpected response format") from None
    if not text or not text.strip():
        raise LLMError("empty response")
    return text.strip()


def _error_detail(response):
    try:
        return ": " + str(response.json()["error"]["message"])[:200]
    except (ValueError, KeyError, TypeError):
        return ""
