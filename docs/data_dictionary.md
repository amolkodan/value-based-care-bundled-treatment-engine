# Data dictionary

This dictionary summarizes the reference tables in `sql/schema/postgres.sql`.

## Core entities

### vbc.member

- member_id: Unique member identifier
- birth_date: Date of birth
- sex: Administrative sex
- zip3: First three digits of ZIP code

### vbc.member_eligibility

- member_id: References vbc.member
- coverage_start, coverage_end: Coverage window
- payer: Payer name or id
- product: Product line

### vbc.provider

- provider_id: Unique provider identifier
- npi: National Provider Identifier
- taxonomy: Provider taxonomy
- organization: Organization name

### vbc.claim_header

- claim_id: Unique claim identifier
- member_id: References vbc.member
- service_start, service_end: Service window
- claim_type: Inpatient, outpatient, professional, pharmacy
- bill_type, place_of_service, revenue_center: Claim classification fields
- admitting_dx, primary_dx: Diagnosis fields

### vbc.claim_line

- claim_line_id: Unique line identifier
- claim_id: References vbc.claim_header
- line_number: Line number
- hcpcs: Procedure code (CPT/HCPCS)
- modifier: Procedure modifier
- units: Units
- allowed_amount: Allowed amount
- paid_amount: Paid amount
- charge_amount: Charge amount

### vbc.rx_claim_header / vbc.rx_claim_line

- rx_claim_id: Pharmacy claim identifier
- fill_date: Date of fill
- days_supply: Days supply
- ndc11: 11-digit NDC (normalized without dashes in assignment logic)
- allowed_amount / paid_amount / ingredient_cost: Financial fields

### vbc.episode_definition / vbc.episode_rule / vbc.episode_rule_window

- episode_id: Bundle / episode catalog key
- rule_role: INDEX, INCLUSION, or EXCLUSION
- code_system: ICD10, CPT, HCPCS, NDC
- code_set_id or code_value: Exactly one per rule row
- rule_weight / specificity_score: Weighted split scoring knobs for overlapping episodes
- anchor_offset_days_pre / post: Episode window around anchor date

### vbc.member_episode_instance / vbc.claim_episode_assignment

- Anchor date and window bounds for each triggered episode
- claim_source: medical or pharmacy; links to claim_header or rx_claim_line
- allocation_weight / allocation_pct: Normalized overlap allocation values
- allocated_allowed_amount / allocated_paid_amount: Amounts split across matched bundles
- match_explanation: JSON text for audit

## Value based care

### vbc.attribution

- member_id: Member attribution
- provider_id: Attributed provider
- attribution_method: Method or algorithm label

### vbc.contract

- contract_id: Contract identifier
- contract_type: Shared savings, capitation, bundle

### vbc.contract_benchmark

- benchmark_pmpm: Benchmark allowed PMPM
- quality_withhold_rate: Withhold rate applied for quality

### vbc.quality_event

- measure_id: Measure identifier
- numerator, denominator: Reporting elements
- event_date: Date for the measure event
