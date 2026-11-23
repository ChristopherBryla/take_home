"""Press Run to ask questions about the companies in the database (blank line to quit)."""
import sys

from newstracker import config, db
from newstracker.summarize import answer

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db.connect(config.DB_PATH)
    print("Ask about a company, e.g. What has the news said about AMZN?")
    try:
        while True:
            question = input("\n> ").strip()
            if not question:
                break
            print(answer(conn, question))
    except (EOFError, KeyboardInterrupt):
        pass
