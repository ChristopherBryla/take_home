"""Press Run to explore the database: pick a query from queries/ or type your own SQL."""
import sqlite3
import sys
from pathlib import Path

from newstracker import config, db
from newstracker.cli import print_table

FILES = sorted((Path(__file__).parent / "queries").glob("*.sql"))

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db.connect(config.DB_PATH)
    conn.execute("PRAGMA query_only = ON")  # read-only: nothing here can change the data
    try:
        while True:
            print("\nQueries:")
            for number, file in enumerate(FILES, 1):
                print(f"  {number}. {file.stem}")
            choice = input("\nQuery number, or your own SQL (blank line to quit): ").strip()
            if not choice:
                break
            if choice.isdigit():
                if not 1 <= int(choice) <= len(FILES):
                    print("No query with that number.")
                    continue
                choice = FILES[int(choice) - 1].read_text(encoding="utf-8")
            try:
                print_table(conn.execute(choice))
            except sqlite3.Error as error:
                print(f"Error: {error}")
    except (EOFError, KeyboardInterrupt):
        pass
