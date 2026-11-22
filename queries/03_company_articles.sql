-- Latest articles about one company. Change 'Amazon' to any company name
-- from config.py (e.g. 'Nvidia', 'Walmart', 'Eli Lilly').
SELECT a.pub_date, a.source_name, a.sentiment, a.title
FROM articles a
JOIN article_companies ac USING (article_id)
WHERE ac.company = 'Amazon'
ORDER BY a.pub_date DESC
LIMIT 10;
