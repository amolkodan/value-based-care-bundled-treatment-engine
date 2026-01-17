from __future__ import annotations

import argparse

from vbc_claims.etl.synthetic import generate_synthetic_claims_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--rows", type=int, default=20000)
    parser.add_argument("--members", type=int, default=2000)
    parser.add_argument("--providers", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    generate_synthetic_claims_dataset(
        output_dir=args.output_dir,
        rows=args.rows,
        members=args.members,
        providers=args.providers,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
