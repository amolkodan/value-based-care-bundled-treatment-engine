from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticDatasetPaths:
    base_dir: Path

    @property
    def member_csv(self) -> Path:
        return self.base_dir / "member.csv"

    @property
    def member_eligibility_csv(self) -> Path:
        return self.base_dir / "member_eligibility.csv"

    @property
    def provider_csv(self) -> Path:
        return self.base_dir / "provider.csv"

    @property
    def claim_header_csv(self) -> Path:
        return self.base_dir / "claim_header.csv"

    @property
    def claim_line_csv(self) -> Path:
        return self.base_dir / "claim_line.csv"

    @property
    def diagnosis_csv(self) -> Path:
        return self.base_dir / "diagnosis.csv"

    @property
    def rx_claim_header_csv(self) -> Path:
        return self.base_dir / "rx_claim_header.csv"

    @property
    def rx_claim_line_csv(self) -> Path:
        return self.base_dir / "rx_claim_line.csv"


def _random_date(rng: np.random.Generator, start: date, end: date) -> date:
    delta_days = (end - start).days
    return start + timedelta(days=int(rng.integers(0, delta_days + 1)))


def generate_synthetic_claims_dataset(
    output_dir: str,
    rows: int = 20000,
    members: int = 2000,
    providers: int = 200,
    seed: int = 42,
    start_date: date = date(2025, 1, 1),
    end_date: date = date(2025, 12, 31),
) -> SyntheticDatasetPaths:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed)

    member_ids = [f"M{idx:06d}" for idx in range(1, members + 1)]
    provider_ids = [f"P{idx:06d}" for idx in range(1, providers + 1)]

    sex = rng.choice(["F", "M"], size=members)
    birth_year = rng.integers(1940, 2015, size=members)
    birth_month = rng.integers(1, 13, size=members)
    birth_day = rng.integers(1, 29, size=members)
    zip3 = rng.integers(100, 999, size=members)

    member_df = pd.DataFrame(
        {
            "member_id": member_ids,
            "first_name": [f"First{idx}" for idx in range(1, members + 1)],
            "last_name": [f"Last{idx}" for idx in range(1, members + 1)],
            "birth_date": [date(int(y), int(m), int(d)) for y, m, d in zip(birth_year, birth_month, birth_day)],
            "sex": sex,
            "zip3": zip3.astype(str),
        }
    )

    payer = rng.choice(["Medicare", "Commercial"], size=members, p=[0.55, 0.45])
    product = np.where(payer == "Medicare", "MA", rng.choice(["HMO", "PPO"], size=members))

    eligibility_df = pd.DataFrame(
        {
            "member_id": member_ids,
            "coverage_start": [start_date] * members,
            "coverage_end": [end_date] * members,
            "payer": payer,
            "product": product,
        }
    )

    provider_df = pd.DataFrame(
        {
            "provider_id": provider_ids,
            "npi": [f"{rng.integers(1000000000, 9999999999)}" for _ in provider_ids],
            "provider_name": [f"Provider{idx}" for idx in range(1, providers + 1)],
            "taxonomy": rng.choice(["207Q00000X", "208D00000X", "363LF0000X"], size=providers),
            "organization": rng.choice(["OrgA", "OrgB", "OrgC"], size=providers),
        }
    )

    claim_ids = [f"C{idx:08d}" for idx in range(1, rows + 1)]
    claim_member = rng.choice(member_ids, size=rows)
    claim_provider = rng.choice(provider_ids, size=rows)

    service_start = [_random_date(rng, start_date, end_date) for _ in range(rows)]
    service_end = [s + timedelta(days=int(rng.integers(0, 3))) for s in service_start]

    claim_type = rng.choice(["professional", "outpatient", "inpatient"], size=rows, p=[0.65, 0.25, 0.10])
    pos = np.where(claim_type == "professional", "11", np.where(claim_type == "outpatient", "22", "21"))

    revenue_center = rng.choice(["0450", "0300", "0250", "0360", "0456", "0981"], size=rows)
    bill_type = rng.choice(["131", "851", "111"], size=rows)

    dx_pool = ["E11.9", "I50.9", "I10", "J45.909", "F32.9", "M54.5", "N18.3", "I25.10", "E78.5"]

    claim_header_df = pd.DataFrame(
        {
            "claim_id": claim_ids,
            "member_id": claim_member,
            "billing_provider_id": claim_provider,
            "rendering_provider_id": claim_provider,
            "service_start": service_start,
            "service_end": service_end,
            "claim_type": claim_type,
            "bill_type": bill_type,
            "place_of_service": pos,
            "revenue_center": revenue_center,
            "admitting_dx": rng.choice(dx_pool, size=rows),
            "primary_dx": rng.choice(dx_pool, size=rows),
        }
    )

    lines_per_claim = rng.integers(1, 4, size=rows)
    total_lines = int(lines_per_claim.sum())

    procedure_pool = [
        "99213",
        "99214",
        "93000",
        "71046",
        "36415",
        "45378",
        "80053",
        "G0402",
        "27447",
        "93458",
        "J0897",
    ]

    claim_line_ids = np.arange(1, total_lines + 1)
    claim_id_for_line = np.repeat(claim_ids, lines_per_claim)

    units = rng.integers(1, 4, size=total_lines)
    allowed = np.round(rng.gamma(shape=2.0, scale=75.0, size=total_lines), 2)
    paid = np.round(allowed * rng.uniform(0.6, 1.0, size=total_lines), 2)

    claim_line_df = pd.DataFrame(
        {
            "claim_line_id": claim_line_ids,
            "claim_id": claim_id_for_line,
            "line_number": np.concatenate([np.arange(1, n + 1) for n in lines_per_claim]),
            "hcpcs": rng.choice(procedure_pool, size=total_lines),
            "modifier": rng.choice(["", "25", "59"], size=total_lines, p=[0.7, 0.2, 0.1]),
            "units": units,
            "charge_amount": np.round(allowed * rng.uniform(1.1, 1.8, size=total_lines), 2),
            "allowed_amount": allowed,
            "paid_amount": paid,
        }
    )

    diagnosis_rows = []
    for claim_id in claim_ids:
        dx_count = int(rng.integers(1, 5))
        for position in range(1, dx_count + 1):
            diagnosis_rows.append(
                {
                    "claim_id": claim_id,
                    "dx_position": position,
                    "icd10_dx": rng.choice(dx_pool),
                }
            )

    diagnosis_df = pd.DataFrame(diagnosis_rows)

    # Pharmacy: align fills with chronic conditions (overlapping episode triggers)
    ndc_metformin = "00904721880"
    ndc_lisinopril = "00069051801"
    ndc_insulin = "00169420101"
    ndc_warfarin = "00054001825"
    ndc_pool = [ndc_metformin, ndc_lisinopril, ndc_insulin, ndc_warfarin]

    rx_rows_header = []
    rx_rows_line = []
    rx_line_id = 1
    for midx, mid in enumerate(member_ids):
        if rng.random() > 0.4:
            continue
        fills = int(rng.integers(1, 5))
        for _ in range(fills):
            rx_id = f"RX{rx_line_id:09d}"
            fill_dt = _random_date(rng, start_date, end_date)
            rx_rows_header.append(
                {
                    "rx_claim_id": rx_id,
                    "member_id": mid,
                    "pharmacy_npi": f"{rng.integers(1000000000, 9999999999)}",
                    "prescriber_npi": f"{rng.integers(1000000000, 9999999999)}",
                    "fill_date": fill_dt,
                    "days_supply": int(rng.choice([30, 30, 90])),
                    "claim_status": "paid",
                }
            )
            # Bias NDC toward diabetes / cardio meds when member has related dx in any claim
            member_claims = claim_header_df[claim_header_df["member_id"] == mid]
            p_dx = "E11.9"
            p_cardio = "I50.9"
            has_dm = (member_claims["primary_dx"] == p_dx).any() or (member_claims["admitting_dx"] == p_dx).any()
            has_chf = (member_claims["primary_dx"] == p_cardio).any() or (member_claims["admitting_dx"] == p_cardio).any()
            if has_dm and rng.random() < 0.7:
                ndc_pick = ndc_metformin if rng.random() < 0.65 else rng.choice(ndc_pool)
            elif has_chf and rng.random() < 0.55:
                ndc_pick = ndc_lisinopril if rng.random() < 0.5 else rng.choice(ndc_pool)
            else:
                ndc_pick = rng.choice(ndc_pool)

            rx_allowed = float(np.round(float(rng.gamma(2.0, 40.0)), 2))
            rx_paid = float(np.round(rx_allowed * float(rng.uniform(0.65, 1.0)), 2))
            rx_rows_line.append(
                {
                    "rx_line_id": rx_line_id,
                    "rx_claim_id": rx_id,
                    "line_number": 1,
                    "ndc11": ndc_pick,
                    "drug_name": "synthetic",
                    "metric_dec_qty": float(rng.integers(30, 120)),
                    "ingredient_cost": float(np.round(rx_allowed * 0.85, 2)),
                    "allowed_amount": rx_allowed,
                    "paid_amount": rx_paid,
                }
            )
            rx_line_id += 1

    rx_header_df = pd.DataFrame(rx_rows_header)
    rx_line_df = pd.DataFrame(rx_rows_line)

    paths = SyntheticDatasetPaths(base_dir=output_path)
    member_df.to_csv(paths.member_csv, index=False)
    eligibility_df.to_csv(paths.member_eligibility_csv, index=False)
    provider_df.to_csv(paths.provider_csv, index=False)
    claim_header_df.to_csv(paths.claim_header_csv, index=False)
    claim_line_df.to_csv(paths.claim_line_csv, index=False)
    diagnosis_df.to_csv(paths.diagnosis_csv, index=False)
    if not rx_header_df.empty:
        rx_header_df.to_csv(paths.rx_claim_header_csv, index=False)
        rx_line_df.to_csv(paths.rx_claim_line_csv, index=False)

    return paths
