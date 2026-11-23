"""Press Run to ask questions about the companies in the database (blank line to quit).

Type /llm to switch between the free rule-based answer and the OpenAI answer
(needs OPENAI_API_KEY in .env; sends article text to OpenAI and costs a little).
"""
import sys

from newstracker import config, db, llm
from newstracker.summarize import answer

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    conn = db.connect(config.DB_PATH)
    use_llm = False
    print("Ask about a company, e.g. What has the news said about AMZN?")
    print("Type /llm to switch between the rule-based answer and the OpenAI answer.")
    try:
        while True:
            question = input(f"\n[{'OpenAI' if use_llm else 'rule-based'}] > ").strip()
            if not question:
                break
            if question.lower() == "/llm":
                use_llm = not use_llm
                print(f"Now using the {'OpenAI' if use_llm else 'rule-based'} answer.")
                continue
            if use_llm:
                try:
                    print(llm.answer_with_llm(conn, question))
                except llm.LLMError as error:
                    print(f"Language model unavailable ({error}). Showing the rule-based summary instead.\n")
                    print(answer(conn, question))
            else:
                print(answer(conn, question))
    except (EOFError, KeyboardInterrupt):
        pass
