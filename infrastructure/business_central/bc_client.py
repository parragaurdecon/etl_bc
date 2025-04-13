# infrastructure/business_central/bc_client.py

"""
infrastructure/business_central/bc_client.py
Maneja la conexión, autenticación y peticiones GET a la API de Business Central.
"""
import logging
import requests
from requests.exceptions import RequestException, HTTPError # Importar excepciones específicas
from typing import Dict, Any, Optional

# Asumiendo que settings.py está en config/ y accesible
try:
    from config.settings import settings
except ImportError:
     logging.critical("Error CRÍTICO: No se pudo importar 'settings' desde config.settings en BCClient.")
     # Definir un objeto settings dummy para evitar NameErrors, pero el cliente no funcionará
     class DummySettings:
         BC_TENANT_ID = None; BC_CLIENT_ID = None; BC_CLIENT_SECRET = None;
         BC_SCOPE = None; BC_ENVIRONMENT = None; BC_COMPANY_ID = None # BC_COMPANY_ID opcional
     settings = DummySettings()

class BCClient:
    """
    Clase que encapsula la autenticación y peticiones GET a la API de Business Central.
    Utiliza las credenciales y configuración de la instancia global 'settings'.
    """
    def __init__(self):
        """
        Inicializa el cliente cargando la configuración desde 'settings'.
        Valida la presencia de credenciales esenciales.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando BCClient...")

        # Cargar configuración desde la instancia settings
        self.tenant_id: Optional[str] = getattr(settings, 'BC_TENANT_ID', None)
        self.client_id: Optional[str] = getattr(settings, 'BC_CLIENT_ID', None)
        self.client_secret: Optional[str] = getattr(settings, 'BC_CLIENT_SECRET', None)
        self.scope: Optional[str] = getattr(settings, 'BC_SCOPE', "https://api.businesscentral.dynamics.com/.default")
        self.environment: Optional[str] = getattr(settings, 'BC_ENVIRONMENT', None)
        # self.company_id = settings.BC_COMPANY_ID # No necesario si trabajamos con múltiples

        # --- Validación de Configuración Esencial ---
        missing_configs = []
        if not self.tenant_id: missing_configs.append('BC_TENANT_ID')
        if not self.client_id: missing_configs.append('BC_CLIENT_ID')
        if not self.client_secret: missing_configs.append('BC_CLIENT_SECRET')
        if not self.scope: missing_configs.append('BC_SCOPE')
        if not self.environment: missing_configs.append('BC_ENVIRONMENT')

        if missing_configs:
            msg = f"BCClient: Faltan configuraciones esenciales en .env o settings: {', '.join(missing_configs)}"
            self.logger.error(msg)
            # Es crítico, así que lanzamos un error para detener la inicialización
            raise ValueError(msg)

        # --- URL Base de la API (evita repetición) ---
        # Asegurarse de que tenant_id y environment no sean None aquí debido a la validación anterior
        self.base_api_url: str = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/api/v2.0"

        self._access_token: Optional[str] = None # Cache simple para el token
        self.logger.info("BCClient inicializado correctamente.")

    def _fetch_access_token(self) -> Optional[str]:
        """
        Obtiene un NUEVO token de acceso (client_credentials) desde Azure AD.
        Retorna el token o None si falla.
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }
        self.logger.info("Solicitando nuevo token de acceso a Azure AD...")
        self.logger.debug(f"POST {url} con client_id={self.client_id[:5]}...") # No loguear secretos

        try:
            response = requests.post(url, headers=headers, data=data, timeout=15) # Añadir timeout
            response.raise_for_status() # Lanza HTTPError para 4xx/5xx
            token_data = response.json()
            access_token = token_data.get('access_token')
            if access_token:
                 expires_in = token_data.get('expires_in', 'N/A')
                 self.logger.info(f"Nuevo token de acceso obtenido con éxito (expira en {expires_in}s).")
                 return access_token
            else:
                 self.logger.error("La respuesta de Azure AD no contenía un 'access_token'. Respuesta: %s", token_data)
                 return None
        except HTTPError as http_err:
            self.logger.error(f"Error HTTP obteniendo token de acceso: {http_err.response.status_code} {http_err.response.reason}")
            try:
                 # Intentar loguear el cuerpo del error si es JSON
                 error_details = http_err.response.json()
                 self.logger.error(f"Detalles del error (Azure AD): {error_details}")
            except Exception:
                 self.logger.error(f"Cuerpo de la respuesta de error (Azure AD): {http_err.response.text}")
            return None
        except RequestException as req_err:
            self.logger.error(f"Error de red/conexión obteniendo token de acceso: {req_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Error inesperado obteniendo token de acceso: {e}", exc_info=True)
            return None

    def get_access_token(self) -> Optional[str]:
        """
        Devuelve el token de acceso cacheado. Si no existe o está vacío,
        intenta obtener uno nuevo.
        Retorna el token o None si no se puede obtener.
        """
        # Aquí podríamos añadir lógica para verificar expiración si tuviéramos la hora de obtención
        if not self._access_token:
            self.logger.debug("Token no cacheado, intentando obtener uno nuevo.")
            self._access_token = self._fetch_access_token()
            if not self._access_token:
                 self.logger.error("Fallo al obtener un nuevo token de acceso.")
                 return None # Falló la obtención
        # else:
        #    self.logger.debug("Usando token de acceso cacheado.")
        return self._access_token

    def _call_get(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Método interno para realizar peticiones GET a la API de BC,
        manejando la obtención/uso del token y errores comunes.
        Retorna el JSON de la respuesta o None si falla.
        """
        token = self.get_access_token()
        if not token:
            self.logger.error(f"No se pudo realizar la llamada GET a '{url}' porque no hay token de acceso.")
            return None # No hay token, no se puede llamar

        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json',
            'Company': self.company_id if hasattr(self, 'company_id') and self.company_id else None # Cabecera opcional si se necesita
        }
        # Eliminar cabecera Company si es None para evitar enviarla vacía
        headers = {k: v for k, v in headers.items() if v is not None}

        self.logger.info(f"Realizando llamada GET a: {url}")
        self.logger.debug(f"Cabeceras: { {k: (v[:10] + '...' if k=='Authorization' else v) for k,v in headers.items()} }") # Ofuscar token en log

        try:
            response = requests.get(url, headers=headers, timeout=30) # Añadir timeout
            response.raise_for_status() # Lanza HTTPError para 4xx/5xx
            json_data = response.json()
            self.logger.info(f"Llamada GET a '{url}' exitosa ({response.status_code}).")
            # Podríamos loguear el número de registros si es una lista OData
            if isinstance(json_data, dict) and 'value' in json_data and isinstance(json_data['value'], list):
                 self.logger.debug(f"Respuesta contiene {len(json_data['value'])} registros en 'value'.")
            return json_data
        except HTTPError as http_err:
            status_code = http_err.response.status_code
            self.logger.error(f"Error HTTP {status_code} en GET '{url}': {http_err.response.reason}")
            # Lógica potencial para reintentar con nuevo token si es 401
            # if status_code == 401:
            #     self.logger.warning("Recibido 401 Unauthorized. Forzando refresco de token en la próxima llamada.")
            #     self._access_token = None # Invalidar token cacheado
            #     # Podríamos reintentar la llamada aquí una vez, pero aumenta complejidad
            try:
                 error_details = http_err.response.json()
                 self.logger.error(f"Detalles del error (API BC): {error_details}")
            except Exception:
                 self.logger.error(f"Cuerpo de la respuesta de error (API BC): {http_err.response.text}")
            return None # Falló la llamada
        except RequestException as req_err:
            self.logger.error(f"Error de red/conexión en GET '{url}': {req_err}", exc_info=True)
            return None
        except Exception as e:
            self.logger.error(f"Error inesperado en GET '{url}': {e}", exc_info=True)
            return None

    # --- Métodos Públicos para Endpoints Específicos ---

    def fetch_companies(self) -> Optional[Dict[str, Any]]:
        """Obtiene la lista de compañías."""
        # La URL de companies no necesita tenant_id en la parte principal
        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/v2.0/companies"
        return self._call_get(url)

    def fetch_company_raw_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos raw de una compañía específica."""
        if not company_id:
             self.logger.warning("Se intentó obtener datos raw sin especificar company_id.")
             return None
        url = f"{self.base_api_url}/companies({company_id})" # Usar URL base
        return self._call_get(url)

    def fetch_entity_definitions(self, company_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Obtiene entityDefinitions. Si no se da company_id, obtiene las generales.
        Si se da company_id, obtiene las de esa compañía.
        """
        # El endpoint $metadata o entityDefinitions a nivel raíz puede no requerir compañía
        # Endpoint $metadata general
        # url = f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/v2.0/$metadata"
        # Endpoint entityDefinitions requiere compañía
        if not company_id:
             self.logger.warning("Se requieren company_id para fetch_entity_definitions del API v2.0 estándar.")
             # Podrías intentar llamar al endpoint raíz si existe una versión que lo permita
             # O simplemente retornar None/error
             return None

        url = f"{self.base_api_url}/companies({company_id})/entityDefinitions"
        return self._call_get(url)


    def fetch_projects(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene los proyectos de una compañía."""
        if not company_id:
             self.logger.warning("Se intentó obtener proyectos sin especificar company_id.")
             return None
        url = f"{self.base_api_url}/companies({company_id})/projects"
        return self._call_get(url)

    def fetch_project_tasks(self, company_id: str, project_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene las tareas (jobTasks) de un proyecto específico."""
        if not company_id or not project_id:
             self.logger.warning("Se intentó obtener tareas sin especificar company_id o project_id.")
             return None
        url = f"{self.base_api_url}/companies({company_id})/projects({project_id})/jobTasks"
        return self._call_get(url)

    # --- Podrías añadir métodos para otros endpoints ---