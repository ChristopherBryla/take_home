-- Articles that were stored but don't mention any of the 11 companies.
SELECT a.pub_date, a.source_name, a.title
FROM articles a
LEFT JOIN article_companies ac USING (article_id)
WHERE ac.article_id IS NULL
ORDER BY a.pub_date DESC
LIMIT 20;
