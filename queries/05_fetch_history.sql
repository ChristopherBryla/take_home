-- Most recent API calls: when, whether they worked, how many results the API
-- reported, and how many articles were new to the database.
SELECT fetched_at, status, total_results, new_articles, query
FROM fetch_log
ORDER BY id DESC
LIMIT 20;
