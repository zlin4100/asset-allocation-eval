"""Generate mock input data for asset-allocation-eval."""

import numpy as np
import pandas as pd
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True)

np.random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────
RISK_LEVELS = ["C1", "C2", "C3", "C4", "C5"]
LIFE_STAGES = [f"S{i}" for i in range(1, 8)]
ASSET_CLASSES = ["CASH", "BOND", "EQUITY", "ALT"]

# Products per asset class
PRODUCTS = {
    "CASH": ["MMF_001"],
    "BOND": ["BOND_001", "BOND_002"],
    "EQUITY": ["EQ_001", "EQ_002"],
    "ALT": ["ALT_001"],
}

# Monthly return params (mean, std) — annualized sense, will convert to monthly
ASSET_PARAMS = {
    "CASH":   (0.025, 0.005),
    "BOND":   (0.045, 0.040),
    "EQUITY": (0.090, 0.180),
    "ALT":    (0.065, 0.120),
}

INDEX_MONTHS = 240  # 20 years
PRODUCT_MONTHS = 60  # 5 years


# ── 1. client_profiles.csv ────────────────────────────────────────────────
def gen_client_profiles() -> pd.DataFrame:
    rows = []
    for r in RISK_LEVELS:
        for s in LIFE_STAGES:
            rows.append({
                "client_id": f"{r}_{s}",
                "risk_level": r,
                "life_stage": s,
            })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "client_profiles.csv", index=False)
    print(f"client_profiles.csv: {len(df)} rows")
    return df


# ── 2. strategy_weights.csv ───────────────────────────────────────────────
def _random_weights(n: int) -> np.ndarray:
    """Generate n random weights that sum to 1."""
    w = np.random.dirichlet(np.ones(n))
    return w


def _risk_tilt(risk_level: str) -> dict[str, float]:
    """Return target allocation tilts based on risk level."""
    idx = RISK_LEVELS.index(risk_level)
    # Higher risk -> more equity, less cash
    equity_base = 0.10 + idx * 0.15  # 0.10 .. 0.70
    cash_base = 0.40 - idx * 0.08    # 0.40 .. 0.08
    bond_base = 0.35 - idx * 0.05    # 0.35 .. 0.15
    alt_base = 1.0 - equity_base - cash_base - bond_base
    return {"CASH": cash_base, "BOND": bond_base, "EQUITY": equity_base, "ALT": alt_base}


def gen_strategy_weights(clients: pd.DataFrame) -> pd.DataFrame:
    rows = []

    for _, c in clients.iterrows():
        cid = c["client_id"]
        tilt = _risk_tilt(c["risk_level"])

        # ── Index layer: 3.0 ──
        noise_30 = {k: max(0.01, v + np.random.uniform(-0.03, 0.03)) for k, v in tilt.items()}
        total = sum(noise_30.values())
        for ac in ASSET_CLASSES:
            rows.append({
                "portfolio_type": "3.0",
                "client_id": cid,
                "asset_class": ac,
                "product_code": "",
                "weight": round(noise_30[ac] / total, 6),
            })

        # ── Index layer: 420_static ──
        noise_420 = {k: max(0.01, v + np.random.uniform(-0.05, 0.05)) for k, v in tilt.items()}
        total = sum(noise_420.values())
        for ac in ASSET_CLASSES:
            rows.append({
                "portfolio_type": "420_static",
                "client_id": cid,
                "asset_class": ac,
                "product_code": "",
                "weight": round(noise_420[ac] / total, 6),
            })

        # ── Product layer: 420_online ──
        prod_weights_420 = _gen_product_weights(tilt, jitter=0.05)
        for ac, prods in prod_weights_420.items():
            for pc, w in prods.items():
                rows.append({
                    "portfolio_type": "420_online",
                    "client_id": cid,
                    "asset_class": ac,
                    "product_code": pc,
                    "weight": w,
                })

        # ── Product layer: 3.0_mapped_product ──
        prod_weights_30 = _gen_product_weights(tilt, jitter=0.03)
        for ac, prods in prod_weights_30.items():
            for pc, w in prods.items():
                rows.append({
                    "portfolio_type": "3.0_mapped_product",
                    "client_id": cid,
                    "asset_class": ac,
                    "product_code": pc,
                    "weight": w,
                })

    df = pd.DataFrame(rows)
    # Fix rounding: normalize weights per (portfolio_type, client_id)
    for (pt, cid), grp in df.groupby(["portfolio_type", "client_id"]):
        total = grp["weight"].sum()
        df.loc[grp.index, "weight"] = grp["weight"] / total

    df["weight"] = df["weight"].round(6)
    df.to_csv(DATA_DIR / "strategy_weights.csv", index=False)
    print(f"strategy_weights.csv: {len(df)} rows")
    return df


def _gen_product_weights(tilt: dict, jitter: float) -> dict[str, dict[str, float]]:
    result = {}
    all_weights = []

    for ac in ASSET_CLASSES:
        prods = PRODUCTS[ac]
        base = max(0.01, tilt[ac] + np.random.uniform(-jitter, jitter))
        if len(prods) == 1:
            result[ac] = {prods[0]: base}
        else:
            split = np.random.dirichlet(np.ones(len(prods)))
            result[ac] = {p: round(base * s, 6) for p, s in zip(prods, split)}
        all_weights.extend(result[ac].values())

    # Normalize
    total = sum(all_weights)
    for ac in result:
        for pc in result[ac]:
            result[ac][pc] = round(result[ac][pc] / total, 6)

    return result


# ── 3. asset_returns.csv ──────────────────────────────────────────────────
def gen_asset_returns() -> pd.DataFrame:
    dates = pd.date_range("2006-01-31", periods=INDEX_MONTHS, freq="ME")
    rows = []
    for ac in ASSET_CLASSES:
        ann_mu, ann_sig = ASSET_PARAMS[ac]
        monthly_mu = ann_mu / 12
        monthly_sig = ann_sig / np.sqrt(12)
        rets = np.random.normal(monthly_mu, monthly_sig, INDEX_MONTHS)
        for d, r in zip(dates, rets):
            rows.append({
                "date": d.strftime("%Y-%m-%d"),
                "asset_class": ac,
                "return": round(r, 8),
            })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "asset_returns.csv", index=False)
    print(f"asset_returns.csv: {len(df)} rows")
    return df


# ── 4. product_returns.csv ────────────────────────────────────────────────
def gen_product_returns() -> pd.DataFrame:
    dates = pd.date_range("2021-01-31", periods=PRODUCT_MONTHS, freq="ME")
    rows = []
    for ac, prods in PRODUCTS.items():
        ann_mu, ann_sig = ASSET_PARAMS[ac]
        monthly_mu = ann_mu / 12
        monthly_sig = ann_sig / np.sqrt(12)
        for pc in prods:
            # Add tracking error relative to index
            rets = np.random.normal(monthly_mu, monthly_sig, PRODUCT_MONTHS)
            tracking = np.random.normal(0, 0.002, PRODUCT_MONTHS)
            rets = rets + tracking
            for d, r in zip(dates, rets):
                rows.append({
                    "date": d.strftime("%Y-%m-%d"),
                    "product_code": pc,
                    "asset_class": ac,
                    "return": round(r, 8),
                })

    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "product_returns.csv", index=False)
    print(f"product_returns.csv: {len(df)} rows")
    return df


# ── 5. risk_anchor.csv ───────────────────────────────────────────────────
def gen_risk_anchor(clients: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, c in clients.iterrows():
        idx = RISK_LEVELS.index(c["risk_level"])
        rows.append({
            "client_id": c["client_id"],
            "risk_level": c["risk_level"],
            "target_vol": round(0.03 + idx * 0.03, 4),  # 3% .. 15%
            "max_drawdown_tolerance": round(-0.05 - idx * 0.05, 4),  # -5% .. -25%
        })
    df = pd.DataFrame(rows)
    df.to_csv(DATA_DIR / "risk_anchor.csv", index=False)
    print(f"risk_anchor.csv: {len(df)} rows")
    return df


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Generating mock data...\n")
    clients = gen_client_profiles()
    gen_strategy_weights(clients)
    gen_asset_returns()
    gen_product_returns()
    gen_risk_anchor(clients)
    print("\nDone. Files saved to data/")
