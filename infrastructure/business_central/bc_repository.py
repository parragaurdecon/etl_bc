# infrastructure/business_central/bc_repository.py

"""
infrastructure/business_central/bc_repository.py
Implementación del repositorio de Business Central usando BCClient.
Añade logging y manejo básico de errores/valores nulos del cliente.
"""
import logging
from typing import Dict, Any, Optional

# Asumiendo interfaces y cliente en rutas accesibles
try:
    # from domain.repositories.interfaces import BusinessCentralRepositoryInterface # Descomentar si usas interfaz
    from infrastructure.business_central.bc_client import BCClient
except ImportError as e:
     logging.critical(f"Error importando dependencias en BCRepository: {e}")
     # class BusinessCentralRepositoryInterface: pass # Placeholder si no usas interfaz
     BCClient = None

# Quitar 'BusinessCentralRepositoryInterface' si no la defines/usas
class BCRepository: # (BusinessCentralRepositoryInterface):
    """
    Implementa operaciones para obtener datos de BC vía BCClient.
    Maneja respuestas None y devuelve estructuras vacías consistentes.
    Distingue entre llamadas API v2 (por ID) y OData v4 (por Nombre, según URLs de ejemplo).
    """
    def __init__(self, bc_client: BCClient):
        if BCClient is None: raise ImportError("Clase BCClient no importada.")
        if not isinstance(bc_client, BCClient): raise TypeError("bc_client debe ser instancia de BCClient.")
        self.bc_client = bc_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("BCRepository inicializado.")

    def _handle_client_response(self, response: Optional[Dict[str, Any]], operation_name: str, default_empty: Any = {"value": []}) -> Optional[Dict[str, Any]]:
        """Helper para manejar respuestas del cliente."""
        if response is None:
            self.logger.warning(f"Operación cliente '{operation_name}' devolvió None. Se devuelve valor por defecto: {default_empty}")
            return default_empty
        # Podríamos añadir validación de 'value' si siempre se espera
        # if default_empty == {"value": []} and (not isinstance(response, dict) or "value" not in response):
        #    self.logger.error(f"Respuesta inesperada de '{operation_name}': {response}. Se esperaba {{'value': [...]}}.")
        #    return {"value": []}
        self.logger.debug(f"Operación cliente '{operation_name}' retornó datos.")
        return response

    # --- Métodos API v2.0 (usan company_id) ---
    def get_companies(self) -> Dict[str, Any]:
        self.logger.info("Repositorio: Obteniendo compañías (API v2)...")
        try:
            data = self.bc_client.fetch_companies()
            return self._handle_client_response(data, "fetch_companies") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_projects(self, company_id: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo proyectos (API v2) para Cia ID: {company_id}")
        if not company_id: return {"value": []}
        try:
            data = self.bc_client.fetch_projects(company_id)
            return self._handle_client_response(data, f"fetch_projects({company_id})") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_customers(self, company_id: str) -> Dict[str, Any]:
         self.logger.info(f"Repositorio: Obteniendo clientes (API v2) para Cia ID: {company_id}")
         if not company_id: return {"value": []}
         try:
             data = self.bc_client.fetch_customers(company_id)
             return self._handle_client_response(data, f"fetch_customers({company_id})") or {"value": []}
         except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_project_tasks(self, company_id: str, project_id: str) -> Dict[str, Any]:
         self.logger.info(f"Repositorio: Obteniendo tareas Proy ID: {project_id} (Cia ID: {company_id})")
         if not company_id or not project_id: return {"value": []}
         try:
             data = self.bc_client.fetch_project_tasks(company_id, project_id)
             return self._handle_client_response(data, f"fetch_project_tasks({company_id},{project_id})") or {"value": []}
         except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_purchase_invoices(self, company_id: str) -> Dict[str, Any]:
        """Wrapper de client.fetch_purchase_invoices."""
        self.logger.info(f"Repositorio: purchaseInvoices (API v2) Cia ID: '{company_id}'")
        if not company_id:
            return {"value": []}
        try:
            data = self.bc_client.fetch_purchase_invoices(company_id)
            return self._handle_client_response(data, f"fetch_purchase_invoices('{company_id}')") or {"value": []}
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            return {"value": []}

    def get_purchase_invoice_lines(self, company_id: str) -> Dict[str, Any]:
        """Wrapper de client.fetch_purchase_invoices_lines."""
        self.logger.info(f"Repositorio: purchaseInvoiceLines (API v2) Cia ID: '{company_id}'")
        if not company_id:
            return {"value": []}
        try:
            data = self.bc_client.fetch_purchase_invoices_lines(company_id)
            return self._handle_client_response(data, f"fetch_purchase_invoices_lines('{company_id}')") or {"value": []}
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            return {"value": []}


    # --- Métodos ODataV4 (usan company_name) ---
    def get_job_ledger_entries(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo JobLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_job_ledger_entries_odata(company_name)
            return self._handle_client_response(data, f"fetch_job_ledger_entries_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_job_task_line_subform(self, company_name: str) -> Dict[str, Any]:
        """
        Llama al client y maneja errores/None → {'value': []}
        """
        self.logger.info(f"Repositorio: Obteniendo JobTaskLineSubform (OData) Cia: '{company_name}'")
        if not company_name:
            return {"value": []}
        try:
            data = self.bc_client.fetch_job_task_line_subform_odata(company_name)
            return self._handle_client_response( data, f"fetch_job_task_line_subform_odata('{company_name}')") or {"value": []}
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            return {"value": []}

    def get_job_list(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo Job_List (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_job_list_odata(company_name)
            return self._handle_client_response(data, f"fetch_job_list_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_job_planning_lines(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo Job_Planning_Lines (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_job_planning_lines_odata(company_name)
            return self._handle_client_response(data, f"fetch_job_planning_lines_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_job_task_lines(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo Job_Task_Lines (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_job_task_lines_odata(company_name)
            return self._handle_client_response(data, f"fetch_job_task_lines_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_customer_list(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo CustomerList (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_customer_list_odata(company_name)
            return self._handle_client_response(data, f"fetch_customer_list_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_customer_ledger_entries(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo CustomerLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_customer_ledger_entries_odata(company_name)
            return self._handle_client_response(data, f"fetch_customer_ledger_entries_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_vendor_list(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo VendorList (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_vendor_list_odata(company_name)
            return self._handle_client_response(data, f"fetch_vendor_list_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_vendor_ledger_entries(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo VendorLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_vendor_ledger_entries_odata(company_name)
            return self._handle_client_response(data, f"fetch_vendor_ledger_entries_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_purchase_documents(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo purchaseDocuments (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_purchase_documents_odata(company_name)
            return self._handle_client_response(data, f"fetch_purchase_documents_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_sales_documents(self, company_name: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo salesDocuments (OData) Cia: '{company_name}'")
        if not company_name: return {"value": []}
        try:
            data = self.bc_client.fetch_sales_documents_odata(company_name)
            return self._handle_client_response(data, f"fetch_sales_documents_odata('{company_name}')") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

     # --- Otros métodos existentes (get_company_raw_data, etc.) SIN CAMBIOS ---
    def get_company_raw_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"Repositorio: Obteniendo datos raw (API v2) Cia ID: {company_id}")
        if not company_id: return None
        try:
            data = self.bc_client.fetch_company_raw_data(company_id)
            return self._handle_client_response(data, f"fetch_company_raw_data({company_id})", default_empty=None)
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return None

    def get_entity_definitions(self, company_id: str) -> Dict[str, Any]:
        self.logger.info(f"Repositorio: Obteniendo entity definitions (API v2) Cia ID: {company_id}")
        if not company_id: return {"value": []}
        try:
            data = self.bc_client.fetch_entity_definitions(company_id)
            return self._handle_client_response(data, f"fetch_entity_definitions({company_id})") or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}