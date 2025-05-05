# infrastructure/business_central/bc_client.py

"""
infrastructure/business_central/bc_client.py
Maneja la conexión, autenticación y peticiones GET a las APIs v2.0 y ODataV4 de Business Central.
Incorpora logging y manejo de errores mejorado.
"""
import logging
import requests
from requests.exceptions import RequestException, HTTPError
from typing import Dict, Any, Optional
import urllib.parse # Necesario para codificar nombres de compañía en URL OData

# Asumiendo que settings.py está en config/ y accesible
try:
    from config.settings import settings
except ImportError:
     logging.critical("Error CRÍTICO: No se pudo importar 'settings' desde config.settings en BCClient.")
     # Definir un objeto settings dummy para evitar NameErrors
     class DummySettings:
         BC_TENANT_ID=None; BC_CLIENT_ID=None; BC_CLIENT_SECRET=None;
         BC_SCOPE=None; BC_ENVIRONMENT=None; BC_COMPANY_ID=None
     settings = DummySettings()

class BCClient:
    """
    Cliente para interactuar con las APIs v2.0 y ODataV4 de Business Central.
    Gestiona la autenticación (OAuth2 client credentials) y realiza llamadas GET.
    """
    def __init__(self):
        """
        Inicializa el cliente cargando configuración desde 'settings' y validando.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando BCClient...")

        # Cargar configuración
        self.tenant_id: Optional[str] = getattr(settings, 'BC_TENANT_ID', None)
        self.client_id: Optional[str] = getattr(settings, 'BC_CLIENT_ID', None)
        self.client_secret: Optional[str] = getattr(settings, 'BC_CLIENT_SECRET', None)
        self.scope: Optional[str] = getattr(settings, 'BC_SCOPE', "https://api.businesscentral.dynamics.com/.default")
        self.environment: Optional[str] = getattr(settings, 'BC_ENVIRONMENT', None)

        # Validación de Configuración Esencial
        missing_configs = [
            name for name, value in [
                ('BC_TENANT_ID', self.tenant_id),
                ('BC_CLIENT_ID', self.client_id),
                ('BC_CLIENT_SECRET', self.client_secret),
                ('BC_SCOPE', self.scope),
                ('BC_ENVIRONMENT', self.environment)
            ] if not value
        ]
        if missing_configs:
            msg = f"BCClient: Faltan configuraciones esenciales: {', '.join(missing_configs)}"
            self.logger.error(msg)
            raise ValueError(msg)

        # --- URLs Base ---
        # URL Base para API v2.0 (dentro de una compañía)
        self.base_api_url: str = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/api/v2.0"
        # URL Base para ODataV4 (dentro de una compañía)
        self.base_odata_url: str = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/ODataV4"
        self.logger.debug(f"URL base API v2.0: {self.base_api_url}")
        self.logger.debug(f"URL base OData v4: {self.base_odata_url}")

        self._access_token: Optional[str] = None # Cache para el token
        self.logger.info("BCClient inicializado correctamente.")

    def _fetch_access_token(self) -> Optional[str]:
        """Obtiene un NUEVO token de acceso desde Azure AD."""
        # ... (Código completo y robusto de _fetch_access_token como en respuestas anteriores) ...
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {'grant_type': 'client_credentials','client_id': self.client_id,'client_secret': self.client_secret,'scope': self.scope}
        self.logger.info("Solicitando nuevo token de acceso a Azure AD...")
        try:
            response = requests.post(url, headers=headers, data=data, timeout=20)
            response.raise_for_status(); token_data = response.json(); access_token = token_data.get('access_token')
            if access_token: self.logger.info(f"Nuevo token obtenido (expira en ~{token_data.get('expires_in','N/A')}s)."); return access_token
            else: self.logger.error("Respuesta OK pero sin 'access_token'."); return None
        except HTTPError as http_err:
            self.logger.error(f"Error HTTP {http_err.response.status_code} obteniendo token: {http_err.response.reason}")
            try: self.logger.error(f"Detalles (Azure AD): {http_err.response.json()}")
            except: self.logger.error(f"Cuerpo error (Azure AD): {http_err.response.text}")
            return None
        except RequestException as req_err: self.logger.error(f"Error red/conexión obteniendo token: {req_err}", exc_info=True); return None
        except Exception as e: self.logger.error(f"Error inesperado obteniendo token: {e}", exc_info=True); return None


    def get_access_token(self) -> Optional[str]:
        """Devuelve token cacheado o busca uno nuevo."""
        # ... (Código completo y robusto de get_access_token como en respuestas anteriores) ...
        if not self._access_token:
            self.logger.debug("Token no cacheado, obteniendo uno nuevo.")
            self._access_token = self._fetch_access_token()
            if not self._access_token: self.logger.error("Fallo al obtener token."); return None
        return self._access_token

    def _call_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Método interno GET con manejo de token y errores."""
        # ... (Código completo y robusto de _call_get como en respuestas anteriores, con reintento 401) ...
        token = self.get_access_token()
        if not token: self.logger.error(f"GET abortado a '{url}' - Sin token."); return None
        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        self.logger.info(f"GET {url}")
        if params: self.logger.debug(f"Params: {params}")
        log_headers = headers.copy(); log_headers['Authorization'] = 'Bearer <token_oculto>'
        self.logger.debug(f"Headers: {log_headers}")
        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 401:
                 self.logger.warning("Recibido 401. Refrescando token y reintentando UNA VEZ.")
                 self._access_token = None; token = self.get_access_token()
                 if not token: return None
                 headers['Authorization'] = f'Bearer {token}'
                 response = requests.get(url, headers=headers, params=params, timeout=60)
            response.raise_for_status()
            json_data = response.json()
            self.logger.info(f"GET a '{url}' exitosa ({response.status_code}).")
            if isinstance(json_data, dict) and 'value' in json_data and isinstance(json_data['value'], list):
                 self.logger.debug(f"Respuesta OData contiene {len(json_data['value'])} registros.")
            return json_data
        except HTTPError as http_err:
            self.logger.error(f"Error HTTP {http_err.response.status_code} en GET '{url}': {http_err.response.reason}")
            try: self.logger.error(f"Detalles error (API): {http_err.response.json()}")
            except: self.logger.error(f"Cuerpo error (API): {http_err.response.text}")
            return None
        except RequestException as req_err: self.logger.error(f"Error red/conexión en GET '{url}': {req_err}", exc_info=True); return None
        except Exception as e: self.logger.error(f"Error inesperado en GET '{url}': {e}", exc_info=True); return None


    # --- Helper ODataV4 ---
    def _get_odata_company_path(self, company_name: str) -> str:
         """Codifica nombre para URL ODataV4 Company('Name')."""
         encoded_name = urllib.parse.quote(company_name.replace("'", "''"))
         print('mirar aqui')
         print(f"Company('{encoded_name}')")
         return f"Company('{encoded_name}')"

    # --- Métodos Fetch API v2.0 (EXISTENTES - URL companies corregida) ---
    def fetch_companies(self) -> Optional[Dict[str, Any]]:
        """Obtiene la lista de compañías del tenant (API v2.0)."""
        # URL que funcionaba: environment SIN tenant_id
        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/v2.0/companies"
        self.logger.info(f"BCClient: Obteniendo lista de compañías desde: {url}")
        return self._call_get(url)

    def fetch_projects(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene proyectos de una compañía (API v2.0)."""
        self.logger.info(f"BCClient: Obteniendo proyectos (API v2) Cia ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/projects"
        return self._call_get(url)

    def fetch_customers(self, company_id: str) -> Optional[Dict[str, Any]]:
         """Obtiene clientes de una compañía (API v2.0)."""
         self.logger.info(f"BCClient: Obteniendo clientes (API v2) Cia ID: {company_id}")
         if not company_id: self.logger.warning("company_id vacío."); return None
         url = f"{self.base_api_url}/companies({company_id})/customers"
         return self._call_get(url)

    def fetch_project_tasks(self, company_id: str, project_id: str) -> Optional[Dict[str, Any]]:
         """Obtiene tareas (jobTasks) de un proyecto (API v2.0)."""
         self.logger.info(f"BCClient: Obteniendo tareas Proy: {project_id} (Cia ID: {company_id})")
         if not company_id or not project_id: self.logger.warning("IDs vacíos."); return None
         url = f"{self.base_api_url}/companies({company_id})/projects({project_id})/jobTasks"
         return self._call_get(url)

    def fetch_company_raw_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos raw de una compañía (API v2.0)."""
        self.logger.info(f"BCClient: Obteniendo datos raw (API v2) Cia ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})"
        return self._call_get(url)

    def fetch_entity_definitions(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene entityDefinitions (API v2.0)."""
        self.logger.info(f"BCClient: Obteniendo entity definitions (API v2) Cia ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/entityDefinitions"
        return self._call_get(url)

    def fetch_purchase_invoices(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene entityDefinitions (API v2.0)."""
        self.logger.info(f"BCClient: Obteniendo entity definitions (API v2) Cia ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/purchaseInvoices"
        return self._call_get(url)

    def fetch_purchase_invoices_lines(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene entityDefinitions (API v2.0)."""
        self.logger.info(f"BCClient: Obteniendo entity definitions (API v2) Cia ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/purchaseInvoiceLines"
        return self._call_get(url)

    # --- Métodos Fetch ODataV4 (NUEVOS - usan company_name) ---

    def fetch_job_ledger_entries_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo JobLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/JobLedgerEntries"
        print('mirar aqui')
        print(company_path)
        print(url)
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_job_task_line_subform_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        """
        Descarga JobTaskLineSubform vía ODataV4 para la compañía indicada.

        Ejemplo de URL resultante:
        https://.../ODataV4/Company('Construct...')/JobTaskLineSubform
        """
        self.logger.info(f"BCClient: Obteniendo JobTaskLineSubform (OData) Cia: '{company_name}'")
        if not company_name:
            return None
        company_path = self._get_odata_company_path(company_name)  # «Company('Nombre%20Escapado')»
        print('mirar aqui')
        print(company_path)
        url = f"{self.base_odata_url}/{company_path}/Subformulario"  # <- RUta real
        print(url)
        self.logger.debug(f"BCClient OData URL: {url}")
        return self._call_get(url)

    def fetch_job_list_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo Job_List (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        select = "No,Description,Bill_to_Customer_No,Status,Person_Responsible,Search_Description,Project_Manager"
        params = {"$select": select}
        url = f"{self.base_odata_url}/{company_path}/Job_List"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url, params=params)

    def fetch_job_planning_lines_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo Job_Planning_Lines (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        select = "Job_Task_No,Planning_Date,Planned_Delivery_Date,Document_No,Type,No,Description,Quantity,Remaining_Qty,Unit_Cost,Total_Cost,Unit_Price,Line_Amount,Qty_to_Transfer_to_Journal,Invoiced_Amount_LCY"
        params = {"$select": select}
        url = f"{self.base_odata_url}/{company_path}/Job_Planning_Lines"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url, params=params)

    def fetch_job_task_lines_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo Job_Task_Lines (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        select = "Job_No,Job_Task_No,Description,Job_Task_Type,Totaling,Job_Posting_Group,WIP_Total,WIP_Method,Start_Date,End_Date,Schedule_Total_Cost,Schedule_Total_Price,Usage_Total_Cost,Usage_Total_Price,Contract_Total_Cost,Contract_Total_Price,Remaining_Total_Cost,Remaining_Total_Price"
        params = {"$select": select}
        url = f"{self.base_odata_url}/{company_path}/Job_Task_Lines"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url, params=params)

    def fetch_customer_list_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo CustomerList (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/CustomerList"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_customer_ledger_entries_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo CustomerLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/CustomerLedgerEntries"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_vendor_list_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo VendorList (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/VendorList"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_vendor_ledger_entries_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo VendorLedgerEntries (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/VendorLedgerEntries"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_purchase_documents_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo purchaseDocuments (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/purchaseDocuments"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)

    def fetch_sales_documents_odata(self, company_name: str) -> Optional[Dict[str, Any]]:
        self.logger.info(f"BCClient: Obteniendo salesDocuments (OData) Cia: '{company_name}'")
        if not company_name: return None
        company_path = self._get_odata_company_path(company_name)
        url = f"{self.base_odata_url}/{company_path}/salesDocuments"
        self.logger.info(f"BCClient OData URL: {url}")  # <-- LOG URL
        return self._call_get(url)