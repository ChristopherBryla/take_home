-- Articles about one company that our app stored in the last hour.
-- Change 'Amazon' to another company, and '-1 hour' to e.g. '-30 minutes' or '-1 day'.
-- To filter by when the article was PUBLISHED instead, replace a.first_seen_at with a.pub_date
-- (the free plan delays articles by about 12 hours, so use a window of '-24 hours' or more).
-- All times are UTC.
SELECT a.first_seen_at, a.pub_date, a.source_name, a.sentiment, a.title
FROM articles a
JOIN article_companies ac USING (article_id)
WHERE ac.company = 'Amazon'
  AND a.first_seen_at >= datetime('now', '-1 day')
ORDER BY a.first_seen_at DESC;
