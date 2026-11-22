-- Sentiment breakdown per company (positive / neutral / negative counts).
SELECT ac.company, a.sentiment, COUNT(*) AS articles
FROM article_companies ac
JOIN articles a USING (article_id)
GROUP BY ac.company, a.sentiment
ORDER BY ac.company, articles DESC;
