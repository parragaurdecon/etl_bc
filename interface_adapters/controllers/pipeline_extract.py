"""
interface_adapters/controllers/pipeline_extract.py

Clases para etapas de extracción del pipeline ETL, con logging,
manejo de excepciones y lógica de transformación delegada a capas inferiores.
"""

import logging
from typing import Any, Dict, Optional, List, Callable, Set
import pandas as pd

# --- Importar la Interfaz Base ---
# Ajusta la ruta si es necesario
try:
    from interface_adapters.controllers.etl_controller import ETLStepInterface
except ImportError:
    logging.critical("Error crítico: No se pudo importar ETLStepInterface desde etl_controller.")
    # Definir un placeholder para evitar errores de carga, pero indicando el problema
    class ETLStepInterface:
        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            logging.error("ETLStepInterface no fue importada correctamente!")
            raise NotImplementedError("Interfaz base no cargada")

# --- Importar Dependencias de Aplicación/Infraestructura ---
# Asegúrate de que estas rutas sean correctas
try:
    from application.use_cases.bc_use_cases import BCUseCases
    from application.use_cases.csv_export_service import CSVExportService
except ImportError as e:
    logging.error(f"Error importando dependencias de aplicación/infraestructura: {e}")
    # Podrías lanzar un error aquí o permitir que falle más tarde
    BCUseCases = None # Placeholder
    CSVExportService = None # Placeholder


# --- Clase ExtractCompaniesStep (Simplificada) ---
class ExtractCompaniesStep(ETLStepInterface):
    """
    Extrae la lista de empresas YA FILTRADAS desde BCUseCases y la
    guarda en el context. Opcionalmente exporta a CSV.
    """
    def __init__(
        self,
        bc_use_cases: BCUseCases, # Sigue necesitando el caso de uso
        csv_export_service: Optional[CSVExportService] = None,
        export_to_csv: bool = False,
        csv_file_path: str = "companies_filtered_export.csv", # Nombre refleja filtro
        context_key: str = "companies_json" # Clave para el contexto
    ):
        if BCUseCases is None: # Comprobar si la importación falló
             raise ImportError("Dependencia BCUseCases no cargada correctamente.")
        self.bc_use_cases = bc_use_cases
        self.csv_export_service = csv_export_service
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path
        self.context_key = context_key
        self.logger = logging.getLogger(__name__) # Logger específico

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Extracción de Compañías (Filtradas) ---")
        # Asegurar que la clave de salida exista, incluso si falla
        context[self.context_key] = {"value": []}
        try:
            # 1. Llamar al caso de uso (que ya filtra internamente)
            self.logger.info("Llamando a BCUseCases.get_companies (que incluye filtrado)...")
            # El caso de uso ahora maneja los IDs excluidos internamente o por defecto
            companies_json_filtered = self.bc_use_cases.get_companies()

            companies_list = companies_json_filtered.get("value", [])
            self.logger.info(f"Recibidas {len(companies_list)} compañías filtradas del caso de uso.")

            # 2. Guardar en el context (sobrescribir si ya existía)
            context[self.context_key] = companies_json_filtered
            self.logger.debug(f"Datos de compañías filtradas guardados en context['{self.context_key}']")

            # 3. Exportar a CSV (opcional)
            if self.export_to_csv and self.csv_export_service:
                if companies_list: # Solo exportar si hay datos
                    self.logger.info(f"Exportando {len(companies_list)} compañías filtradas a CSV: {self.csv_file_path}")
                    try:
                        self.csv_export_service.export_json_to_csv(
                            data_json=companies_json_filtered, # Usar datos filtrados
                            file_path=self.csv_file_path,
                            array_key="value"
                        )
                        self.logger.info(f"Exportación a CSV completada: {self.csv_file_path}")
                    except Exception as csv_err:
                        self.logger.error(f"Error durante la exportación a CSV de compañías: {csv_err}", exc_info=True)
                        # No relanzar para no detener el pipeline solo por el CSV
                else:
                    self.logger.info("No hay compañías filtradas para exportar a CSV.")

        except Exception as e:
            self.logger.error(f"Error fatal durante la extracción de compañías filtradas: {e}", exc_info=True)
            # Relanzar para detener el pipeline si la extracción principal falla
            raise RuntimeError(f"Fallo en {self.__class__.__name__}") from e
        finally:
            self.logger.info(f"--- Step Finalizado: Extracción de Compañías (Filtradas) ---")

        return context


# --- Clase ExtractProjectsStep (Mejorada con Logging) ---
class ExtractProjectsStep(ETLStepInterface):
    """
    Extrae proyectos para UNA compañía específica.
    (Actualmente no usado en el main.py proporcionado, pero mejorado).
    """
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        company_id: str, # ID de la compañía a procesar
        csv_export_service: Optional[CSVExportService] = None,
        export_to_csv: bool = False,
        csv_file_path: str = "projects_data.csv",
        context_key: str = "projects_json" # Clave donde guardar/sobrescribir
    ):
        if BCUseCases is None: raise ImportError("Dependencia BCUseCases no cargada.")
        self.bc_use_cases = bc_use_cases
        self.company_id = company_id
        self.csv_export_service = csv_export_service
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path
        self.context_key = context_key
        self.logger = logging.getLogger(__name__)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Extracción de Proyectos (Compañía ID: {self.company_id}) ---")
        # Asegurar clave de salida vacía por defecto
        context[self.context_key] = {"value": []}
        try:
            self.logger.info(f"Llamando a BCUseCases.get_company_projects para '{self.company_id}'...")
            projects_json = self.bc_use_cases.get_company_projects(self.company_id) # El caso de uso maneja errores internos
            projects_list = projects_json.get("value", [])
            self.logger.info(f"Recibidos {len(projects_list)} proyectos para '{self.company_id}'.")

            # Guardar en el contexto
            context[self.context_key] = projects_json
            self.logger.debug(f"Datos de proyectos guardados en context['{self.context_key}']")

            # Exportar a CSV (opcional)
            if self.export_to_csv and self.csv_export_service:
                 if projects_list:
                    self.logger.info(f"Exportando {len(projects_list)} proyectos a CSV: {self.csv_file_path}")
                    try:
                        self.csv_export_service.export_json_to_csv(
                            data_json=projects_json,
                            file_path=self.csv_file_path,
                            array_key="value"
                        )
                        self.logger.info(f"Exportación a CSV de proyectos completada.")
                    except Exception as csv_err:
                         self.logger.error(f"Error exportando proyectos a CSV: {csv_err}", exc_info=True)
                 else:
                      self.logger.info("No hay proyectos para exportar a CSV.")

        except Exception as e:
            # Captura errores si el propio bc_use_cases falla inesperadamente
            self.logger.error(f"Error fatal extrayendo proyectos para '{self.company_id}': {e}", exc_info=True)
            raise RuntimeError(f"Fallo en {self.__class__.__name__} para compañía {self.company_id}") from e
        finally:
            self.logger.info(f"--- Step Finalizado: Extracción de Proyectos ({self.company_id}) ---")
        return context


# --- Clase ExtractMultiCompanyStep (Mejorada con Logging) ---
class ExtractMultiCompanyStep(ETLStepInterface):
    """
    Obtiene compañías del contexto (ya filtradas), itera sobre ellas,
    llama a extract_func para cada una, y concatena los resultados
    en un DataFrame JSON en el contexto.
    """
    def __init__(
        self,
        companies_context_key: str, # Clave donde están las compañías FILTRADAS
        extract_func: Callable[[str], Dict[str, Any]], # Función a llamar por compañía (ej: bc_use_cases.get_company_projects)
        out_context_key: str, # Clave para guardar resultado JSON {"value": [...]}
        company_col: str = "CompanyId", # Nombre de columna para añadir ID de compañía
    ):
        self.companies_context_key = companies_context_key
        self.extract_func = extract_func
        self.out_context_key = out_context_key
        self.company_col = company_col
        self.logger = logging.getLogger(__name__)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Extracción Multi-Compañía ({self.out_context_key}) ---")
        all_data_list = []
        processed_companies = 0
        failed_companies = 0
        total_records = 0

        # Asegurar salida vacía por defecto
        context[self.out_context_key] = {"value": []}

        # Obtener lista de compañías (ya filtradas)
        companies_json = context.get(self.companies_context_key, {})
        companies_list = companies_json.get("value", [])
        total_companies_to_process = len(companies_list)

        if not companies_list:
            self.logger.warning(f"No hay compañías en el context_key '{self.companies_context_key}' para procesar. Saltando step.")
            self.logger.info(f"--- Step Finalizado: Extracción Multi-Compañía - Sin Compañías ---")
            return context

        self.logger.info(f"Procesando {total_companies_to_process} compañías (ya filtradas) desde '{self.companies_context_key}'...")

        # Iterar y extraer
        for i, comp in enumerate(companies_list):
            c_id = comp.get("id")
            c_name = comp.get("name", "ID Desconocido")
            if not c_id:
                self.logger.warning(f"Ítem {i+1}/{total_companies_to_process} en lista de compañías sin 'id'. Omitiendo.")
                failed_companies += 1 # Contar como fallo si no tiene ID
                continue

            self.logger.debug(f"Procesando compañía {i+1}/{total_companies_to_process}: {c_name} (ID: {c_id})")
            try:
                # Llamar a la función de extracción (ej: get_company_projects)
                # El caso de uso ya maneja sus propios errores y devuelve {"value": []} si falla
                entity_json = self.extract_func(c_id)
                items = entity_json.get("value", [])

                if items:
                    self.logger.info(f"Extraídos {len(items)} registros para compañía '{c_name}' ({c_id}).")
                    # Añadir CompanyId a cada registro y añadir a la lista general
                    for item in items:
                        item[self.company_col] = c_id # Añadir/sobrescribir ID de compañía
                        all_data_list.append(item)
                        total_records += 1
                else:
                    # No es necesariamente un error, puede que la compañía no tenga esos datos
                    self.logger.info(f"No se encontraron registros para compañía '{c_name}' ({c_id}).")

                processed_companies += 1 # Contar como procesada si la llamada no lanzó excepción

            except Exception as e:
                # Capturar error si la propia llamada a extract_func falla catastróficamente
                self.logger.error(f"Error irrecuperable extrayendo datos para compañía '{c_name}' ({c_id}): {e}", exc_info=True)
                failed_companies += 1
                # Continuar con la siguiente compañía

        # Guardar resultado final en el contexto
        context[self.out_context_key] = {"value": all_data_list}
        self.logger.info(f"Extracción Multi-Compañía completada. Total registros concatenados: {total_records}.")
        self.logger.info(f"Resumen: Compañías procesadas={processed_companies}, Fallidas/Omitidas={failed_companies}, Total inicial={total_companies_to_process}.")
        self.logger.info(f"--- Step Finalizado: Extracción Multi-Compañía ({self.out_context_key}) ---")
        return context