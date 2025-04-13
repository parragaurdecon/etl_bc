# infrastructure/business_central/bc_client.py

"""
infrastructure/business_central/bc_client.py
Maneja la conexión, autenticación y peticiones GET a la API v2.0 de Business Central.
Incorpora logging y manejo de errores mejorado.
URL para fetch_companies ajustada a la versión funcional anterior.
"""
import logging
import requests
from requests.exceptions import RequestException, HTTPError
from typing import Dict, Any, Optional

try:
    from config.settings import settings
except ImportError:
     logging.critical("Error CRÍTICO: No se pudo importar 'settings' desde config.settings en BCClient.")
     class DummySettings:
         BC_TENANT_ID=None; BC_CLIENT_ID=None; BC_CLIENT_SECRET=None;
         BC_SCOPE=None; BC_ENVIRONMENT=None; BC_COMPANY_ID=None
     settings = DummySettings()

class BCClient:
    """
    Cliente para interactuar con la API v2.0 de Business Central.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando BCClient...")

        self.tenant_id: Optional[str] = getattr(settings, 'BC_TENANT_ID', None)
        self.client_id: Optional[str] = getattr(settings, 'BC_CLIENT_ID', None)
        self.client_secret: Optional[str] = getattr(settings, 'BC_CLIENT_SECRET', None)
        self.scope: Optional[str] = getattr(settings, 'BC_SCOPE', "https://api.businesscentral.dynamics.com/.default")
        self.environment: Optional[str] = getattr(settings, 'BC_ENVIRONMENT', None)

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

        # --- URL Base para endpoints DENTRO de una compañía ---
        self.base_api_url: str = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/api/v2.0"
        self.logger.debug(f"URL base de API (para endpoints de compañía) configurada: {self.base_api_url}")

        self._access_token: Optional[str] = None
        self.logger.info("BCClient inicializado correctamente.")

    def _fetch_access_token(self) -> Optional[str]:
        """Obtiene un NUEVO token de acceso desde Azure AD."""
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }
        self.logger.info("Solicitando nuevo token de acceso a Azure AD...")
        self.logger.debug(f"POST {url} con client_id={self.client_id[:5]}...")

        try:
            response = requests.post(url, headers=headers, data=data, timeout=20)
            response.raise_for_status()
            token_data = response.json()
            access_token = token_data.get('access_token')
            if access_token:
                 expires_in = token_data.get('expires_in', 'N/A')
                 self.logger.info(f"Nuevo token de acceso obtenido (expira en ~{expires_in}s).")
                 return access_token
            else:
                 self.logger.error("Respuesta de Azure AD OK pero sin 'access_token'. Respuesta: %s", token_data)
                 return None
        except HTTPError as http_err:
            self.logger.error(f"Error HTTP {http_err.response.status_code} obteniendo token: {http_err.response.reason}")
            try: self.logger.error(f"Detalles error token (Azure AD): {http_err.response.json()}")
            except: self.logger.error(f"Cuerpo error token (Azure AD): {http_err.response.text}")
            return None
        except RequestException as req_err:
            self.logger.error(f"Error de red/conexión obteniendo token: {req_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Error inesperado obteniendo token: {e}", exc_info=True)
            return None

    def get_access_token(self) -> Optional[str]:
        """Devuelve token cacheado o busca uno nuevo."""
        if not self._access_token:
            self.logger.debug("Token no cacheado o inválido, obteniendo uno nuevo.")
            self._access_token = self._fetch_access_token()
            if not self._access_token:
                 self.logger.error("Fallo crítico al obtener token de acceso.")
                 return None
        return self._access_token

    def _call_get(self, url: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Método interno GET con manejo de token y errores."""
        token = self.get_access_token()
        if not token:
            self.logger.error(f"Llamada GET abortada a '{url}' - Sin token de acceso.")
            return None

        headers = {'Authorization': f'Bearer {token}', 'Accept': 'application/json'}
        self.logger.info(f"GET {url}")
        if params: self.logger.debug(f"Params: {params}")
        self.logger.debug(f"Headers: {{'Authorization': 'Bearer <token_oculto>', 'Accept': ...}}")

        try:
            response = requests.get(url, headers=headers, params=params, timeout=60)
            if response.status_code == 401:
                 self.logger.warning("Recibido 401 Unauthorized. Intentando refrescar token y reintentar UNA VEZ.")
                 self._access_token = None
                 token = self.get_access_token()
                 if not token:
                      self.logger.error("Fallo al refrescar token tras 401.")
                      return None
                 headers['Authorization'] = f'Bearer {token}'
                 self.logger.info(f"Reintentando GET {url} con nuevo token...")
                 response = requests.get(url, headers=headers, params=params, timeout=60)

            response.raise_for_status()
            json_data = response.json()
            self.logger.info(f"Llamada GET a '{url}' exitosa ({response.status_code}).")
            if isinstance(json_data, dict) and 'value' in json_data and isinstance(json_data['value'], list):
                 self.logger.debug(f"Respuesta contiene {len(json_data['value'])} registros en 'value'.")
            return json_data
        except HTTPError as http_err:
            status_code = http_err.response.status_code
            self.logger.error(f"Error HTTP {status_code} en GET '{url}': {http_err.response.reason}")
            try: self.logger.error(f"Detalles error (API BC): {http_err.response.json()}")
            except: self.logger.error(f"Cuerpo error (API BC): {http_err.response.text}")
            return None
        except RequestException as req_err:
            self.logger.error(f"Error de red/conexión en GET '{url}': {req_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Error inesperado en GET '{url}': {e}", exc_info=True)
            return None

    # --- Métodos Públicos para Endpoints Específicos ---

    # --- MÉTODO CORREGIDO (URL Revertida) ---
    def fetch_companies(self) -> Optional[Dict[str, Any]]:
        """Obtiene la lista de compañías usando la URL que funcionaba."""
        # Esta URL incluye el environment pero NO el tenant_id en el path principal
        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/v2.0/companies"
        self.logger.debug(f"Llamando a fetch_companies con URL específica: {url}")
        return self._call_get(url)
    # --------------------------------------

    # --- Resto de métodos usan la URL BASE (que incluye tenant y environment) ---
    def fetch_company_raw_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Llamando a fetch_company_raw_data para ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})"
        return self._call_get(url)

    def fetch_entity_definitions(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Llamando a fetch_entity_definitions para ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/entityDefinitions"
        return self._call_get(url)

    def fetch_projects(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Llamando a fetch_projects para ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/projects"
        return self._call_get(url)

    def fetch_customers(self, company_id: str) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Llamando a fetch_customers para ID: {company_id}")
        if not company_id: self.logger.warning("company_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/customers"
        return self._call_get(url)

    def fetch_project_tasks(self, company_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        self.logger.debug(f"Llamando a fetch_project_tasks para Cia:{company_id}, Proj:{project_id}")
        if not company_id or not project_id: self.logger.warning("company_id o project_id vacío."); return None
        url = f"{self.base_api_url}/companies({company_id})/projects({project_id})/jobTasks"
        return self._call_get(url)

    # def fetch_entities(self) -> Optional[Dict[str, Any]]: ... # Añadir si es necesario