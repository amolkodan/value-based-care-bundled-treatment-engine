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
- procedure_code, modifier1, modifier2: Procedure and modifiers
- ndc: NDC for pharmacy
- units: Units
- allowed_amount: Allowed amount
- paid_amount: Paid amount
- charge_amount: Charge amount

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
