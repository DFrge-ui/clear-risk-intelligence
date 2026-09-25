-- Read-only examples for instance/clear.sqlite3 (SQLite with JSON functions).
-- Run against synthetic demo data only. No third-party SQL service required.

-- Dataset quality accounting: 175 = 168 + 4 + 3.
SELECT name,
       json_extract(quality, '$.total') AS source_rows,
       json_extract(quality, '$.accepted') AS accepted_rows,
       json_extract(quality, '$.duplicates') AS duplicates,
       json_extract(quality, '$.rejected') AS rejected
FROM datasets WHERE id = 'demo';

-- Exact cent totals by category; presentation converts cents to EUR.
SELECT json_extract(payload, '$.category') AS category,
       count(*) AS incident_count,
       sum(json_extract(payload, '$.loss_cents')) AS recorded_loss_cents
FROM incidents
WHERE dataset_id = 'demo'
GROUP BY category
ORDER BY recorded_loss_cents DESC;

-- Active cases without an owner, preserving source-row provenance.
SELECT incident_id,
       json_extract(payload, '$.occurred_on') AS occurred_on,
       json_extract(payload, '$.business_unit') AS business_unit,
       json_extract(payload, '$.source_row') AS source_row
FROM incidents
WHERE dataset_id = 'demo'
  AND json_extract(payload, '$.status') <> 'Resolved'
  AND json_extract(payload, '$.owner') = 'Unassigned'
ORDER BY occurred_on;
