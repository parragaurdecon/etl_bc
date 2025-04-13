"""
domain/repositories/interfaces.py
Define la interfaz para interactuar con Business Central,
con solo los métodos que realmente uses en BCUseCases.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any

class BusinessCentralRepositoryInterface(ABC):
    """
    Contrato para obtener datos de Business Central.
    """

    @abstractmethod
    def get_entities(self) -> Dict[str, Any]:
        """
        Devuelve la lista de entidades disponibles en BC.
        """
        pass

    @abstractmethod
    def get_companies(self) -> Dict[str, Any]:
        """
        Devuelve las compañías disponibles en BC.
        """
        pass

    @abstractmethod
    def get_entity_definitions(self, company_id: str) -> Dict[str, Any]:
        """
        Devuelve las entityDefinitions para la compañía especificada.
        """
        pass

    @abstractmethod
    def get_company_raw_data(self, company_id: str) -> Dict[str, Any]:
        """
        Devuelve un JSON crudo con información de la compañía (endpoint /companies({company_id})/).
        """
        pass

    @abstractmethod
    def get_projects(self, company_id: str) -> Dict[str, Any]:
        """
        Devuelve los proyectos para la compañía especificada.
        """
        pass

    @abstractmethod
    def get_project_tasks(self, company_id: str, project_id: str) -> Dict[str, Any]:
        """
        Devuelve las tareas (jobTasks) de un proyecto en la compañía especificada.
        """
        pass

    @abstractmethod
    def get_customers(self, company_id: str) -> Dict[str, Any]:
        pass
