# infrastructure/business_central/bc_repository.py

"""
infrastructure/business_central/bc_repository.py
Implementación del repositorio de Business Central usando BCClient.
"""
from typing import Dict, Any
from domain.repositories.interfaces import BusinessCentralRepositoryInterface
from infrastructure.business_central.bc_client import BCClient

class BCRepository(BusinessCentralRepositoryInterface):
    """
    Implementa las operaciones para obtener datos de Business Central
    a través del BCClient.
    """
    def __init__(self, bc_client: BCClient):
        self.bc_client = bc_client

    def get_companies(self) -> Dict[str, Any]:
        return self.bc_client.fetch_companies()

    def get_entity_definitions(self, company_id: str):
        """
        Llama a bc_client para obtener las tablas (entityDefinitions) de la compañía.
        """
        return self.bc_client.fetch_entity_definitions(company_id)

    def get_projects(self, company_id: str):
        """
        Usa bc_client.fetch_projects() para obtener los proyectos de la compañía dada.
        """
        return self.bc_client.fetch_projects(company_id)

    def get_company_raw_data(self, company_id: str):
        """
        Llama a bc_client.fetch_company_raw_data() para obtener los datos
        de la compañía desde el endpoint directo.
        """
        return self.bc_client.fetch_company_raw_data(company_id)

    def get_project_tasks(self, company_id: str, project_id: str):
        """
        Obtiene las tareas de proyecto (jobTasks) de la compañía indicada.
        """
        return self.bc_client.fetch_project_tasks(company_id, project_id)

    def get_entities(self) -> Dict[str, Any]:
        # Asumiendo que bc_client tiene un fetch_entities():
        return self.bc_client.fetch_entities()


