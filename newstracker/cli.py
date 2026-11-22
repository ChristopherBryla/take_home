import argparse
import sqlite3
import sys
import time

from newstracker import config, db, fetcher, llm
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
    p_query = sub.add_parser("query", help="run a read-only SQL file, e.g. queries\\01_articles_per_company.sql")
    p_query.add_argument("file")
    p_ask = sub.add_parser("ask", help="ask what the news has said about a company")
    p_ask.add_argument("question")
    p_ask.add_argument(
        "--llm",
        action="store_true",
        help="answer with OpenAI instead (needs OPENAI_API_KEY; sends article text to OpenAI)",
    )
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
    elif args.command == "query":
        conn.execute("PRAGMA query_only = ON")
        with open(args.file, encoding="utf-8") as f:
            print_table(conn.execute(f.read()))
    elif args.command == "ask":
        if args.llm:
            try:
                print(llm.answer_with_llm(conn, args.question))
            except llm.LLMError as e:
                print(f"Language model unavailable ({e}). Showing the rule-based summary instead.\n")
                print(answer(conn, args.question))
        else:
            print(answer(conn, args.question))


def print_table(cursor, max_width=70):
    headers = [d[0] for d in cursor.description]
    rows = [["" if v is None else str(v)[:max_width] for v in row] for row in cursor.fetchall()]
    widths = [max(len(h), *(len(r[i]) for r in rows)) for i, h in enumerate(headers)]
    for line in [headers, ["-" * w for w in widths], *rows]:
        print("  ".join(cell.ljust(w) for cell, w in zip(line, widths)).rstrip())
    print(f"({len(rows)} rows)")


def stamp():
    return time.strftime("[%Y-%m-%d %H:%M:%S]")


def print_tick(results):
    if not results:
        print(f"{stamp()} daily credit limit reached; nothing fetched.", flush=True)
    for query, new in results:
        outcome = "request failed (see fetch_log)" if new is None else f"{new} new articles"
        print(f"{stamp()} {outcome} for: {query}", flush=True)
