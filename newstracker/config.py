import os

from dotenv import load_dotenv

load_dotenv()

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_URL = "https://newsdata.io/api/1/latest"

DB_PATH = "news.db"

# Free plan: 200 credits/day, 1 credit per request. 96 runs/day x 2 queries = 192.
CREDITS_PER_DAY = 200
POLL_SECONDS = 15 * 60

# The API caps a search query at 100 characters, so the 11 companies are split
# across two queries that both run on every 15-minute tick.
MAX_QUERY_LENGTH = 100
QUERY_GROUPS = [
    ["Amazon", "Nvidia", "Alphabet", "Eli Lilly", "Berkshire Hathaway"],
    ["Walmart", "ExxonMobil", "NextEra Energy", "Welltower", "Linde", "GE Aerospace"],
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
