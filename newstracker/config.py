import os

from dotenv import load_dotenv

load_dotenv()

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_URL = "https://newsdata.io/api/1/latest"

DB_PATH = "news.db"

# Free plan: 200 credits/day, 1 credit per request. 96 runs/day x 2 companies = 192.
CREDITS_PER_DAY = 200
COMPANIES_PER_RUN = 2
POLL_SECONDS = 15 * 60

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
