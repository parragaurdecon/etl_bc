# tests/test_purchase_invoice_lines.py
"""
Descarga purchaseInvoices y sus líneas (purchaseInvoiceLines) para TODAS
las compañías y genera un CSV único.  No toca el resto del código.

Requisitos:
    pip install pandas
    Variables de entorno BC (USER, PASSWORD, tenant, etc.) ya configuradas.
Ejecuta:
    python -m tests.test_purchase_invoice_lines
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd
from infrastructure.business_central.bc_client import BCClient


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

LOGGER = logging.getLogger("test_purch_inv_lines")


def _fetch_lines_for_company(
    client: BCClient, company_id: str
) -> List[Dict[str, Any]]:
    """
    Devuelve todas las líneas de compra de una compañía:
        /companies({company_id})/purchaseInvoices({invoice_id})/purchaseInvoiceLines
    Añade campos CompanyId e InvoiceId a cada línea.
    """
    invoices = client.fetch_purchase_invoices(company_id) or {"value": []}
    lines_acc: List[Dict[str, Any]] = []

    for inv in invoices.get("value", []):
        inv_id = inv.get("id")
        if not inv_id:
            continue
        url = (
            f"{client.base_api_url}/companies({company_id})"
            f"/purchaseInvoices({inv_id})/purchaseInvoiceLines"
        )
        resp = client._call_get(url)  # usamos directamente el helper interno
        for ln in resp.get("value", []):
            ln["CompanyId"] = company_id
            ln["InvoiceId"] = inv_id
            lines_acc.append(ln)

    LOGGER.info("  → %s líneas", len(lines_acc))
    return lines_acc


def main() -> None:
    client = BCClient()

    company_ids = [
        c["id"] for c in client.fetch_companies().get("value", [])
    ]
    LOGGER.info("Total compañías: %d", len(company_ids))

    all_lines: List[Dict[str, Any]] = []
    for cid in company_ids:
        LOGGER.info("Procesando compañía %s", cid)
        all_lines.extend(_fetch_lines_for_company(client, cid))

    df = pd.DataFrame(all_lines)
    LOGGER.info("Líneas totales: %d", len(df))

    out = Path("purchase_invoice_lines_all.csv")
    df.to_csv(out, index=False, sep=";")
    LOGGER.info("CSV guardado en %s", out.resolve())


if __name__ == "__main__":
    main()
