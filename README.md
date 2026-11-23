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

Then run [app.py](app.py) (press Run in VS Code, or `python app.py`). It fetches right away and then every 15 minutes until you stop it with Ctrl+C.

Then, while it runs or after:

- **Ask questions:** run [ask.py](ask.py) and type something like `What has the news said about AMZN?`. Type `/llm` to switch to the optional OpenAI answer (and `/llm` again to switch back).
- **Explore the database:** run [query.py](query.py), pick a number from the SQL files in `queries/` or type your own SQL (read-only).

Both can also be run from a terminal, along with a few extras:

```powershell
python -m newstracker ask "What has the news said about AMZN?"
python -m newstracker ask --llm "Did Amazon announce layoffs?"   # optional: answer with OpenAI
python -m newstracker query queries\01_articles_per_company.sql  # run a read-only SQL file
python -m newstracker fetch                                      # one tick now (2 credits)
python -m newstracker retag                                      # rebuild company tags from stored articles
python -m pytest -s                                              # one end-to-end test, no API calls, no credits
```

Data is stored in `news.db` next to `app.py`. It is git-ignored, so a fresh clone starts empty until `app.py` has run. `queries/` holds a few basic SQL queries for exploring it. The test (`tests/test_flow.py`) feeds the saved response in `sample_data/sample_response.json` through the whole flow: fetch, store, tag, answer.

## How it works

1. **Fetch.** Every 15 minutes the app makes two API calls. The API caps a search query at 100 characters, so the 11 companies are split across five queries: one for the two busiest companies (Amazon and Alphabet/Google) that runs on every tick, and four smaller ones (Walmart and Nvidia; Eli Lilly, Berkshire Hathaway and GE Aerospace; ExxonMobil and NextEra; Linde and Welltower) that take turns in the second slot, so each runs about once an hour. Each query has company names, aliases and as many tickers as fit, except tickers that are also ordinary words (`GE`, `LIN`, `WELL`): the API search is not case-sensitive, so those returned unrelated articles in a live test. They are still matched, uppercase only, by our own relevance check. Which rotating query runs next is read from `fetch_log`, so it survives restarts.
2. **Store.** Every returned article goes into the `articles` table. The complete API object is kept as JSON in `raw_json`, and the fields we query on (title, description, date, source, sentiment, ...) are also stored as columns. Articles are de-duplicated on `article_id`.
3. **Tag.** After each fetch, the whole database is re-scanned and every article is linked to every company it mentions (`article_companies`). An article found by one query can therefore count for any company.
4. **Answer.** `ask` finds the company in the question (name, alias or ticker), then summarizes its linked articles: story count and date range, sentiment tally, top topics and sources, and the latest headlines. Copies of the same story from different outlets (same title) are counted once. This default answer is rule-based, free, and needs no extra key, and it answers about one company (the first one found in the question). With `--llm`, the question and the stored stories for every company it names are sent to an OpenAI model, which answers only from those articles (see below).

Tables: `articles`, `article_companies` (article-to-company links), `fetch_log` (one row per API call: query, status, total results, new articles).

## Decisions

- **Credit budget.** Free plan = 200 credits/day, 1 credit per request. Two requests per 15-minute tick = 96 x 2 = 192 credits/day. The app stops fetching once the day's logged requests reach 200. Failed requests are logged and counted as used.
- **Several queries, two calls per tick.** One query per company would need 1,056 credits/day, and one query cannot hold all 11 companies. A single request also returns at most 10 articles, shared by every company in that query, so busy companies crowd out quiet ones. Giving the busiest companies their own every-tick query and rotating smaller groups through the other slot keeps the same 192 credits/day. The cost is that the rotating groups refresh about hourly instead of every 15 minutes, which I judged acceptable because they have fewer new articles per hour.
- **Tag the whole database, not just the searched company.** Links are rebuilt from the stored text and the current matching rules, so changing an alias and running `retag` fixes old data.
- **What counts as "about a company".** An article is linked only if its title or description names the company, a known alias (Google, Exxon, Lilly, NextEra) or its ticker. Tickers must be uppercase whole words, so "well", "ge" and "lin" do not match Welltower, GE Aerospace or Linde. The boilerplate "Google News" and the name "van der Linde" (a racing driver) are ignored. Articles that match nothing are still stored.
- **Same story, many outlets.** One story is often syndicated by many outlets with different `article_id`s. The summary groups articles with the same title and counts each story once, and shows how many copies there were.
- **Sentiment comes from the API.** The free plan includes a sentiment label and scores, so no separate model is used. The summary tallies the labels. I did not look into how NewsData.io computes them, a few articles have no label, and the label describes an article's tone, not necessarily whether it is good or bad news for the company.
- **Summary is rule-based by default.** The free plan hides article `content` (and `ai_summary`), leaving only titles and descriptions, so the default summary is a roll-up of those fields rather than a model-written paragraph. Fields locked on the free plan are stored as NULL.
- **Language model is optional (`ask --llm`).** The rule-based answer only identifies the company in a question, so it cannot answer things like "Did Amazon announce layoffs?". With `--llm` and an `OPENAI_API_KEY` in `.env`, the stored stories (title, description, date, source, sentiment; one entry per distinct story, newest 40 per company) are sent to OpenAI's `gpt-5.4-mini` model (override with `OPENAI_MODEL` in `.env`) with instructions to answer only from them and to say when the data doesn't cover the question. It is opt-in because it costs money and sends article text to a third party. If the key is missing or the call fails, the rule-based summary is printed instead. It has no automated test; I checked it by hand against the real API.
- **SQLite.** One file, no setup, enough for this volume.

## Steps followed

1. Read the brief and checked the free-plan limits (200 credits/day, 10 articles per request, 12-hour delay, 100-character queries, no full content).
2. Set up the environment and repo, then the config (company list).
3. Made one real API call (Amazon) and inspected the response: sentiment is included, `content` is locked, and a loose query returns many shopping-deal articles.
4. Designed the schema and tested it against that saved real response (`sample_data/sample_response.json`).
5. Added the relevance filter and aliases after seeing what the real data looked like.
6. Built the fetcher, summary and CLI, with one end-to-end test driven by the saved response.
7. Changed the fetching approach to combined queries plus whole-database tagging, instead of one request per company.
8. Ran the first version live for about an hour (12 calls, no failures). It showed false matches ("Google News" boilerplate), the same story counted many times, and busy companies crowding out quiet ones; five of the 11 companies had no articles at all.
9. Fixed those: ignored the boilerplate, grouped copies of a story by title in the summary, and replaced the two fixed queries with the every-tick plus rotating layout.
10. Added read-only SQL query files and a `query` command for exploring the data, and the optional `--llm` answer for questions the rule-based summary can't handle.

## Limitations

- Each request returns at most 10 articles shared by every company in its query, and no paging is done, so a busy company can still miss articles published between ticks. The rotating queries refresh about hourly.
- The search also matches article bodies, which the free plan hides, so some results are dropped because the title and description never name the company.
- Retailer mentions ("on sale at Amazon"), shopping-deal articles and automated stock-holding posts still count as being about the company, so the topic list and sentiment tally can be noisy.
- Matching is by name and ticker only; there is no disambiguation beyond that.
- Copies of a story are only grouped when their titles are identical (ignoring case and spacing).
- The default `ask` only recognizes a company name in the question; the rest of the wording is ignored, so it cannot answer specific questions. `--llm` is meant for those.
- Berkshire Hathaway got no articles in live tests: its search results were dominated by automated stock-holding posts that only mention it in the article body (hidden on the free plan), so none named it in the title or description. Real Berkshire news may exist further down the results, which would need paging or a title-only search; I did not pursue that.
- Articles arrive about 12 hours late on the free plan.
- The daily credit count only includes requests made through this app.

## Use of AI

I used GitHub Copilot (agent mode in VS Code) to build this. It wrote the code and tests step by step while I directed the work, reviewed the results, and made the design calls above (for example the relevance rule, tagging the whole database, the query layout, which aliases to add, and making the language-model answer optional). Copilot suggested options and trade-offs, such as the credit math, SQLite and the summary approach.

<!-- Edit this section so it describes what you actually did, including which model you used. -->
