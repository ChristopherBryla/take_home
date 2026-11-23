import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_URL = "https://newsdata.io/api/1/latest"

# Optional: only used by `ask --llm`.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

DB_PATH = str(Path(__file__).resolve().parent.parent / "news.db")

# Free plan: 200 credits/day, 1 credit per request. 96 runs/day x 2 queries = 192.
CREDITS_PER_DAY = 200
POLL_SECONDS = 15 * 60

# The API caps a search query at 100 characters, so the 11 companies are split
# across several queries. Each tick makes 2 calls (96 ticks x 2 = 192 credits):
# every query in EVERY_TICK_GROUPS runs each tick, and the second slot goes to
# whichever ROTATING_GROUPS query was fetched longest ago.
# Each request returns at most 10 articles shared by its whole group, so busy
# companies get a query to themselves and the quiet ones share the rarer slot.
MAX_QUERY_LENGTH = 100
EVERY_TICK_GROUPS = [
    ["Amazon", "Alphabet"],
]
ROTATING_GROUPS = [
    ["Walmart", "Nvidia"],
    ["Eli Lilly", "Berkshire Hathaway", "GE Aerospace"],
    ["ExxonMobil", "NextEra Energy"],
    ["Linde", "Welltower"],
]

# name -> tickers. Alphabet has two share classes.
COMPANIES = {
    "Nvidia": ["NVDA"],
    "Berkshire Hathaway": ["BRK.B"],
    "Alphabet": ["GOOGL", "GOOG"],
    "Eli Lilly": ["LLY"],
    "Amazon": ["AMZN"],
    "GE Aerospace": ["GE"],
    "Walmart": ["WMT"],
    "ExxonMobil": ["XOM"],
    "NextEra Energy": ["NEE"],
    "Linde": ["LIN"],
    "Welltower": ["WELL"],
}

# Other names an article might use for a company. Matched case-insensitively.
ALIASES = {
    "Alphabet": ["Google"],
    "ExxonMobil": ["Exxon"],
    "Eli Lilly": ["Lilly"],
    "NextEra Energy": ["NextEra"],
}

# Boilerplate that contains a company name without being about the company
# (e.g. "See more headlines & perspectives on Google News").
IGNORED_PHRASES = ["Google News", "van der Linde"]

# Tickers that are also ordinary words. The search isn't case-sensitive, so sending
# them returns unrelated articles; they are still matched (uppercase only) in our own
# relevance check.
SEARCH_SKIP_TICKERS = ["GE", "LIN", "WELL"]
