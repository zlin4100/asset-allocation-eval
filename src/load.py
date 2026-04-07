"""Load and validate input CSVs."""

import pandas as pd
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_csv(name: str) -> pd.DataFrame:
    path = DATA_DIR / name
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run generate_mock.py first.")
    return pd.read_csv(path)


def load_all() -> dict[str, pd.DataFrame]:
    names = [
        "client_profiles.csv",
        "strategy_weights.csv",
        "asset_returns.csv",
        "product_returns.csv",
        "risk_anchor.csv",
    ]
    return {n.replace(".csv", ""): load_csv(n) for n in names}


def validate_weights(weights: pd.DataFrame) -> None:
    """Check that weights sum to 1 per (portfolio_type, client_id)."""
    sums = weights.groupby(["portfolio_type", "client_id"])["weight"].sum()
    bad = sums[~sums.between(0.999, 1.001)]
    if len(bad) > 0:
        raise ValueError(f"Weight sums != 1:\n{bad}")
