"""
application/use_cases/bc_use_cases.py
Casos de uso para interactuar con Business Central, incluyendo transformaciones básicas.
"""
import logging
from typing import Dict, Any, Set # Set ya no es necesario para get_companies

# Asumiendo que las interfaces/clases están correctamente ubicadas para la importación
try:
    from domain.repositories.interfaces import BusinessCentralRepositoryInterface
    from domain.services.transform_service import TransformService
except ImportError as e:
     logging.critical(f"Error importando dependencias de dominio/repositorio: {e}")
     # Definir placeholders para evitar errores de carga inmediatos
     BusinessCentralRepositoryInterface = None
     TransformService = None

# Ya NO necesitamos DEFAULT_EXCLUDED_COMPANY_IDS aquí

class BCUseCases:
    """
    Clase que orquesta la obtención y la lógica de negocio (incluyendo transformaciones)
    para datos de Business Central. Las transformaciones específicas (como filtros)
    se delegan a TransformService, que a su vez puede usar configuración externa.
    """

    def __init__(self, bc_repository: BusinessCentralRepositoryInterface, transform_service: TransformService):
        """
        Inicializa los casos de uso con las dependencias necesarias.

        :param bc_repository: Repositorio para acceder a los datos de BC.
        :param transform_service: Servicio para aplicar transformaciones a los datos.
        """
        # Validar dependencias importadas
        if BusinessCentralRepositoryInterface is None or TransformService is None:
            raise ImportError("Dependencias de dominio (Repositorio/Servicio) no cargadas correctamente.")
        if not isinstance(bc_repository, BusinessCentralRepositoryInterface):
             raise TypeError("bc_repository debe implementar BusinessCentralRepositoryInterface.")
        if not isinstance(transform_service, TransformService):
             raise TypeError("transform_service debe ser una instancia de TransformService.")

        self.bc_repository = bc_repository
        self.transform_service = transform_service
        self.logger = logging.getLogger(__name__) # Logger específico

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

    # --- MÉTODO SIMPLIFICADO ---
    def get_companies(self) -> Dict[str, Any]:
        """
        Obtiene las compañías del repositorio y aplica el filtrado configurado
        a través del TransformService.

        :return: Diccionario JSON con la lista de compañías filtradas.
                 Devuelve {"value": []} en caso de error.
        """
        # Ya no necesita el parámetro excluded_ids
        self.logger.info("Iniciando caso de uso: Obtener Compañías (con filtro de config aplicado por TransformService).")
        try:
            # 1. Extracción
            self.logger.debug("Llamando a BCRepository.get_companies...")
            raw_companies_data = self.bc_repository.get_companies()
            self.logger.debug(f"Datos brutos obtenidos: {len(raw_companies_data.get('value',[]))} compañías.")

            if not raw_companies_data or "value" not in raw_companies_data:
                 self.logger.warning("No se recibieron datos válidos de compañías del repositorio.")
                 return {"value": []}

            # 2. Transformación (Delegada al servicio)
            self.logger.debug("Aplicando filtro de compañías vía TransformService...")
            # Simplemente llamamos al método del servicio; él ya sabe qué excluir
            filtered_companies_data = self.transform_service.filter_companies(raw_companies_data)
            # El transform_service debería loguear los detalles del filtrado
            self.logger.info(f"Compañías filtradas por TransformService. Resultado: {len(filtered_companies_data.get('value',[]))} compañías.")

            return filtered_companies_data

        except Exception as e:
             self.logger.error(f"Error en el caso de uso get_companies: {e}", exc_info=True)
             return {"value": []}

    def get_company_entity_definitions(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON con las entityDefinitions de una compañía concreta.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener EntityDefinitions para Compañía ID: {company_id}")
        try:
            # Validar company_id (simple)
            if not company_id or not isinstance(company_id, str):
                 self.logger.error("company_id inválido proporcionado para get_company_entity_definitions.")
                 return {"value": []}
            self.logger.debug(f"Llamando a BCRepository.get_entity_definitions para '{company_id}'...")
            definitions = self.bc_repository.get_entity_definitions(company_id)
            self.logger.info(f"EntityDefinitions obtenidas para '{company_id}': {len(definitions.get('value',[]))} definiciones.")
            return definitions
        except Exception as e:
             self.logger.error(f"Error al obtener entity definitions para compañía '{company_id}': {e}", exc_info=True)
             return {"value": []}

    def get_company_raw_data(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON que trae /companies({companyId})/.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Datos Raw para Compañía ID: {company_id}")
        try:
            if not company_id or not isinstance(company_id, str):
                 self.logger.error("company_id inválido proporcionado para get_company_raw_data.")
                 return {}
            self.logger.debug(f"Llamando a BCRepository.get_company_raw_data para '{company_id}'...")
            raw_data = self.bc_repository.get_company_raw_data(company_id)
            if raw_data: self.logger.info(f"Datos raw obtenidos para '{company_id}'.")
            else: self.logger.warning(f"No se obtuvieron datos raw para '{company_id}'.")
            return raw_data if raw_data else {}
        except Exception as e:
             self.logger.error(f"Error al obtener datos raw para compañía '{company_id}': {e}", exc_info=True)
             return {}

    def get_company_projects(self, company_id: str) -> Dict[str, Any]:
        """
        Obtiene el JSON con los proyectos de una compañía.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Proyectos para Compañía ID: {company_id}")
        try:
            if not company_id or not isinstance(company_id, str):
                 self.logger.error("company_id inválido proporcionado para get_company_projects.")
                 return {"value": []}
            self.logger.debug(f"Llamando a BCRepository.get_projects para '{company_id}'...")
            projects_data = self.bc_repository.get_projects(company_id)
            self.logger.info(f"Proyectos obtenidos para '{company_id}': {len(projects_data.get('value',[]))} registros.")
            # Aquí se podrían aplicar transformaciones específicas de proyectos si fuera necesario
            # projects_data = self.transform_service.clean_project_names(projects_data)
            return projects_data
        except Exception as e:
            self.logger.error(f"Error en caso de uso get_company_projects para ID '{company_id}': {e}", exc_info=True)
            return {"value": []}

    def get_project_tasks_for_project(self, company_id: str, project_id: str) -> Dict[str, Any]:
        """
        Obtiene jobTasks para un proyecto específico.
        """
        self.logger.info(f"Iniciando caso de uso: Obtener Tareas para Proyecto ID: {project_id} (Compañía: {company_id})")
        try:
            if not company_id or not project_id or not isinstance(company_id, str) or not isinstance(project_id, str):
                 self.logger.error("IDs inválidos proporcionados para get_project_tasks_for_project.")
                 return {"value": []}
            self.logger.debug(f"Llamando a BCRepository.get_project_tasks para proyecto '{project_id}'...")
            tasks_data = self.bc_repository.get_project_tasks(company_id, project_id)
            self.logger.info(f"Tareas obtenidas para proyecto '{project_id}': {len(tasks_data.get('value',[]))} tareas.")
            return tasks_data
        except Exception as e:
             self.logger.error(f"Error al obtener tareas para proyecto '{project_id}' (compañía '{company_id}'): {e}", exc_info=True)
             return {"value": []}

    # --- Añadir más casos de uso ---