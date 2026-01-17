WITH member_month AS (
  SELECT
    mm.member_id,
    mm.month_start,
    mm.payer,
    mm.product
  FROM vbc.member_month mm
), allowed AS (
  SELECT
    ch.member_id,
    date_trunc('month', ch.service_start)::date AS month_start,
    SUM(cl.allowed_amount) AS allowed_amount
  FROM vbc.claim_header ch
  JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
  GROUP BY ch.member_id, date_trunc('month', ch.service_start)::date
)
SELECT
  m.month_start,
  m.payer,
  m.product,
  COUNT(DISTINCT m.member_id) AS member_months,
  COALESCE(SUM(a.allowed_amount), 0) AS total_allowed,
  CASE WHEN COUNT(DISTINCT m.member_id) > 0 THEN COALESCE(SUM(a.allowed_amount), 0) / COUNT(DISTINCT m.member_id) ELSE 0 END AS pmpm
FROM member_month m
LEFT JOIN allowed a
  ON a.member_id = m.member_id
  AND a.month_start = m.month_start
GROUP BY m.month_start, m.payer, m.product
ORDER BY m.month_start, m.payer, m.product;
