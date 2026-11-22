-- The 20 newest articles stored, tagged or not.
SELECT pub_date, source_name, sentiment, title
FROM articles
ORDER BY pub_date DESC
LIMIT 20;
