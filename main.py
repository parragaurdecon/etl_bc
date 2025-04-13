"""
main.py
Punto de entrada de la aplicación.
Configura el pipeline: primero extraemos datos de BC,
luego almacenamos esos datos en PostgreSQL evitando duplicados según PK='id'.
"""

import logging # Importar logging
import sys # Para dirigir logs a stdout

from infrastructure.business_central.bc_client import BCClient
from infrastructure.business_central.bc_repository import BCRepository
from infrastructure.postgresql.pg_client import SqlAlchemyClient
from infrastructure.postgresql.pg_repository import PGRepository

from domain.services.transform_service import TransformService
from application.use_cases.bc_use_cases import BCUseCases
from application.use_cases.csv_export_service import CSVExportService

from interface_adapters.controllers.etl_controller import ETLController
from interface_adapters.controllers.pipeline_extract import (
    ExtractCompaniesStep,
    ExtractMultiCompanyStep,
)
from interface_adapters.controllers.pipeline_store import (
    CheckPostgresConnectionStep,
    StoreDataInPostgresStep
)

# --- CONFIGURACIÓN DE LOGGING ---
# Configurar al principio del script
logging.basicConfig(
    level=logging.INFO,  # Nivel mínimo a mostrar (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s', # Formato del mensaje
    datefmt='%Y-%m-%d %H:%M:%S', # Formato de la fecha/hora
    stream=sys.stdout # Dirigir la salida a la consola estándar (por defecto es stderr)
    # Opcional: Para escribir a un archivo también o en lugar de la consola:
    # filename='etl_pipeline.log',
    # filemode='a' # 'a' para añadir, 'w' para sobrescribir
)

# Obtener un logger para el propio main (opcional)
logger = logging.getLogger(__name__)
# -----------------------------

def main():
    # 1. Infraestructura de Business Central
    bc_client = BCClient()
    bc_repository = BCRepository(bc_client)

    # 2. Servicios de dominio / aplicación
    transform_service = TransformService()
    bc_use_cases = BCUseCases(bc_repository, transform_service)
    csv_exporter = CSVExportService()

    # 3. Infraestructura Postgres via SQLAlchemy
    sa_client = SqlAlchemyClient()
    pg_repository = PGRepository(sa_client)

    # 4. Steps de extracción de datos
    step_extract_companies = ExtractCompaniesStep(
        bc_use_cases=bc_use_cases,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=True,
        csv_file_path="companies_export.csv"
    )

    step_extract_multi_projects = ExtractMultiCompanyStep(
        companies_context_key="companies_json",
        extract_func=bc_use_cases.get_company_projects,
        out_context_key="projects_json",
        company_col="CompanyId",
        print_to_console=True
    )

    # 5. Step para verificar conexión a PostgreSQL
    check_pg_step = CheckPostgresConnectionStep(pg_repository)

    # 6. Steps para almacenar compañías y proyectos en la DB de manera incremental
    #    con PK='id' por defecto en la data de BC (se asume que cada objeto tiene un campo "id").
    store_companies_step = StoreDataInPostgresStep(
        pg_repository=pg_repository,
        context_key="companies_json",
        table_name="companies_bc",
        convert_json_to_df=True,
        # if_exists="append",
        primary_key="id"   # <- Así evitamos duplicados segun la PK "id"
    )
    store_projects_step = StoreDataInPostgresStep(
        pg_repository=pg_repository,
        context_key="projects_json",
        table_name="projects_bc",
        convert_json_to_df=True,
        # if_exists="append",
        primary_key="id"   # <- Carga incremental con PK "id"
    )

    # 7. Definir la secuencia de steps
    steps = [
        step_extract_companies,      # extrae compañías -> "companies_json"
        step_extract_multi_projects, # extrae proyectos -> "projects_json" (con CompanyId)
        check_pg_step,               # verifica la conexión a PostgreSQL
        store_companies_step,        # guarda companies_json en "companies_bc"
        store_projects_step          # guarda projects_json en "projects_multi"
    ]

    # 8. Crear el controlador y ejecutar la pipeline
    controller = ETLController(steps)
    controller.run_etl_process()

if __name__ == "__main__":
    main()
