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

-- ---------------------------------------------------------------------------
-- Code sets (versioned groupings for episode rules and analytics)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vbc.code_set (
  code_set_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  code_system TEXT NOT NULL,
  version TEXT NOT NULL DEFAULT '1.0',
  effective_start DATE,
  effective_end DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.code_set_member (
  code_set_id TEXT NOT NULL REFERENCES vbc.code_set(code_set_id) ON DELETE CASCADE,
  code_value TEXT NOT NULL,
  PRIMARY KEY (code_set_id, code_value)
);

CREATE INDEX IF NOT EXISTS idx_code_set_member_value ON vbc.code_set_member (code_value);

-- ---------------------------------------------------------------------------
-- Pharmacy claims (normalized)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vbc.rx_claim_header (
  rx_claim_id TEXT PRIMARY KEY,
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  pharmacy_npi TEXT,
  prescriber_npi TEXT,
  fill_date DATE NOT NULL,
  days_supply INTEGER NOT NULL DEFAULT 30,
  claim_status TEXT NOT NULL DEFAULT 'paid',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vbc.rx_claim_line (
  rx_line_id BIGSERIAL PRIMARY KEY,
  rx_claim_id TEXT NOT NULL REFERENCES vbc.rx_claim_header(rx_claim_id) ON DELETE CASCADE,
  line_number INTEGER NOT NULL,
  ndc11 TEXT NOT NULL,
  drug_name TEXT,
  metric_dec_qty NUMERIC(12,4) NOT NULL DEFAULT 1,
  ingredient_cost NUMERIC(14,2) NOT NULL DEFAULT 0,
  allowed_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  paid_amount NUMERIC(14,2) NOT NULL DEFAULT 0,
  UNIQUE (rx_claim_id, line_number)
);

CREATE INDEX IF NOT EXISTS idx_rx_header_member_fill ON vbc.rx_claim_header (member_id, fill_date);
CREATE INDEX IF NOT EXISTS idx_rx_line_ndc ON vbc.rx_claim_line (ndc11);

-- ---------------------------------------------------------------------------
-- Episode catalog (bundled payment / episode-of-care definitions)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vbc.episode_definition (
  episode_id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL,
  clinical_domain TEXT,
  bundle_type TEXT NOT NULL DEFAULT 'episodic',
  model_version TEXT NOT NULL DEFAULT '1.0',
  effective_start DATE NOT NULL,
  effective_end DATE,
  description TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- rule_role: INDEX triggers episode instance; INCLUSION narrows claims in window; EXCLUSION removes
-- code_system: ICD10, CPT, HCPCS, NDC
CREATE TABLE IF NOT EXISTS vbc.episode_rule (
  rule_id BIGSERIAL PRIMARY KEY,
  episode_id TEXT NOT NULL REFERENCES vbc.episode_definition(episode_id) ON DELETE CASCADE,
  rule_order INTEGER NOT NULL DEFAULT 100,
  rule_role TEXT NOT NULL CHECK (rule_role IN ('INDEX', 'INCLUSION', 'EXCLUSION')),
  code_system TEXT NOT NULL CHECK (code_system IN ('ICD10', 'CPT', 'HCPCS', 'NDC')),
  code_set_id TEXT REFERENCES vbc.code_set(code_set_id),
  code_value TEXT,
  match_operator TEXT NOT NULL DEFAULT 'EQUALS' CHECK (match_operator IN ('EQUALS', 'PREFIX')),
  CONSTRAINT episode_rule_code_chk CHECK (
    (code_set_id IS NOT NULL AND code_value IS NULL) OR (code_set_id IS NULL AND code_value IS NOT NULL)
  )
);

CREATE INDEX IF NOT EXISTS idx_episode_rule_episode ON vbc.episode_rule (episode_id, rule_order);

-- Temporal window applied from anchor (index) service/fill date
CREATE TABLE IF NOT EXISTS vbc.episode_rule_window (
  window_id BIGSERIAL PRIMARY KEY,
  episode_id TEXT NOT NULL REFERENCES vbc.episode_definition(episode_id) ON DELETE CASCADE,
  anchor_offset_days_pre INTEGER NOT NULL DEFAULT 0,
  anchor_offset_days_post INTEGER NOT NULL DEFAULT 90,
  UNIQUE (episode_id)
);

-- One anchor event per member per episode per anchor date (deterministic dedup)
CREATE TABLE IF NOT EXISTS vbc.member_episode_instance (
  instance_id BIGSERIAL PRIMARY KEY,
  episode_id TEXT NOT NULL REFERENCES vbc.episode_definition(episode_id),
  member_id TEXT NOT NULL REFERENCES vbc.member(member_id),
  anchor_date DATE NOT NULL,
  window_start DATE NOT NULL,
  window_end DATE NOT NULL,
  anchor_medical_claim_id TEXT REFERENCES vbc.claim_header(claim_id),
  anchor_rx_claim_id TEXT REFERENCES vbc.rx_claim_header(rx_claim_id),
  anchor_rule_id BIGINT REFERENCES vbc.episode_rule(rule_id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE (episode_id, member_id, anchor_date)
);

CREATE INDEX IF NOT EXISTS idx_member_episode_member ON vbc.member_episode_instance (member_id, window_start, window_end);

-- Many-to-many: claims (medical whole claim or pharmacy line) to episode instances
CREATE TABLE IF NOT EXISTS vbc.claim_episode_assignment (
  assignment_id BIGSERIAL PRIMARY KEY,
  instance_id BIGINT NOT NULL REFERENCES vbc.member_episode_instance(instance_id) ON DELETE CASCADE,
  claim_source TEXT NOT NULL CHECK (claim_source IN ('medical', 'pharmacy')),
  medical_claim_id TEXT REFERENCES vbc.claim_header(claim_id),
  rx_line_id BIGINT REFERENCES vbc.rx_claim_line(rx_line_id),
  rule_priority INTEGER,
  match_explanation TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  CONSTRAINT claim_episode_one_claim_chk CHECK (
    (claim_source = 'medical' AND medical_claim_id IS NOT NULL AND rx_line_id IS NULL)
    OR (claim_source = 'pharmacy' AND rx_line_id IS NOT NULL AND medical_claim_id IS NULL)
  )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_claim_episode_assign_medical
  ON vbc.claim_episode_assignment (instance_id, medical_claim_id)
  WHERE claim_source = 'medical';

CREATE UNIQUE INDEX IF NOT EXISTS uq_claim_episode_assign_pharmacy
  ON vbc.claim_episode_assignment (instance_id, rx_line_id)
  WHERE claim_source = 'pharmacy';

CREATE INDEX IF NOT EXISTS idx_assignment_medical ON vbc.claim_episode_assignment (medical_claim_id);
CREATE INDEX IF NOT EXISTS idx_assignment_rx ON vbc.claim_episode_assignment (rx_line_id);

-- ---------------------------------------------------------------------------
-- ETL audit (idempotent loads)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS vbc.etl_load_batch (
  batch_id BIGSERIAL PRIMARY KEY,
  load_type TEXT NOT NULL,
  source_path TEXT,
  row_count INTEGER,
  started_at TIMESTAMPTZ DEFAULT NOW(),
  completed_at TIMESTAMPTZ,
  status TEXT NOT NULL DEFAULT 'running'
);
