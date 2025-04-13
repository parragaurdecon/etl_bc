# domain/services/transform_service.py
import logging
from typing import Dict, Any, List, Set
import pandas as pd

class TransformService:
    """
    Contiene lógica de transformación de datos desacoplada.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def filter_companies(self, companies_data: Dict[str, Any], excluded_ids: Set[str]) -> Dict[str, Any]:
        """
        Filtra una lista de compañías (en formato JSON OData) para excluir IDs específicos.

        :param companies_data: Diccionario con la clave 'value' conteniendo una lista de diccionarios de compañías.
        :param excluded_ids: Un set con las IDs de las compañías a excluir.
        :return: Un nuevo diccionario con la misma estructura, pero con la lista 'value' filtrada.
                 Devuelve un diccionario con 'value' vacío si la entrada es inválida o no hay resultados.
        """
        if not companies_data or "value" not in companies_data or not isinstance(companies_data["value"], list):
            self.logger.warning("Formato de datos de compañías inválido o vacío recibido para filtrar.")
            return {"value": []} # Devolver estructura válida pero vacía

        original_list = companies_data["value"]
        self.logger.debug(f"Filtrando {len(original_list)} compañías. Excluyendo IDs: {excluded_ids}")

        filtered_list = [
            comp for comp in original_list
            if comp.get("id") not in excluded_ids
        ]

        filtered_count = len(original_list) - len(filtered_list)
        if filtered_count > 0:
            self.logger.info(f"Se filtraron {filtered_count} compañías excluidas.")
        else:
             self.logger.debug("No se encontraron compañías para excluir según los IDs proporcionados.")

        return {"value": filtered_list}

    # --- Aquí podrías añadir más métodos de transformación en el futuro ---
    # ej: def clean_project_names(self, projects_data: Dict[str, Any]) -> Dict[str, Any]: ...
    # ej: def enrich_company_data(self, companies_data: Dict[str, Any], external_source) -> Dict[str, Any]: ...