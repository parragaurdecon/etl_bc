"""
application/use_cases/bc_use_cases.py
Casos de uso para interactuar con Business Central (solo métodos puros).
"""

from domain.repositories.interfaces import BusinessCentralRepositoryInterface
from domain.services.transform_service import TransformService
from typing import Dict, Any

class BCUseCases:
    """
    Clase que orquesta la obtención y la lógica de negocio
    para datos de Business Central, sin incluir acciones de E/S (export a CSV).
    """

    def __init__(self, bc_repository: BusinessCentralRepositoryInterface, transform_service: TransformService):
        self.bc_repository = bc_repository
        self.transform_service = transform_service

    def get_entities(self) -> Dict[str, Any]:
        """
        Devuelve el JSON de entidades disponibles en BC.
        """
        return self.bc_repository.get_entities()

    def get_companies(self) -> Dict[str, Any]:
        """
        Devuelve el JSON de las empresas en BC.
        """
        return self.bc_repository.get_companies()

    def get_company_entity_definitions(self, company_id: str) -> dict:
        """
        Devuelve el JSON con las entityDefinitions de una compañía concreta.
        """
        return self.bc_repository.get_entity_definitions(company_id)

    def get_company_raw_data(self, company_id: str) -> dict:
        """
        Devuelve el JSON que trae /companies({companyId})/.
        """
        return self.bc_repository.get_company_raw_data(company_id)

    def get_company_projects(self, company_id: str) -> dict:
        """
        Devuelve el JSON con los proyectos de una compañía.
        """
        return self.bc_repository.get_projects(company_id)

    def get_project_tasks_for_project(self, company_id: str, project_id: str) -> dict:
        """
        Devuelve jobTasks para un proyecto específico.
        """
        return self.bc_repository.get_project_tasks(company_id, project_id)
