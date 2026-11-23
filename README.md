# Company News Tracker

A small app that collects news about 11 companies from [NewsData.io](https://newsdata.io) (free plan), stores it in SQLite, and answers questions like *"What has the news said about AMZN?"*.

## How to run

Developed and tested on Python 3.13.

1. Activate Environment in Terminal:
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

2. Create .env file and input your api key
    copy .env.example .env     

3. Open and Run app.py, it will fetch data every 15 minutes and store in a database. (Ctrl + C when you are done fetching data)

4. Explore the data. The news articles are stored in a database (news.db)

    4a. Run ask.py to ask questions about the news articles in the database 
    4b. Run query.py to look at the data stored in the database





## Decisions

- **Credit budget.** Free plan = 200 credits/day, 1 credit per request. Two requests per 15-minute tick = 96 x 2 = 192 credits/day. The app stops fetching once the day's logged requests reach 200. Failed requests are logged and counted as used.
- **Two queries, two calls per tick.** One query per company would need 1,056 credits/day, and one query cannot hold all 11 companies. Two queries per tick is 96 x 2 = 192 credits/day and still searches every company every 15 minutes. A single request returns at most 10 articles, shared by every company in that query, so a busy company can crowd out the others in its group; I spread the busy companies across the two queries (Amazon and Nvidia in one, Alphabet and Walmart in the other) to limit that.
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
9. Fixed those: ignored the boilerplate, grouped copies of a story by title in the summary, and tried a rotating layout (a busy-company query every tick, smaller groups taking turns) before going back to two queries that both run every tick, with the busy companies spread across them.
10. Added read-only SQL query files and a `query` command for exploring the data, and the optional `--llm` answer for questions the rule-based summary can't handle.

## Limitations

- Each request returns at most 10 articles shared by every company in its query, and no paging is done, so a busy company can still miss articles published between ticks and crowd out the quieter companies in its query.
- The search also matches article bodies, which the free plan hides, so some results are dropped because the title and description never name the company.
- Retailer mentions ("on sale at Amazon"), shopping-deal articles and automated stock-holding posts still count as being about the company, so the topic list and sentiment tally can be noisy.
- Matching is by name and ticker only; there is no disambiguation beyond that.
- Copies of a story are only grouped when their titles are identical (ignoring case and spacing).
- The default `ask` only recognizes a company name in the question; the rest of the wording is ignored, so it cannot answer specific questions. `--llm` is meant for those.
- Berkshire Hathaway got no articles in live tests: its search results were dominated by automated stock-holding posts that only mention it in the article body (hidden on the free plan), so none named it in the title or description. Real Berkshire news may exist further down the results, which would need paging or a title-only search; I did not pursue that.
- Articles arrive about 12 hours late on the free plan.
- The daily credit count only includes requests made through this app.

## Use of AI

I used GitHub Copilot (agent mode in VS Code) to build this. It helped write the code and tests step by step while I directed the work, reviewed the results, and made the design calls above (for example the relevance rule, tagging the whole database, the query layout, which aliases to add, and making the language-model answer optional). Copilot suggested options and trade-offs, such as the credit math, SQLite and the summary approach.