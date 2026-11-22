-- Pull a field out of the stored raw API response. Any key the API returned
-- works here, e.g. '$.keywords', '$.creator', '$.source_url', '$.country'.
SELECT title, json_extract(raw_json, '$.ai_tag') AS topics
FROM articles
ORDER BY pub_date DESC
LIMIT 10;
