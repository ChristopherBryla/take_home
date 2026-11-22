-- Which news sources show up most often?
SELECT source_name, COUNT(*) AS articles
FROM articles
GROUP BY source_name
ORDER BY articles DESC
LIMIT 10;
