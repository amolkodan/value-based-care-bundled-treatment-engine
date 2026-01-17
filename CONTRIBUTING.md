# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e ".[dev]"
```

## Quality gates

```bash
make lint
make type
make test
```

## Data safety

Do not add PHI. Use the synthetic data generator in `vbc-claims generate-sample`.
