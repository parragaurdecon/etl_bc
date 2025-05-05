# application/use_cases/bc_use_cases.py

"""
application/use_cases/bc_use_cases.py
Casos de uso para interactuar con Business Central, incluyendo transformaciones básicas.
Coordina la obtención de datos (vía Repositorio) y su posible transformación (vía Servicio).
Todos los métodos get_company_* aceptan (company_id, context) por consistencia de firma,
aunque solo los métodos OData usan activamente el contexto para buscar el nombre.
"""
import logging
from typing import Dict, Any, Optional

# Asumiendo que las interfaces/clases están correctamente ubicadas
try:
    # from domain.repositories.interfaces import BusinessCentralRepositoryInterface
    from infrastructure.business_central.bc_repository import BCRepository as BusinessCentralRepositoryInterface # Usar clase concreta si no hay interfaz
    from domain.services.transform_service import TransformService
except ImportError as e:
     logging.critical(f"Error importando dependencias de dominio/repositorio en BCUseCases: {e}")
     BusinessCentralRepositoryInterface = None
     TransformService = None

class BCUseCases:
    """
    Clase que orquesta la obtención y la lógica de negocio (incluyendo transformaciones)
    para datos de Business Central. Las transformaciones específicas se delegan a TransformService.
    """

    def __init__(self, bc_repository: BusinessCentralRepositoryInterface, transform_service: TransformService):
        """
        Inicializa los casos de uso con las dependencias necesarias.

        :param bc_repository: Repositorio para acceder a los datos de BC.
        :param transform_service: Servicio para aplicar transformaciones a los datos.
        """
        if BusinessCentralRepositoryInterface is None or TransformService is None:
            raise ImportError("Dependencias de Repositorio/Servicio no cargadas correctamente en BCUseCases.")
        # Ajustar la comprobación si no usas una interfaz formal
        if not hasattr(bc_repository, 'get_companies'): raise TypeError("bc_repository debe tener métodos esperados.")
        if not isinstance(transform_service, TransformService): raise TypeError("transform_service debe ser instancia de TransformService.")

        self.bc_repository = bc_repository
        self.transform_service = transform_service
        self.logger = logging.getLogger(__name__)

    # --- Helper Interno (Sigue siendo útil para métodos OData) ---
    def _get_company_name_from_id(self, company_id: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Intenta obtener el nombre de la compañía usando el ID, buscando en el contexto.
        Esencial para traducir ID a Nombre para llamadas OData que lo requieran.
        """
        self.logger.debug(f"Buscando nombre para company_id: {company_id}")
        companies_data = context.get("companies_json", {})
        companies_list = companies_data.get("value", [])
        if not companies_list:
            self.logger.warning("No hay lista de compañías ('companies_json') en el contexto para buscar nombre por ID.")
            return None

        for comp in companies_list:
            if comp.get("id") == company_id:
                name = comp.get("name")
                if name:
                     self.logger.debug(f"Nombre encontrado para ID {company_id}: '{name}'")
                     return name
                else:
                     self.logger.warning(f"Compañía con ID {company_id} encontrada pero sin campo 'name'.")
                     return None

        self.logger.warning(f"No se encontró compañía con ID '{company_id}' en context['companies_json'].")
        return None

    # --- Casos de Uso (Todos aceptan company_id y context) ---

    def get_companies(self) -> Dict[str, Any]:
        """Obtiene compañías y aplica filtro de exclusión."""
        self.logger.info("Use Case: Obteniendo compañías filtradas...")
        try:
            raw_data = self.bc_repository.get_companies()
            if not raw_data or "value" not in raw_data: return {"value": []}
            filtered_data = self.transform_service.filter_companies(raw_data)
            self.logger.info(f"Compañías filtradas. Resultado: {len(filtered_data.get('value',[]))}.")
            return filtered_data
        except Exception as e: self.logger.error(f"Error en get_companies: {e}", exc_info=True); return {"value": []}

    # Métodos API V2: Aceptan context por consistencia, pero lo ignoran
    def get_company_projects(self, company_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Obtiene proyectos de una compañía (API v2). Ignora el contexto."""
        self.logger.info(f"Use Case: Obteniendo proyectos (API v2) para Cia ID: {company_id}")
        if not company_id: self.logger.warning("ID de compañía vacío."); return {"value": []}
        try:
            data = self.bc_repository.get_projects(company_id) # Llama al repo solo con ID
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_customers(self, company_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
         """Obtiene clientes de una compañía (API v2). Ignora el contexto."""
         self.logger.info(f"Use Case: Obteniendo clientes (API v2) para Cia ID: {company_id}")
         if not company_id: self.logger.warning("ID de compañía vacío."); return {"value": []}
         try:
             data = self.bc_repository.get_customers(company_id) # Llama al repo solo con ID
             return data or {"value": []}
         except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    # Este método tiene firma diferente, lo dejamos como está
    def get_project_tasks_for_project(self, company_id: str, project_id: str) -> Dict[str, Any]:
         """Obtiene tareas de proyecto (API v2)."""
         self.logger.info(f"Use Case: Obteniendo Tareas Proy: {project_id} (Cia ID: {company_id})")
         if not company_id or not project_id: return {"value": []}
         try:
             data = self.bc_repository.get_project_tasks(company_id, project_id)
             return data or {"value": []}
         except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    # --- Casos de Uso ODataV4 (Usan context para buscar nombre por ID) ---

    def get_company_job_ledger_entries(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene JobLedgerEntries (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo JobLedgerEntries (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_job_ledger_entries(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_job_list(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene Job_List (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo Job_List (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_job_list(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_job_task_line_subform(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Caso de uso: obtener JobTaskLineSubform (OData) buscando primero el nombre de compañía.
        """
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name:
            return {"value": []}

        self.logger.info(f"Use Case: Obteniendo JobTaskLineSubform (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_job_task_line_subform(company_name)
            # Aquí podrías llamar a TransformService si quisieras limpiar columnas:
            # data = self.transform_service.drop_columns(data, {'@odata.etag'})
            return data or {"value": []}
        except Exception as e:
            self.logger.error(f"Error: {e}", exc_info=True)
            return {"value": []}

    def get_company_job_planning_lines(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene Job_Planning_Lines (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo Job_Planning_Lines (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_job_planning_lines(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_job_task_lines(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene Job_Task_Lines (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo Job_Task_Lines (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_job_task_lines(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_customer_list(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene CustomerList (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo CustomerList (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_customer_list(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_customer_ledger_entries(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene CustomerLedgerEntries (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo CustomerLedgerEntries (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_customer_ledger_entries(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_vendor_list(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene VendorList (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo VendorList (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_vendor_list(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_vendor_ledger_entries(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene VendorLedgerEntries (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo VendorLedgerEntries (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_vendor_ledger_entries(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_purchase_documents(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene purchaseDocuments (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo purchaseDocuments (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_purchase_documents(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_sales_documents(self, company_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Obtiene salesDocuments (ODataV4) buscando el nombre por ID."""
        company_name = self._get_company_name_from_id(company_id, context)
        if not company_name: return {"value": []}
        self.logger.info(f"Use Case: Obteniendo salesDocuments (OData) para Cia: '{company_name}'")
        try:
            data = self.bc_repository.get_sales_documents(company_name)
            return data or {"value": []}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    # --- Otros métodos (pueden necesitar ajuste de firma si son llamados por ExtractMultiCompanyStep) ---
    def get_company_entity_definitions(self, company_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
         """Obtiene entityDefinitions (API v2). Ignora context."""
         self.logger.info(f"Use Case: Obteniendo EntityDefinitions para Cia ID: {company_id}")
         if not company_id: return {"value": []}
         try:
             data = self.bc_repository.get_entity_definitions(company_id)
             return data or {"value": []}
         except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {"value": []}

    def get_company_raw_data(self, company_id: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Obtiene datos raw de compañía (API v2). Ignora context."""
        self.logger.info(f"Use Case: Obteniendo Datos Raw para Cia ID: {company_id}")
        if not company_id: return {}
        try:
            data = self.bc_repository.get_company_raw_data(company_id)
            return data or {}
        except Exception as e: self.logger.error(f"Error: {e}", exc_info=True); return {}

    def get_company_purchase_invoices(self, company_id: str, _: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve purchaseInvoices (API v2) para la compañía cuyo ID recibimos.
        (No hace falta nombre: la API usa ID).
        """
        if not company_id:
            return {"value": []}
        self.logger.info(f"Use Case: purchaseInvoices para Cia ID '{company_id}'")
        return self.bc_repository.get_purchase_invoices(company_id)

    def get_company_purchase_invoice_lines(self, company_id: str, _: Dict[str, Any]) -> Dict[str, Any]:
        """
        Devuelve purchaseInvoiceLines (API v2) para la compañía cuyo ID recibimos.
        """
        if not company_id:
            return {"value": []}
        self.logger.info(f"Use Case: purchaseInvoiceLines para Cia ID '{company_id}'")
        return self.bc_repository.get_purchase_invoice_lines(company_id)