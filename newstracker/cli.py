import argparse
import sys
import time

from newstracker import config, db, fetcher
from newstracker.relevance import find_company
from newstracker.summarize import answer


def main(argv=None, fetch=fetcher.fetch_articles):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(prog="newstracker")
    parser.add_argument("--db", default=config.DB_PATH, help="SQLite file (default: %(default)s)")
    sub = parser.add_subparsers(dest="command", required=True)
    p_fetch = sub.add_parser("fetch", help="fetch one company now (uses 1 credit)")
    p_fetch.add_argument("company", help="company name or ticker, e.g. Amazon or AMZN")
    sub.add_parser("run", help="poll every 15 minutes, rotating through the companies")
    p_ask = sub.add_parser("ask", help="ask what the news has said about a company")
    p_ask.add_argument("question")
    args = parser.parse_args(argv)

    conn = db.connect(args.db)

    if args.command == "fetch":
        company = find_company(args.company)
        if company is None:
            parser.error(f"unknown company: {args.company}")
        new = fetcher.fetch_and_store(conn, company, fetch)
        print(f"{company}: {new} new articles stored.")
    elif args.command == "run":
        try:
            while True:
                for company, new in fetcher.run_once(conn, fetch):
                    print(f"{company}: {new} new articles stored.", flush=True)
                time.sleep(config.POLL_SECONDS)
        except KeyboardInterrupt:
            print("Stopped.")
    elif args.command == "ask":
        print(answer(conn, args.question))
