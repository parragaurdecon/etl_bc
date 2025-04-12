"""
interface_adapters/controllers/pipeline_steps.py

Clases para cada etapa (step) del pipeline ETL, con posibilidad
de imprimir en consola y exportar a CSV opcionalmente.
"""

from typing import Any, Dict, Optional
from application.use_cases.bc_use_cases import BCUseCases
from application.use_cases.csv_export_service import CSVExportService

class ETLStepInterface:
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


# 1) Extraer compañías
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
        """
        :param bc_use_cases: casos de uso para BC
        :param csv_export_service: servicio para exportar CSV (opcional)
        :param print_to_console: si True, se imprimirán los datos en consola
        :param export_to_csv: si True, se generará un CSV con la data
        :param csv_file_path: ruta donde guardar el CSV, si export_to_csv = True
        """
        self.bc_use_cases = bc_use_cases
        self.csv_export_service = csv_export_service
        self.print_to_console = print_to_console
        self.export_to_csv = export_to_csv
        self.csv_file_path = csv_file_path

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        companies_json = self.bc_use_cases.get_companies()
        context["companies_json"] = companies_json

        # 1. Imprimir si corresponde
        if self.print_to_console:
            companies_list = companies_json.get("value", [])
            print("\n[ExtractCompaniesStep] Empresas en BC:")
            for c in companies_list:
                print(f"- {c.get('name')} (ID: {c.get('id')})")

        # 2. Exportar a CSV si corresponde
        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=companies_json,
                file_path=self.csv_file_path,
                array_key="value"  # asumiendo que la data está en companies_json["value"]
            )
            print(f"[ExtractCompaniesStep] CSV generado: {self.csv_file_path}")

        return context


# 2) Extraer datos de una compañía en /companies({companyId})/
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

        # 1. Imprimir
        if self.print_to_console:
            print(f"\n[ExtractCompanyRawDataStep] Datos de la compañía {self.company_id}:")
            print(company_json)

        # 2. Exportar a CSV si corresponde
        if self.export_to_csv and self.csv_export_service:
            self.csv_export_service.export_json_to_csv(
                data_json=company_json,
                file_path=self.csv_file_path,
                array_key=None  # suponer que NO viene en 'value'
            )
            print(f"[ExtractCompanyRawDataStep] CSV generado: {self.csv_file_path}")

        return context


# 3) Extraer definiciones de tablas (entityDefinitions)
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


# 4) Extraer proyectos de una compañía
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


# 5) Extraer tareas de un proyecto
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
