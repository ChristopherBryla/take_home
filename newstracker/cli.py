import argparse
import sqlite3
import sys
import time

from newstracker import config, db, fetcher
from newstracker.summarize import answer


def main(argv=None, fetch=fetcher.fetch_articles):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="newstracker")
    parser.add_argument("--db", default=config.DB_PATH, help="SQLite file (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("fetch", help="run one tick now: both queries, 2 credits")
    sub.add_parser("run", help="run a tick every 15 minutes")
    sub.add_parser("retag", help="re-scan every stored article for company mentions")
    p_ask = sub.add_parser("ask", help="ask what the news has said about a company")
    p_ask.add_argument("question")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)

    if args.command == "fetch":
        print_tick(fetcher.run_once(conn, fetch))
    elif args.command == "run":
        try:
            while True:
                try:
                    print_tick(fetcher.run_once(conn, fetch))
                except sqlite3.Error as e:
                    conn.rollback()
                    print(f"{stamp()} tick failed: {type(e).__name__}: {e}", flush=True)
                except Exception as e:
                    # Keep polling; only the type is printed since a message could contain the key.
                    print(f"{stamp()} tick failed: {type(e).__name__}", flush=True)
                time.sleep(config.POLL_SECONDS)
        except KeyboardInterrupt:
            print("Stopped.")
    elif args.command == "retag":
        print(f"{db.tag_articles(conn)} article-company links.")
    elif args.command == "ask":
        print(answer(conn, args.question))


def stamp():
    return time.strftime("[%Y-%m-%d %H:%M:%S]")


def print_tick(results):
    if not results:
        print(f"{stamp()} daily credit limit reached; nothing fetched.", flush=True)
    for query, new in results:
        outcome = "request failed (see fetch_log)" if new is None else f"{new} new articles"
        print(f"{stamp()} {outcome} for: {query}", flush=True)
