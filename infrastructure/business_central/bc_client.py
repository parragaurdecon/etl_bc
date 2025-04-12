# infrastructure/business_central/bc_client.py

"""
infrastructure/business_central/bc_client.py
Maneja la conexión y autenticación con Business Central (obtención del token y peticiones).
"""
import requests
from config.settings import settings

class BCClient:
    """
    Clase que encapsula la autenticación y peticiones a Business Central.
    """
    def __init__(self):
        self.tenant_id = settings.BC_TENANT_ID
        self.client_id = settings.BC_CLIENT_ID
        self.client_secret = settings.BC_CLIENT_SECRET
        self.scope = settings.BC_SCOPE
        self.environment = settings.BC_ENVIRONMENT
        self.company_id = settings.BC_COMPANY_ID
        self._access_token = None

    def _fetch_access_token(self):
        """
        Obtiene el token de acceso (client_credentials).
        """
        url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'scope': self.scope
        }

        response = requests.post(url, headers=headers, data=data)
        response.raise_for_status()
        return response.json()['access_token']

    def get_access_token(self):
        """
        Devuelve el token de acceso, lo refresca si no existe.
        """
        if not self._access_token:
            self._access_token = self._fetch_access_token()
        return self._access_token

    def fetch_companies(self):
        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/v2.0/companies"
        return self._call_get(url)

    def fetch_company_raw_data(self, company_id: str):
        """
        Llama al endpoint:
        GET https://api.businesscentral.dynamics.com/v2.0/<tenant_id>/<environment>/api/v2.0/companies({company_id})/
        y devuelve el JSON de la compañía (datos de la empresa).
        """
        url = f"https://api.businesscentral.dynamics.com/v2.0/{self.tenant_id}/{self.environment}/api/v2.0/companies({company_id})/"
        return self._call_get(url)

    def fetch_entity_definitions(self, company_id: str):
        """
        Devuelve todas las entityDefinitions (tablas) para una compañía dada.
        Endpoint: /companies({companyId})/entityDefinitions
        """
        url = (
            f"https://api.businesscentral.dynamics.com/v2.0/{self.environment}/api/V2.0/"
        )
        return self._call_get(url)

    def fetch_projects(self, company_id: str):
        """
        Llama a:
        GET /v2.0/{tenant_id}/{environment}/api/v2.0/companies({companyId})/projects
        y devuelve el JSON de proyectos.
        """
        url = (
            f"https://api.businesscentral.dynamics.com/v2.0/"
            f"{self.tenant_id}/{self.environment}/api/v2.0/"
            f"companies({company_id})/projects"
        )
        return self._call_get(url)

    def fetch_project_tasks(self, company_id: str, project_id: str):
        """
        Llama a:
        GET /companies({company_id})/projects({project_id})/jobTasks
        """
        url = (
            f"https://api.businesscentral.dynamics.com/v2.0/"
            f"{self.tenant_id}/{self.environment}/api/v2.0/"
            f"companies({company_id})/projects({project_id})/jobTasks"
        )
        return self._call_get(url)

    def _call_get(self, url):
        """
        Método interno para GET requests con el token.
        """
        token = self.get_access_token()
        headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
