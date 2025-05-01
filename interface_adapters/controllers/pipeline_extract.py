# interface_adapters/controllers/pipeline_extract.py

"""
interface_adapters/controllers/pipeline_extract.py
Clases para etapas de extracción del pipeline ETL, con logging,
manejo de excepciones y lógica de transformación delegada.
ExtractMultiCompanyStep adaptado para usar 'id' o 'name' y pasar contexto.
"""

import logging
from typing import Any, Dict, Optional, List, Callable
import pandas as pd

# --- Importar la Interfaz Base ---
try:
    from .etl_controller import ETLStepInterface
except ImportError:
    logging.critical("Error crítico: No se pudo importar ETLStepInterface desde .etl_controller.")
    class ETLStepInterface:
        def run(self, context: Dict[str, Any]) -> Dict[str, Any]: raise NotImplementedError
# ---------------------------------------------------

# --- Importar Dependencias ---
try:
    from application.use_cases.bc_use_cases import BCUseCases
    from application.use_cases.csv_export_service import CSVExportService
except ImportError as e:
    logging.error(f"Error importando dependencias: {e}")
    BCUseCases = CSVExportService = None
# ---------------------------------------------------


# --- Clase ExtractCompaniesStep ---
class ExtractCompaniesStep(ETLStepInterface):
    """Extrae compañías filtradas y opcionalmente exporta a CSV."""
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        csv_export_service: Optional[CSVExportService] = None,
        export_to_csv: bool = False,
        csv_file_path: str = "companies_filtered_export.csv",
        context_key: str = "companies_json"
    ):
        if BCUseCases is None: raise ImportError("Dependencia BCUseCases no cargada.")
        self.bc_use_cases = bc_use_cases
        self.csv_export_service = csv_export_service
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path
        self.context_key = context_key
        self.logger = logging.getLogger(__name__)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Extracción de Compañías (Filtradas) ---")
        context[self.context_key] = {"value": []} # Inicializar
        try:
            self.logger.info("Llamando a BCUseCases.get_companies...")
            companies_json_filtered = self.bc_use_cases.get_companies()
            companies_list = companies_json_filtered.get("value", [])
            self.logger.info(f"Recibidas {len(companies_list)} compañías filtradas.")
            context[self.context_key] = companies_json_filtered

            if self.export_to_csv and self.csv_export_service:
                if companies_list:
                    self.logger.info(f"Exportando {len(companies_list)} compañías a CSV: {self.csv_file_path}")
                    try:
                        self.csv_export_service.export_json_to_csv(data_json=companies_json_filtered, file_path=self.csv_file_path, array_key="value")
                        self.logger.info(f"Exportación CSV completa: {self.csv_file_path}")
                    except Exception as csv_err: self.logger.error(f"Error exportando CSV: {csv_err}", exc_info=True)
                else: self.logger.info("No hay compañías para exportar.")
        except Exception as e:
            self.logger.error(f"Error fatal en extracción de compañías: {e}", exc_info=True)
            raise RuntimeError(f"Fallo en {self.__class__.__name__}") from e
        finally:
            self.logger.info(f"--- Step Finalizado: Extracción de Compañías (Filtradas) ---")
        return context


# --- Clase ExtractMultiCompanyStep (SIMPLIFICADA - Asume firma única en UC) ---
class ExtractMultiCompanyStep(ETLStepInterface):
    """
    Obtiene compañías del contexto, itera, llama a extract_func para cada una
    (pasando identificador Y contexto), y concatena resultados.
    Asume que todas las funciones en BCUseCases aceptan (identificador, contexto).
    """
    def __init__(
        self,
        companies_context_key: str,
        # La función ahora SIEMPRE debe aceptar (str, Dict)
        extract_func: Callable[[str, Dict[str, Any]], Dict[str, Any]],
        out_context_key: str,
        company_col: str = "CompanyId",
        # Ya no es necesario identifier_key si UC acepta ID y busca nombre
        # Pasaremos siempre el ID al caso de uso
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
        context[self.out_context_key] = {"value": []} # Inicializar

        companies_json = context.get(self.companies_context_key, {})
        companies_list = companies_json.get("value", [])
        total_companies_to_process = len(companies_list)

        if not companies_list:
            self.logger.warning(f"No hay compañías en '{self.companies_context_key}'. Saltando step.")
            self.logger.info(f"--- Step Finalizado: {self.__class__.__name__} - Sin Compañías ---")
            return context

        self.logger.info(f"Procesando {total_companies_to_process} compañías desde '{self.companies_context_key}'...")

        for i, comp_dict in enumerate(companies_list):
            company_id = comp_dict.get("id") # Siempre usar ID para pasar al caso de uso
            company_name_for_log = comp_dict.get("name", f"ID:{company_id}")

            if not company_id:
                self.logger.warning(f"Ítem {i+1}/{total_companies_to_process} sin 'id'. Omitiendo.")
                failed_companies += 1
                continue

            self.logger.debug(f"Procesando {i+1}/{total_companies_to_process}: '{company_name_for_log}' (ID: {company_id})")
            try:
                # --- LLAMADA ÚNICA Y DIRECTA ---
                # Pasamos ID y contexto a la función del caso de uso
                entity_json = self.extract_func(company_id, context)
                # -------------------------------
                items = entity_json.get("value", [])
                if items:
                    self.logger.info(f"Extraídos {len(items)} registros para '{company_name_for_log}'.")
                    for item in items:
                         item[self.company_col] = company_id # Usar el ID real
                         all_data_list.append(item)
                         total_records += 1
                else:
                     # El caso de uso ya loguea si no pudo obtener nombre, aquí solo indicamos 0 registros
                     self.logger.info(f"No se encontraron/obtuvieron registros para '{company_name_for_log}'.")
                processed_companies += 1

            except Exception as e:
                # Capturar error si la propia llamada a extract_func falla
                self.logger.error(f"Error irrecuperable extrayendo datos para '{company_name_for_log}': {e}", exc_info=True)
                failed_companies += 1

        context[self.out_context_key] = {"value": all_data_list}
        self.logger.info(f"Extracción Multi-Compañía ({self.out_context_key}) completada. Total registros: {total_records}.")
        self.logger.info(f"Resumen: Procesadas={processed_companies}, Fallidas/Omitidas={failed_companies}, Total={total_companies_to_process}.")
        self.logger.info(f"--- Step Finalizado: {self.__class__.__name__} ({self.out_context_key}) ---")
        return context

# NOTA: La clase ExtractProjectsStep (si la tenías definida) se puede eliminar si ya no se usa,
# o mantenerla si tiene un propósito específico fuera de ExtractMultiCompanyStep.