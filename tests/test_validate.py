from __future__ import annotations

from datetime import date

import pandas as pd
import pytest

from vbc_claims.etl.validate import validate_medical_claims


def test_validate_medical_rejects_orphan_lines() -> None:
    header = pd.DataFrame(
        {
            "claim_id": ["C1"],
            "member_id": ["M1"],
            "service_start": [date(2025, 1, 1)],
            "service_end": [date(2025, 1, 2)],
            "claim_type": ["professional"],
        }
    )
    lines = pd.DataFrame(
        {
            "claim_line_id": [1],
            "claim_id": ["C2"],
            "line_number": [1],
            "units": [1],
            "charge_amount": [100],
            "allowed_amount": [80],
            "paid_amount": [70],
        }
    )
    diagnosis = pd.DataFrame({"claim_id": ["C1"], "dx_position": [1], "icd10_dx": ["E11.9"]})
    with pytest.raises(ValueError, match="orphan"):
        validate_medical_claims(header, lines, diagnosis)
