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
    from domain.repositories.interfaces import BusinessCentralRepositoryInterface
    from infrastructure.business_central.bc_client import BCClient
except ImportError as e:
     logging.critical(f"Error importando dependencias en BCRepository: {e}")
     BusinessCentralRepositoryInterface = None
     BCClient = None

class BCRepository(BusinessCentralRepositoryInterface):
    """
    Implementa las operaciones para obtener datos de Business Central
    a través del BCClient, manejando posibles respuestas nulas del cliente.
    """
    def __init__(self, bc_client: BCClient):
        """
        Inicializa el repositorio con una instancia de BCClient.

        :param bc_client: Cliente para interactuar con la API de BC.
        :raises TypeError: Si bc_client no es una instancia de BCClient.
        """
        if BCClient is None: # Comprobar importación
             raise ImportError("Clase BCClient no importada correctamente.")
        if not isinstance(bc_client, BCClient):
             raise TypeError("bc_client debe ser una instancia de BCClient.")
        self.bc_client = bc_client
        self.logger = logging.getLogger(__name__)
        self.logger.info("BCRepository inicializado.")

    def _handle_client_response(self, response: Optional[Dict[str, Any]], operation_name: str, default_empty: Any = {"value": []}) -> Dict[str, Any]:
        """
        Helper interno para verificar y loguear respuestas del cliente.
        Devuelve la respuesta si es válida, o un valor por defecto vacío.
        """
        if response is None:
            self.logger.warning(f"La operación '{operation_name}' no devolvió datos (respuesta None del cliente).")
            return default_empty
        # Podríamos añadir más validaciones aquí si fuera necesario (ej. verificar presencia de 'value')
        self.logger.debug(f"Operación '{operation_name}' devolvió datos.")
        return response

    def get_companies(self) -> Dict[str, Any]:
        """Obtiene compañías. Devuelve {"value": []} si falla."""
        self.logger.info("Repositorio: Obteniendo compañías...")
        try:
            data = self.bc_client.fetch_companies()
            return self._handle_client_response(data, "fetch_companies")
        except Exception as e:
            # Capturar cualquier excepción inesperada del cliente o la llamada
            self.logger.error(f"Error inesperado en get_companies: {e}", exc_info=True)
            return {"value": []} # Devolver vacío consistente

    def get_entity_definitions(self, company_id: str) -> Dict[str, Any]:
        """Obtiene entityDefinitions para una compañía. Devuelve {"value": []} si falla."""
        self.logger.info(f"Repositorio: Obteniendo entity definitions para compañía ID: {company_id}")
        if not company_id:
            self.logger.warning("get_entity_definitions llamado sin company_id.")
            return {"value": []}
        try:
            data = self.bc_client.fetch_entity_definitions(company_id)
            return self._handle_client_response(data, f"fetch_entity_definitions({company_id})")
        except Exception as e:
            self.logger.error(f"Error inesperado en get_entity_definitions para {company_id}: {e}", exc_info=True)
            return {"value": []}

    def get_projects(self, company_id: str) -> Dict[str, Any]:
        """Obtiene proyectos para una compañía. Devuelve {"value": []} si falla."""
        self.logger.info(f"Repositorio: Obteniendo proyectos para compañía ID: {company_id}")
        if not company_id:
            self.logger.warning("get_projects llamado sin company_id.")
            return {"value": []}
        try:
            data = self.bc_client.fetch_projects(company_id)
            return self._handle_client_response(data, f"fetch_projects({company_id})")
        except Exception as e:
            self.logger.error(f"Error inesperado en get_projects para {company_id}: {e}", exc_info=True)
            return {"value": []}

    def get_company_raw_data(self, company_id: str) -> Optional[Dict[str, Any]]:
        """Obtiene datos raw de una compañía. Devuelve None si falla."""
        self.logger.info(f"Repositorio: Obteniendo datos raw para compañía ID: {company_id}")
        if not company_id:
            self.logger.warning("get_company_raw_data llamado sin company_id.")
            return None
        try:
            # Usar un default diferente para indicar fallo vs. no encontrado
            data = self.bc_client.fetch_company_raw_data(company_id)
            return self._handle_client_response(data, f"fetch_company_raw_data({company_id})", default_empty=None)
        except Exception as e:
            self.logger.error(f"Error inesperado en get_company_raw_data para {company_id}: {e}", exc_info=True)
            return None

    def get_project_tasks(self, company_id: str, project_id: str) -> Dict[str, Any]:
        """Obtiene tareas de proyecto. Devuelve {"value": []} si falla."""
        self.logger.info(f"Repositorio: Obteniendo tareas para proyecto ID: {project_id} (Compañía: {company_id})")
        if not company_id or not project_id:
            self.logger.warning("get_project_tasks llamado sin company_id o project_id.")
            return {"value": []}
        try:
            data = self.bc_client.fetch_project_tasks(company_id, project_id)
            return self._handle_client_response(data, f"fetch_project_tasks({company_id}, {project_id})")
        except Exception as e:
            self.logger.error(f"Error inesperado en get_project_tasks para {project_id}: {e}", exc_info=True)
            return {"value": []}

    def get_entities(self) -> Dict[str, Any]:
        """Obtiene entidades generales (si el cliente lo soporta). Devuelve {"value": []} si falla."""
        self.logger.info("Repositorio: Obteniendo entidades generales...")
        try:
            # Verificar si el método existe en el cliente antes de llamarlo
            if hasattr(self.bc_client, 'fetch_entities') and callable(getattr(self.bc_client, 'fetch_entities')):
                data = self.bc_client.fetch_entities()
                return self._handle_client_response(data, "fetch_entities")
            else:
                self.logger.warning("El método 'fetch_entities' no está implementado en BCClient.")
                return {"value": []}
        except Exception as e:
            self.logger.error(f"Error inesperado en get_entities: {e}", exc_info=True)
            return {"value": []}