import argparse
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
                print_tick(fetcher.run_once(conn, fetch))
                time.sleep(config.POLL_SECONDS)
        except KeyboardInterrupt:
            print("Stopped.")
    elif args.command == "retag":
        print(f"{db.tag_articles(conn)} article-company links.")
    elif args.command == "ask":
        print(answer(conn, args.question))


def print_tick(results):
    if not results:
        print("Daily credit limit reached; nothing fetched.", flush=True)
    for query, new in results:
        print(f"{new} new articles stored for: {query}", flush=True)
