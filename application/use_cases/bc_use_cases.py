"""
application/use_cases/bc_use_cases.py
Casos de uso para interactuar con Business Central, incluyendo transformaciones básicas.
"""
import logging
from typing import Dict, Any, Set # Importar Set

# Asumiendo que las interfaces/clases están correctamente ubicadas para la importación
from domain.repositories.interfaces import BusinessCentralRepositoryInterface
from domain.services.transform_service import TransformService

# IDs de Compañías a Excluir (puede vivir aquí, en config, o pasarse como argumento)
# Definirlo aquí lo hace un default para este caso de uso específico.
DEFAULT_EXCLUDED_COMPANY_IDS: Set[str] = {
    "533db2ec-6ed9-ef11-8eec-6045bd9e5a05", # MASTER
    "c0fe57e4-d5d7-ef11-b8ec-7c1e525de7b1", # test3
    "7ac53006-a8fd-ef11-9346-000d3a46cc7c", # URD0310
    "1b15ed70-98dc-ef11-9344-000d3aaf69aa", # URDE2701
}


class BCUseCases:
    """
    Clase que orquesta la obtención y la lógica de negocio (incluyendo transformaciones)
    para datos de Business Central.
    """

    def __init__(self, bc_repository: BusinessCentralRepositoryInterface, transform_service: TransformService):
        """
        Inicializa los casos de uso con las dependencias necesarias.

        :param bc_repository: Repositorio para acceder a los datos de BC.
        :param transform_service: Servicio para aplicar transformaciones a los datos.
        """
        self.bc_repository = bc_repository
        self.transform_service = transform_service
        self.logger = logging.getLogger(__name__) # Logger específico para esta clase

    def get_entities(self) -> Dict[str, Any]:
        """
        Obtiene el JSON de entidades disponibles en BC.
        """
        self.logger.info("Iniciando caso de uso: Obtener Entidades.")
        try:
            self.logger.debug("Llamando a BCRepository.get_entities...")
            entities_data = self.bc_repository.get_entities()
            self.logger.info(f"Entidades obtenidas: {len(entities_data.get('value',[]))} encontradas.")
            return entities_data
        except Exception as e:
            self.logger.error(f"Error al obtener entidades: {e}", exc_info=True)
            return {"value": []} # Devolver estructura vacía en error

    # --- MÉTODO MODIFICADO ---
    def get_companies(self, excluded_ids: Set[str] = DEFAULT_EXCLUDED_COMPANY_IDS) -> Dict[str, Any]:
        """
        Obtiene las compañías del repositorio y aplica el filtrado de exclusión
        usando el TransformService antes de devolverlas.

        :param excluded_ids: Set de IDs a excluir. Usa el default si no se provee.
        :return: Diccionario JSON con la lista de compañías filtradas.
                 Devuelve {"value": []} en caso de error.
        """
        self.logger.info("Iniciando caso de uso: Obtener Compañías Filtradas.")
        try:
            # 1. Extracción (Infrastructure)
            self.logger.debug("Llamando a BCRepository.get_companies...")
            raw_companies_data = self.bc_repository.get_companies()
            self.logger.debug(f"Datos brutos obtenidos: {len(raw_companies_data.get('value',[]))} compañías.")

            if not raw_companies_data or "value" not in raw_companies_data:
                 self.logger.warning("No se recibieron datos válidos de compañías del repositorio.")
                 return {"value": []}

            # 2. Transformación (Domain Service)
            self.logger.debug(f"Aplicando filtro de compañías (excluyendo {len(excluded_ids)} IDs) vía TransformService...")
            filtered_companies_data = self.transform_service.filter_companies(
                companies_data=raw_companies_data,
                excluded_ids=excluded_ids
            )
            # El transform_service ya loguea detalles del filtrado
            self.logger.info(f"Compañías filtradas. Resultado: {len(filtered_companies_data.get('value',[]))} compañías.")

            return filtered_companies_data

        except Exception as e:
             self.logger.error(f"Error en el caso de uso get_companies: {e}", exc_info=True)
             return {"value": []} # Devolver estructura vacía en error

    def get_company_entity_definitions(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON con las entityDefinitions de una compañía concreta.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener EntityDefinitions para Compañía ID: {company_id}")
        try:
            self.logger.debug(f"Llamando a BCRepository.get_entity_definitions para compañía {company_id}...")
            definitions = self.bc_repository.get_entity_definitions(company_id)
            self.logger.info(f"EntityDefinitions obtenidas para {company_id}: {len(definitions.get('value',[]))} definiciones.")
            return definitions
        except Exception as e:
             self.logger.error(f"Error al obtener entity definitions para compañía {company_id}: {e}", exc_info=True)
             return {"value": []}

    def get_company_raw_data(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON que trae /companies({companyId})/.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Datos Raw para Compañía ID: {company_id}")
        try:
            self.logger.debug(f"Llamando a BCRepository.get_company_raw_data para compañía {company_id}...")
            raw_data = self.bc_repository.get_company_raw_data(company_id)
            # Podríamos loguear si se encontró algo o no
            if raw_data:
                 self.logger.info(f"Datos raw obtenidos para {company_id}.")
            else:
                 self.logger.warning(f"No se obtuvieron datos raw para {company_id}.")
            return raw_data if raw_data else {} # Devolver dict vacío si no hay nada
        except Exception as e:
             self.logger.error(f"Error al obtener datos raw para compañía {company_id}: {e}", exc_info=True)
             return {}

    def get_company_projects(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON con los proyectos de una compañía.
        (Podría incluir transformaciones futuras aquí si fuera necesario).
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Proyectos para Compañía ID: {company_id}")
        try:
            self.logger.debug(f"Llamando a BCRepository.get_projects para compañía {company_id}...")
            projects_data = self.bc_repository.get_projects(company_id) # Asume que existe este método en el repo
            self.logger.info(f"Proyectos obtenidos para {company_id}: {len(projects_data.get('value',[]))} registros.")

            # --- Punto Potencial para Transformación de Proyectos ---
            # projects_data = self.transform_service.clean_project_data(projects_data)
            # self.logger.info("Transformación de datos de proyectos aplicada.")
            # --------------------------------------------------------

            return projects_data
        except Exception as e:
            self.logger.error(f"Error en el caso de uso get_company_projects para ID {company_id}: {e}", exc_info=True)
            return {"value": []}

    def get_project_tasks_for_project(self, company_id: str, project_id: str) -> Dict[str, Any]:
        """
        Obtiene jobTasks para un proyecto específico.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Tareas para Proyecto ID: {project_id} (Compañía: {company_id})")
        try:
            self.logger.debug(f"Llamando a BCRepository.get_project_tasks para proyecto {project_id}...")
            tasks_data = self.bc_repository.get_project_tasks(company_id, project_id) # Asume método existe
            self.logger.info(f"Tareas obtenidas para proyecto {project_id}: {len(tasks_data.get('value',[]))} tareas.")
            return tasks_data
        except Exception as e:
             self.logger.error(f"Error al obtener tareas para proyecto {project_id} (compañía {company_id}): {e}", exc_info=True)
             return {"value": []}

    # --- Añadir más casos de uso según sea necesario ---