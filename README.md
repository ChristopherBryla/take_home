# Company News Tracker

A small app that collects news about 11 companies from [NewsData.io](https://newsdata.io) (free plan), stores it in SQLite, and answers questions like *"What has the news said about AMZN?"*.

## How to run

Developed and tested on Python 3.13.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env      # then put your NewsData.io key in .env
```

```powershell
python -m newstracker fetch                                   # one tick now (2 credits)
python -m newstracker run                                     # a tick every 15 minutes
python -m newstracker ask "What has the news said about AMZN?"
python -m newstracker ask --llm "Did Amazon announce layoffs?"   # optional: answer with OpenAI
python -m newstracker retag                                   # rebuild company tags from stored articles
python -m pytest                                              # tests (no API calls, no credits)
```

Data is stored in `news.db` (override with `--db path`).

## How it works

1. **Fetch.** Every 15 minutes the app runs two search queries, each covering about half of the companies (the API caps a query at 100 characters, and one query cannot fit all 11). Names, aliases and as many tickers as fit are included.
2. **Store.** Every returned article goes into the `articles` table. The complete API object is kept as JSON in `raw_json`, and the fields we query on (title, description, date, source, sentiment, ...) are also stored as columns. Articles are de-duplicated on `article_id`.
3. **Tag.** After each fetch, the whole database is re-scanned and every article is linked to every company it mentions (`article_companies`). An article found by one query can therefore count for any company.
4. **Answer.** `ask` finds the company in the question (name, alias or ticker), then summarizes its linked articles: article count and date range, sentiment tally, top topics and sources, and the latest headlines. This default answer is rule-based, free, and needs no extra key. With `--llm`, the question and the stored stories for the companies it names are sent to an OpenAI model, which answers only from those articles (see below).

Tables: `articles`, `article_companies` (article-to-company links), `fetch_log` (one row per API call: query, status, total results, new articles).

## Decisions

- **Credit budget.** Free plan = 200 credits/day, 1 credit per request. Two requests per 15-minute tick = 96 x 2 = 192 credits/day. The app stops fetching once the day's logged requests reach 200. Failed requests are logged and counted as used.
- **Two combined queries instead of one query per company.** One query per company would need 1,056 credits/day. Splitting the 11 companies into two queries keeps every company searched on every tick.
- **Tag the whole database, not just the searched company.** Links are rebuilt from the stored text and the current matching rules, so changing an alias and running `retag` fixes old data.
- **What counts as "about a company".** An article is linked only if its title or description names the company, a known alias (Google, Exxon, Lilly, NextEra) or its ticker. Tickers must be uppercase whole words, so "well", "ge" and "lin" do not match Welltower, GE Aerospace or Linde. The boilerplate "Google News" is ignored. Articles that match nothing are still stored.
- **Sentiment comes from the API.** The free plan includes a sentiment label and scores, so no separate model is used.
- **Summary is rule-based by default.** The free plan hides article `content` (and `ai_summary`), leaving only titles and descriptions, so the default summary is a roll-up of those fields rather than a model-written paragraph. Fields locked on the free plan are stored as NULL.
- **Language model is optional (`ask --llm`).** The rule-based answer only identifies the company in a question, so it cannot answer things like "Did Amazon announce layoffs?". With `--llm` and an `OPENAI_API_KEY` in `.env`, the stored stories (title, description, date, source, sentiment; one entry per distinct story, newest 40 per company) are sent to OpenAI's `gpt-6-luna` model with instructions to answer only from them and to say when the data doesn't cover the question. It is opt-in because it costs money and sends article text to a third party. If the key is missing or the call fails, the rule-based summary is printed instead. The tests use a fake HTTP client, so the live call is untested until a key is added.
- **SQLite.** One file, no setup, enough for this volume.

## Steps followed

1. Read the brief and checked the free-plan limits (200 credits/day, 10 articles per request, 12-hour delay, 100-character queries, no full content).
2. Set up the environment and repo, then the config (company list).
3. Made one real API call (Amazon) and inspected the response: sentiment is included, `content` is locked, and a loose query returns many shopping-deal articles.
4. Designed the schema and tested it against that saved real response (`sample_data/real_amzn.json`).
5. Added the relevance filter and aliases after seeing what the real data looked like.
6. Built the fetcher, summary and CLI, with a flow test driven by the saved response.
7. Changed the fetching approach to two combined queries plus whole-database tagging.
8. Ran it live; fixed a bug the mocked tests missed and a false match from "Google News" boilerplate.

## Limitations

- Each request returns at most 10 articles shared among about 6 companies, so busy companies (Amazon, Google, Walmart) can crowd out quieter ones. No paging is done.
- The search also matches article bodies, which the free plan hides, so some results are dropped because the title and description never name the company.
- Retailer mentions ("on sale at Amazon") and automated stock-holding posts still count as being about the company.
- Matching is by name and ticker only; there is no disambiguation beyond that.
- Articles arrive about 12 hours late on the free plan.
- The daily credit count only includes requests made through this app.

## Use of AI

I used GitHub Copilot (agent mode in VS Code) to build this. It wrote the code and tests step by step while I directed the work, reviewed the results, and made the design calls above (for example the relevance rule, tagging the whole database, the two-query approach, and which aliases to add). Copilot suggested options and trade-offs, such as the credit math, SQLite and the summary approach.

<!-- Edit this section so it describes what you actually did, including which model you used. -->
