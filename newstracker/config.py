import os

from dotenv import load_dotenv

load_dotenv()

NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
NEWSDATA_URL = "https://newsdata.io/api/1/latest"

DB_PATH = "news.db"

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
