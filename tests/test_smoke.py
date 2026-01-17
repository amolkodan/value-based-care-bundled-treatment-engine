from __future__ import annotations

from pathlib import Path

from vbc_claims.etl.synthetic import generate_synthetic_claims_dataset


def test_generate_synthetic_dataset(tmp_path: Path) -> None:
    paths = generate_synthetic_claims_dataset(output_dir=str(tmp_path), rows=100, members=20, providers=5, seed=1)
    assert paths.member_csv.exists()
    assert paths.claim_header_csv.exists()
    assert paths.claim_line_csv.exists()
