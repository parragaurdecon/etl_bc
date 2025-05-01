# services/eda/eda_service.py
"""Exploratory Data Analysis helpers for PostgreSQL tables.

This module lives in the *Infrastructure* ring (close to `pg_client.py`) but does **not** touch
Business‑Central.  It focuses on *reading* a persisted table and emitting a concise, tabular
report that can later be saved as CSV or logged.  The public API surface is intentionally
minimal so it can be plugged into your current pipelines as a *Step* or invoked ad‑hoc.

The main entry point is :func:`analyse_table` which returns a :class:`pandas.DataFrame`
containing, per column:

* ``data_type``              – SQLAlchemy/Python dtype (string for clarity).
* ``row_count``              – Total rows inspected.
* ``unique_values``          – ``df[col].nunique(dropna=True)``.
* ``pct_unique``             – Ratio ``unique / rows``.
* ``pct_nulls``              – ``null_count / rows``.
* ``pct_zeros``              – Only for numeric columns (else *NaN*).
* ``is_unique``              – *True* if the column can be treated as PK (== rows).
* ``most_common_value``      – Top value (mode) **excluding** nulls.
* ``freq_most_common``       – Relative frequency of the mode.
* ``mean`` / ``std`` / ``min`` / ``max`` – For numeric columns; otherwise *NaN*.

Example
-------
>>> from sqlalchemy import create_engine
>>> from eda_service import analyse_table, save_report
>>> engine = create_engine("postgresql+psycopg2://…")
>>> report_df = analyse_table(engine, "sales_invoice_header")
>>> save_report(report_df, "sales_invoice_header_eda.csv")

The resulting CSV can be shipped to your artefact store or attached as build artefact in CI.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import MetaData, Table, inspect, select
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# Public helpers
# --------------------------------------------------------------------------------------

def analyse_table(engine: Engine, table_name: str, *, schema: str | None = "public", sample: int | None = None) -> pd.DataFrame:  # noqa: D401
    """Return a DataFrame with column‑wise EDA metrics.

    Parameters
    ----------
    engine
        A live SQLAlchemy :class:`Engine` already configured with your Postgres DSN.
    table_name
        Name of the target table (without schema qualification).
    schema
        Postgres schema; *public* by default.
    sample
        If given, the query will *limit* rows to this number to speed up analysis on
        very large tables.  ``None`` means *all rows*.

    Returns
    -------
    pandas.DataFrame
        One row per column; suitable to :py:meth:`DataFrame.to_csv` or pretty‑print.
    """
    LOGGER.info("Starting EDA for %s.%s", schema, table_name)
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names(schema=schema):
        raise ValueError(f"Table '{schema}.{table_name}' not found in database")

    metadata_obj = MetaData(schema=schema)
    table: Table = Table(table_name, metadata_obj, autoload_with=engine)
    col_names: List[str] = [c.name for c in table.columns]

    # Fetch data (optionally sampled)
    stmt = select(table)  # type: ignore[arg-type]
    if sample is not None:
        stmt = stmt.limit(sample)
    try:
        df = pd.read_sql(stmt, engine, columns=col_names)
    except SQLAlchemyError as exc:
        LOGGER.exception("Failed reading table: %s", exc)
        raise

    row_count = len(df)
    metrics: Dict[str, Dict[str, Any]] = {}

    for col in df.columns:
        series = df[col]
        nulls = series.isna().sum()
        uniques = series.nunique(dropna=True)
        is_numeric = pd.api.types.is_numeric_dtype(series)

        zeros = int(series.eq(0).sum()) if is_numeric else np.nan
        pct_zeros = zeros / row_count if is_numeric and row_count else np.nan

        # Mode (most common non‑null value)
        try:
            mode_val = series.mode(dropna=True).iloc[0]
            freq_mode = series.eq(mode_val).sum() / row_count
        except (IndexError, ValueError):
            mode_val, freq_mode = np.nan, np.nan

        metrics[col] = {
            "data_type": str(series.dtype),
            "row_count": row_count,
            "unique_values": int(uniques),
            "pct_unique": uniques / row_count if row_count else np.nan,
            "pct_nulls": nulls / row_count if row_count else np.nan,
            "pct_zeros": pct_zeros,
            "is_unique": uniques == row_count,
            "most_common_value": mode_val,
            "freq_most_common": freq_mode,
            # Descriptive stats only for numeric
            "mean": series.mean() if is_numeric else np.nan,
            "std": series.std(ddof=0) if is_numeric else np.nan,
            "min": series.min() if is_numeric else np.nan,
            "max": series.max() if is_numeric else np.nan,
        }

    report_df = pd.DataFrame.from_dict(metrics, orient="index")
    report_df.index.name = "column"
    LOGGER.info("EDA for %s.%s complete", schema, table_name)
    return report_df.reset_index()


def save_report(df: pd.DataFrame, output_path: str | Path, *, index: bool = False) -> None:
    """Persist *df* to *output_path* as CSV, creating parent directories if required."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=index, sep=';')
    LOGGER.info("EDA report saved to %s", path)


# --------------------------------------------------------------------------------------
# CLI usage (optional)
# --------------------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(description="Run EDA on a Postgres table and output CSV report.")
    parser.add_argument("dsn", help="PostgreSQL SQLAlchemy DSN, e.g. postgresql+psycopg2://user:pass@host/db")
    parser.add_argument("table", help="Target table name (without schema)")
    parser.add_argument("--schema", default="public", help="Postgres schema (default: public)")
    parser.add_argument("--sample", type=int, help="Limit rows to SAMPLE for speed")
    parser.add_argument("--out", default="eda_report.csv", help="CSV destination path")
    args = parser.parse_args()

    from sqlalchemy import create_engine

    logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"))
    _engine = create_engine(args.dsn, pool_pre_ping=True)
    _df = analyse_table(_engine, args.table, schema=args.schema, sample=args.sample)
    save_report(_df, args.out)
    print("EDA report written to", args.out)
