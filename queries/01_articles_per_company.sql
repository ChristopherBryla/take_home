-- How many articles are linked to each company?
SELECT company, COUNT(*) AS articles
FROM article_companies
GROUP BY company
ORDER BY articles DESC;
