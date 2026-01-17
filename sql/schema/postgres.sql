CREATE SCHEMA IF NOT EXISTS vbc;

CREATE TABLE IF NOT EXISTS vbc.member (
  member_id TEXT PRIMARY KEY,
  first_name TEXT,
  last_name TEXT,
  birth_date DATE,
  sex TEXT,
  zip3 TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.provider (
  provider_id TEXT PRIMARY KEY,
  npi TEXT,
  provider_name TEXT,
  taxonomy TEXT,
  organization TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.member_eligibility (
  eligibility_id BIGSERIAL PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  coverage_start DATE NOT NULL,
  coverage_end DATE NOT NULL,
  payer TEXT NOT NULL,
  product TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.member_month (
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  month_start DATE NOT NULL,
  payer TEXT NOT NULL,
  product TEXT NOT NULL,
  PRIMARY KEY (member_id, month_start)
);

CREATE TABLE IF NOT EXISTS vbc.claim_header (
  claim_id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  billing_provider_id TEXT REFERENCES vbc.provider(provider_id),
  rendering_provider_id TEXT REFERENCES vbc.provider(provider_id),
  service_start DATE NOT NULL,
  service_end DATE NOT NULL,
  claim_type TEXT NOT NULL,
  bill_type TEXT,
  place_of_service TEXT,
  revenue_center TEXT,
  admitting_dx TEXT,
  primary_dx TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.claim_line (
  claim_line_id BIGINT PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES vbc.claim_header(claim_id),
  line_number INTEGER NOT NULL,
  hcpcs TEXT,
  modifier TEXT,
  units NUMERIC(12,2) NOT NULL,
  charge_amount NUMERIC(14,2) NOT NULL,
  allowed_amount NUMERIC(14,2) NOT NULL,
  paid_amount NUMERIC(14,2) NOT NULL
);

CREATE TABLE IF NOT EXISTS vbc.diagnosis (
  diagnosis_id BIGSERIAL PRIMARY KEY,
  claim_id TEXT NOT NULL REFERENCES vbc.claim_header(claim_id),
  dx_position INTEGER NOT NULL,
  icd10_dx TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vbc.attribution (
  attribution_id BIGSERIAL PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  provider_id TEXT NOT NULL REFERENCES vbc.provider(provider_id),
  attribution_start DATE NOT NULL,
  attribution_end DATE NOT NULL,
  method TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS vbc.contract (
  contract_id TEXT PRIMARY KEY,
  contract_name TEXT NOT NULL,
  contract_type TEXT NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.contract_benchmark (
  benchmark_id BIGSERIAL PRIMARY KEY,
  contract_id TEXT NOT NULL REFERENCES vbc.contract(contract_id),
  performance_year INTEGER NOT NULL,
  benchmark_pmpm NUMERIC(14,4) NOT NULL,
  min_savings_rate NUMERIC(6,4) NOT NULL,
  shared_savings_rate NUMERIC(6,4) NOT NULL,
  quality_withhold_rate NUMERIC(6,4) NOT NULL,
  UNIQUE (contract_id, performance_year)
);

CREATE TABLE IF NOT EXISTS vbc.quality_event (
  quality_event_id BIGSERIAL PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  measure_id TEXT NOT NULL,
  event_date DATE NOT NULL,
  numerator INTEGER NOT NULL,
  denominator INTEGER NOT NULL,
  source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_claim_header_member_dates ON vbc.claim_header (member_id, service_start, service_end);
CREATE INDEX IF NOT EXISTS idx_claim_line_claim ON vbc.claim_line (claim_id);
CREATE INDEX IF NOT EXISTS idx_diagnosis_claim ON vbc.diagnosis (claim_id);
CREATE INDEX IF NOT EXISTS idx_elig_member_dates ON vbc.member_eligibility (member_id, coverage_start, coverage_end);
CREATE INDEX IF NOT EXISTS idx_member_month_month ON vbc.member_month (month_start);
CREATE INDEX IF NOT EXISTS idx_attr_member_dates ON vbc.attribution (member_id, attribution_start, attribution_end);
