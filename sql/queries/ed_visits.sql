WITH ed_claims AS (
  SELECT
    ch.member_id,
    ch.claim_id,
    ch.service_start,
    SUM(cl.allowed_amount) AS allowed_amount
  FROM vbc.claim_header ch
  JOIN vbc.claim_line cl ON cl.claim_id = ch.claim_id
  WHERE (ch.place_of_service = '23' OR ch.revenue_center IN ('0450','0451','0452','0456','0459','0981'))
  GROUP BY ch.member_id, ch.claim_id, ch.service_start
)
SELECT
  date_trunc('month', service_start)::date AS month_start,
  COUNT(DISTINCT claim_id) AS ed_visits,
  COUNT(DISTINCT member_id) AS members_with_ed,
  SUM(allowed_amount) AS total_allowed
FROM ed_claims
GROUP BY date_trunc('month', service_start)::date
ORDER BY month_start;
