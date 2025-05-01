# eda_main.py
"""CLI entry‑point to run EDA reports on any Postgres table.

Usage (inside Docker or local venv)::

    python -m cmd.eda_main --table sales_invoice_header --out reports/sales_invoice_header_eda.csv

Environment variables required (same as ETL main):
    * PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, PG_DB      – or PG_CONNECTION_STRING
    * LOGLEVEL (optional)                                – DEBUG, INFO, ...

The script re‑uses SqlAlchemyClient for connection pooling and the
`analyse_table` helper from *services.eda.eda_service*.
"""
from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Iterable, List

from sqlalchemy import inspect

from infrastructure.postgresql.pg_client import SqlAlchemyClient  # type: ignore
from domain.services.eda_service import analyse_table, save_report
from config.settings import Settings

LOGGER = logging.getLogger(__name__)

# --------------------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate EDA CSV reports for Postgres tables. If no --table or --all flag is provided, the script defaults to --all."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--table", help="Target table name (without schema)")
    group.add_argument("--all", action="store_true", help="Analyse *all* tables in schema")

    parser.add_argument("--schema", default="public", help="Schema (default: public)")
    parser.add_argument("--sample", type=int, help="Limit rows to SAMPLE for speed (optional)")
    parser.add_argument(
        "--out",
        default="reports",
        help="Destination folder or CSV path. If analysing many tables, it must be a folder.",
    )
    args = parser.parse_args()

    # Default behaviour: if neither flag is provided, run on *all* tables
    if not args.table and not args.all:
        args.all = True
    return args


# --------------------------------------------------------------------------------------
# Core helpers
# --------------------------------------------------------------------------------------

def _resolve_tables(engine, schema: str, table: str | None, all_flag: bool) -> List[str]:
    inspector = inspect(engine)
    if all_flag:
        return inspector.get_table_names(schema=schema)
    if table is None:
        raise ValueError("Parameter 'table' cannot be None when --table is used")
    return [table]


# --------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------

def main() -> None:
    args = _parse_args()
    logging.basicConfig(level=os.getenv("LOGLEVEL", "INFO"), format="%(asctime)s [%(levelname)s] %(message)s")

    Settings()  # initialise singleton (loads YAML/env)
    engine = SqlAlchemyClient().get_engine()

    dest_path = Path(args.out)
    if args.all and dest_path.suffix:
        raise SystemExit("--out must be a directory when --all is specified.")
    dest_path.mkdir(parents=True, exist_ok=True)

    tables = _resolve_tables(engine, args.schema, args.table, args.all)
    LOGGER.info("Running EDA for %d table(s) in schema '%s'", len(tables), args.schema)

    for tbl in tables:
        df_report = analyse_table(engine, tbl, schema=args.schema, sample=args.sample)
        outfile = dest_path / f"{tbl}_eda.csv" if dest_path.is_dir() else dest_path
        save_report(df_report, outfile)

    LOGGER.info("EDA process finished successfully")


if __name__ == "__main__":
    main()
