# domain/services/transform_service.py
import logging
from typing import Dict, Any, List, Set
import pandas as pd # Mantener por si se usa en otras transformaciones

# --- Importar la instancia de settings ---
# Ajusta la ruta según tu estructura. Asumiendo que settings.py está en una carpeta 'config'
try:
    from config.settings import settings
except ImportError:
    logging.critical("Error CRÍTICO: No se pudo importar 'settings' desde config.settings.")
    # Crear un objeto Dummy para evitar NameErrors, pero indicar el problema
    class DummySettings:
        EXCLUDED_COMPANY_IDS: Set[str] = set()
        # Añadir otros atributos esperados si es necesario para evitar errores
    settings = DummySettings()
    logging.error("Se utilizará configuración dummy para TransformService debido a fallo de importación.")
# ---------------------------------------


class TransformService:
    """
    Contiene lógica de transformación de datos desacoplada.
    Obtiene la configuración de exclusión desde el objeto 'settings'.
    """
    def __init__(self):
        """Inicializa el servicio y carga la configuración necesaria."""
        self.logger = logging.getLogger(__name__)
        self.excluded_ids: Set[str] = set() # Inicializar como vacío

        # Cargar IDs excluidos desde la instancia settings
        # Es importante que 'settings' ya esté inicializado al crear TransformService
        if settings and hasattr(settings, 'EXCLUDED_COMPANY_IDS') and isinstance(settings.EXCLUDED_COMPANY_IDS, set):
            self.excluded_ids = settings.EXCLUDED_COMPANY_IDS
            self.logger.info(f"TransformService inicializado. Excluyendo {len(self.excluded_ids)} IDs de compañías (leídos desde settings).")
        elif settings:
             self.logger.warning("El atributo 'EXCLUDED_COMPANY_IDS' no es un set válido en 'settings'. No se excluirán compañías por ID.")
        else:
             self.logger.error("La instancia 'settings' no está disponible. No se aplicará filtro de exclusión de compañías.")


    # --- MÉTODO MODIFICADO ---
    def filter_companies(self, companies_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra una lista de compañías (formato OData) usando los IDs excluidos
        obtenidos de la configuración global ('settings').

        :param companies_data: Diccionario con 'value': [lista de compañías].
        :return: Diccionario con 'value': [lista de compañías filtradas].
                 Devuelve {"value": []} si la entrada es inválida o no hay resultados.
        """
        # Ya no recibe excluded_ids como parámetro

        if not companies_data or "value" not in companies_data or not isinstance(companies_data["value"], list):
            self.logger.warning("Formato de datos de compañías inválido o vacío recibido en filter_companies.")
            return {"value": []} # Devolver estructura válida pero vacía

        original_list = companies_data["value"]
        # Usar los IDs cargados durante la inicialización del servicio
        excluded_ids_to_use = self.excluded_ids
        self.logger.debug(f"Filtrando {len(original_list)} compañías. Excluyendo {len(excluded_ids_to_use)} IDs (desde config).")

        # Aplicar el filtro
        filtered_list = [
            comp for comp in original_list
            if comp.get("id") not in excluded_ids_to_use # Comparar con la lista cargada
        ]

        # Loguear el resultado del filtrado
        filtered_count = len(original_list) - len(filtered_list)
        if filtered_count > 0:
            self.logger.info(f"Se filtraron {filtered_count} compañías excluidas.")
        else:
             self.logger.debug("No se encontraron compañías para excluir según la configuración.")

        return {"value": filtered_list}

    # --- Otros métodos de transformación ---
    # (Puedes añadir más aquí, podrían usar 'settings' también si necesitan config)
    # ej: def clean_project_data(self, projects_data: Dict[str, Any]) -> Dict[str, Any]:
    #         threshold = settings.get_yaml_config('project_threshold', 0) # Ejemplo
    #         # ... lógica ...