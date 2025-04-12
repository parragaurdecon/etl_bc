"""
interface_adapters/controllers/pipeline_extract.py

Clases para cada etapa (step) del pipeline ETL, con posibilidad
de imprimir en consola, exportar a CSV opcionalmente,
y un paso final para almacenar datos en PostgreSQL.
"""

from typing import Any, Dict, Optional, List, Callable
import pandas as pd

from application.use_cases.bc_use_cases import BCUseCases
from application.use_cases.csv_export_service import CSVExportService
from infrastructure.postgresql.pg_repository import PGRepository

class ETLStepInterface:
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

# ----------------------------------------------------------------------
# STEPS DE EXTRACCIÓN
# ----------------------------------------------------------------------

class ExtractCompaniesStep(ETLStepInterface):
    """
    Extrae la lista de empresas desde Business Central y la
    guarda en el context. Opcionalmente, imprime y/o exporta a CSV.
    """
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        csv_export_service: Optional[CSVExportService] = None,
        print_to_console: bool = False,
        export_to_csv: bool = False,
        csv_file_path: str = "companies_export.csv",
    ):
        self.bc_use_cases = bc_use_cases
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        companies_json = self.bc_use_cases.get_companies()
        context["companies_json"] = companies_json

        # 1. Imprimir en consola
        if self.print_to_console:
            companies_list = companies_json.get("value", [])
            print("\n[ExtractCompaniesStep] Empresas en BC:")
            for c in companies_list:
                print(f"- {c.get('name')} (ID: {c.get('id')})")

        # 2. Exportar a CSV
        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=companies_json,
                file_path=self.csv_file_path,
                array_key="value"
            )
            print(f"[ExtractCompaniesStep] CSV generado: {self.csv_file_path}")

        return context

class ExtractCompanyRawDataStep(ETLStepInterface):
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        company_id: str,
        csv_export_service: Optional[CSVExportService] = None,
        print_to_console: bool = False,
        export_to_csv: bool = False,
        csv_file_path: str = "company_raw_data.csv",
    ):
        self.bc_use_cases = bc_use_cases
        self.company_id = company_id
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        company_json = self.bc_use_cases.get_company_raw_data(self.company_id)
        context["company_raw_data"] = company_json

        if self.print_to_console:
            print(f"\n[ExtractCompanyRawDataStep] Datos de la compañía {self.company_id}:")
            print(company_json)

        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=company_json,
                file_path=self.csv_file_path
            )
            print(f"[ExtractCompanyRawDataStep] CSV generado: {self.csv_file_path}")

        return context

class ExtractCompanyTablesStep(ETLStepInterface):
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        company_id: str,
        csv_export_service: Optional[CSVExportService] = None,
        print_to_console: bool = False,
        export_to_csv: bool = False,
        csv_file_path: str = "company_tables.csv",
    ):
        self.bc_use_cases = bc_use_cases
        self.company_id = company_id
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tables_json = self.bc_use_cases.get_company_entity_definitions(self.company_id)
        context["company_tables_json"] = tables_json

        if self.print_to_console:
            tables_list = tables_json.get("value", [])
            print(f"\n[ExtractCompanyTablesStep] Tablas de la compañía {self.company_id}:")
            for table_def in tables_list:
                name = table_def.get("name")
                caption = table_def.get("caption")
                print(f"- {name} (Caption: {caption})")

        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=tables_json,
                file_path=self.csv_file_path,
                array_key="value"
            )
            print(f"[ExtractCompanyTablesStep] CSV generado: {self.csv_file_path}")

        return context

class ExtractProjectsStep(ETLStepInterface):
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        company_id: str,
        csv_export_service: Optional[CSVExportService] = None,
        print_to_console: bool = False,
        export_to_csv: bool = False,
        csv_file_path: str = "projects_data.csv",
    ):
        self.bc_use_cases = bc_use_cases
        self.company_id = company_id
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        projects_json = self.bc_use_cases.get_company_projects(self.company_id)
        context["projects_json"] = projects_json

        if self.print_to_console:
            projects_list = projects_json.get("value", [])
            print(f"\n[ExtractProjectsStep] Proyectos de la compañía {self.company_id}:")
            for proj in projects_list:
                name = proj.get("name")
                pid = proj.get("id")
                print(f"- {name} (ID: {pid})")

        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=projects_json,
                file_path=self.csv_file_path,
                array_key="value"
            )
            print(f"[ExtractProjectsStep] CSV generado: {self.csv_file_path}")

        return context

class ExtractProjectTasksStep(ETLStepInterface):
    def __init__(
        self,
        bc_use_cases: BCUseCases,
        company_id: str,
        project_id: str,
        csv_export_service: Optional[CSVExportService] = None,
        print_to_console: bool = False,
        export_to_csv: bool = False,
        csv_file_path: str = "project_tasks_data.csv",
    ):
        self.bc_use_cases = bc_use_cases
        self.company_id = company_id
        self.project_id = project_id
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        tasks_json = self.bc_use_cases.get_project_tasks_for_project(
            self.company_id,
            self.project_id
        )
        context["project_tasks_json"] = tasks_json

        if self.print_to_console:
            tasks_list = tasks_json.get("value", [])
            print(f"\n[ExtractProjectTasksStep] Tareas del proyecto {self.project_id}:")
            for t in tasks_list:
                print(f"- {t.get('id')} : {t.get('description')}")

        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=tasks_json,
                file_path=self.csv_file_path,
                array_key="value"
            )
            print(f"[ExtractProjectTasksStep] CSV generado: {self.csv_file_path}")

        return context


class ExtractMultiCompanyStep(ETLStepInterface):
    """
    Step que obtiene la lista de compañías del context (por ejemplo "companies_json"),
    luego para cada compañía, llama a la función de extracción (extract_func)
    y concatena los resultados en un único DataFrame.

    No incluye logging; imprime en consola si así se desea.
    """

    def __init__(
        self,
        companies_context_key: str,
        extract_func: Callable[[str], Dict[str, Any]],
        out_context_key: str,
        company_col: str = "CompanyId",
        print_to_console: bool = False,
    ):
        """
        :param companies_context_key: clave en el context donde está el JSON de compañías
                                      (ej: "companies_json"), que contiene "value": [{id, name...}, ...]
        :param extract_func: función/callable que, dado un company_id, devuelva un JSON con "value"
        :param out_context_key: clave donde guardar el DataFrame resultante en forma JSON {"value": ...}
        :param company_col: nombre de la columna que indica la compañía
        :param print_to_console: si True, imprime mensajes en pantalla
        """
        self.companies_context_key = companies_context_key
        self.extract_func = extract_func
        self.out_context_key = out_context_key
        self.company_col = company_col
        self.print_to_console = print_to_console

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Obtener lista de compañías desde el context
        companies_json = context.get(self.companies_context_key, {})
        companies_list = companies_json.get("value", [])
        if not companies_list:
            if self.print_to_console:
                print(f"No hay compañías en '{self.companies_context_key}' o la lista está vacía.")
            # Guardar un valor vacío para el out_context_key
            context[self.out_context_key] = {"value": []}
            return context

        # 2. Iterar sobre cada compañía y extraer datos
        all_data_df = pd.DataFrame()

        for comp in companies_list:
            c_id = comp.get("id")
            if not c_id:
                continue

            entity_json = self.extract_func(c_id)
            items = entity_json.get("value", [])
            if not items:
                if self.print_to_console:
                    print(f"No hay datos para la compañía {c_id}.")
                continue

            df = pd.DataFrame(items)
            df[self.company_col] = c_id

            all_data_df = pd.concat([all_data_df, df], ignore_index=True)

            if self.print_to_console:
                print(f"Extraídos {len(df)} registros para la compañía '{c_id}'.")

        # 3. Guardar en el context como JSON {"value": ...}
        if all_data_df.empty:
            context[self.out_context_key] = {"value": []}
            if self.print_to_console:
                print("No se obtuvieron datos de ninguna compañía.")
        else:
            all_dicts = all_data_df.to_dict(orient="records")
            context[self.out_context_key] = {"value": all_dicts}
            if self.print_to_console:
                print(f"Concatenado un total de {len(all_data_df)} registros para {len(companies_list)} compañías.")

        return context


