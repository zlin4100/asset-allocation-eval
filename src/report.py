"""Generate output files: CSV and markdown."""

import pandas as pd
from pathlib import Path


OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def save_csv(df: pd.DataFrame, name: str) -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / name
    df.to_csv(path, index=False, float_format="%.6f")
    print(f"  -> {path}")
    return path


def generate_markdown(
    summary_index: pd.DataFrame,
    summary_product: pd.DataFrame,
    label_a_idx: str,
    label_b_idx: str,
    label_a_prd: str,
    label_b_prd: str,
) -> str:
    lines = ["# Asset Allocation Eval — Summary Report\n"]

    lines.append("## Index Layer: {} vs {}\n".format(label_a_idx, label_b_idx))
    lines.append(_df_to_md(summary_index))
    lines.append("")

    lines.append("## Product Layer: {} vs {}\n".format(label_a_prd, label_b_prd))
    lines.append(_df_to_md(summary_product))
    lines.append("")

    return "\n".join(lines)


def save_markdown(content: str, name: str = "summary.md") -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    path = OUTPUT_DIR / name
    path.write_text(content, encoding="utf-8")
    print(f"  -> {path}")
    return path


def _df_to_md(df: pd.DataFrame) -> str:
    """Convert DataFrame to markdown table."""
    # Format floats
    formatted = df.copy()
    for col in formatted.select_dtypes(include="float").columns:
        formatted[col] = formatted[col].map(lambda x: f"{x:.4f}")

    header = "| " + " | ".join(formatted.columns) + " |"
    sep = "| " + " | ".join(["---"] * len(formatted.columns)) + " |"
    rows = []
    for _, row in formatted.iterrows():
        rows.append("| " + " | ".join(str(v) for v in row) + " |")

    return "\n".join([header, sep] + rows)
