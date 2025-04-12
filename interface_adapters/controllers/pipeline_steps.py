"""
interface_adapters/controllers/pipeline_steps.py

Clases para cada etapa (step) del pipeline ETL, con posibilidad
de imprimir en consola, exportar a CSV opcionalmente,
y un paso final para almacenar datos en PostgreSQL.
"""

from typing import Any, Dict, Optional
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


# ----------------------------------------------------------------------
# STEP PARA ALMACENAR DATOS EN POSTGRES
# ----------------------------------------------------------------------

class StoreDataInPostgresStep(ETLStepInterface):
    """
    Paso que toma datos (JSON o DataFrame) del context y los
    inserta en una tabla PostgreSQL usando PGRepository.

    Acciones:
    1) Verificar/crear la BD si no existe
    2) Verificar/crear la tabla si no existe
    3) Insertar los datos
    """

    def __init__(
            self,
            pg_repository: PGRepository,
            context_key: str,
            table_name: str,
            convert_json_to_df: bool = True,
            if_exists: str = "append"
    ):
        """
        :param pg_repository: instancia de PGRepository
        :param context_key: clave del context donde están los datos
        :param table_name: nombre de la tabla en PostgreSQL
        :param convert_json_to_df: si True, data es JSON y se convierte a DF;
                                   si False, asumimos data es DataFrame
        :param if_exists: "append", "replace", "fail"
        """
        self.pg_repository = pg_repository
        self.context_key = context_key
        self.table_name = table_name
        self.convert_json_to_df = convert_json_to_df
        self.if_exists = if_exists

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Verificar si hay data en el context
        data = context.get(self.context_key)
        if data is None:
            print(f"[StoreDataInPostgresStep] No hay datos en '{self.context_key}'.")
            return context

        # 2. Convertir a DataFrame si es JSON
        if self.convert_json_to_df:
            if isinstance(data, dict) and "value" in data:
                df = pd.DataFrame(data["value"])
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)
        else:
            # asumimos data ya es DataFrame
            df = data

        if df.empty:
            print(f"[StoreDataInPostgresStep] DataFrame vacío, no guardamos en '{self.table_name}'.")
            return context

        # 3. Verificar / crear la BD si no existe
        self.pg_repository.create_database_if_not_exists()

        # 4. Verificar si la tabla existe; si no, crearla a partir del schema de df
        if not self.pg_repository.table_exists(self.table_name):
            # Crear la tabla con 0 filas (para el schema). Podrías usar df.head(0).
            print(f"[StoreDataInPostgresStep] La tabla '{self.table_name}' no existe. Creándola...")
            self.pg_repository.create_table_from_df(self.table_name, df.head(0))

        # 5. Insertar datos en la tabla
        # Usa if_exists según tu preferencia ("append", "replace", o "fail").
        self.pg_repository.insert_table(self.table_name, df, if_exists=self.if_exists)

        return context


class CheckPostgresConnectionStep(ETLStepInterface):
    """
    Step que simplemente verifica la conexión a PostgreSQL.
    """

    def __init__(self, pg_repository: PGRepository):
        self.pg_repository = pg_repository

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        print("[CheckPostgresConnectionStep] Verificando conexión a PostgreSQL...")
        self.pg_repository.check_connection()
        print("[CheckPostgresConnectionStep] Conexión verificada con éxito.")
        return context

