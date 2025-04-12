"""
main.py
Punto de entrada de la aplicación.
Configura el pipeline: primero extraemos datos de BC,
luego almacenamos esos datos en PostgreSQL.
"""

from infrastructure.business_central.bc_client import BCClient
from infrastructure.business_central.bc_repository import BCRepository
from infrastructure.postgresql.pg_client import SqlAlchemyClient
from infrastructure.postgresql.pg_repository import PGRepository

from domain.services.transform_service import TransformService
from application.use_cases.bc_use_cases import BCUseCases
from application.use_cases.csv_export_service import CSVExportService

from interface_adapters.controllers.etl_controller import ETLController
from interface_adapters.controllers.pipeline_steps import (
    ExtractCompaniesStep,
    ExtractProjectsStep,
    CheckPostgresConnectionStep,
    StoreDataInPostgresStep
)

def main():
    # 1. Infraestructura de Business Central
    bc_client = BCClient()
    bc_repository = BCRepository(bc_client)

    # 2. Servicios de dominio / aplicación
    transform_service = TransformService()
    bc_use_cases = BCUseCases(bc_repository, transform_service)
    csv_exporter = CSVExportService()

    # 3. Infraestructura Postgres via SQLAlchemy
    sa_client = SqlAlchemyClient()          # Usa settings para PG_HOST, PG_USER, etc.
    pg_repository = PGRepository(sa_client) # Repositorio que operará con la DB

    # 4. Steps de extracción de datos
    step_extract_companies = ExtractCompaniesStep(
        bc_use_cases=bc_use_cases,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=False,    # no exportamos a CSV en este ejemplo
        csv_file_path="companies_export.csv"
    )
    step_extract_projects = ExtractProjectsStep(
        bc_use_cases=bc_use_cases,
        company_id="4a0799a1-96cd-ef11-8a6d-7c1e527596b1",  # Ejemplo de Company ID
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=False,
        csv_file_path="projects_data.csv"
    )

    # 5. Step para verificar conexión a PostgreSQL
    check_pg_step = CheckPostgresConnectionStep(pg_repository)

    # 6. Steps para almacenar compañías y proyectos en la DB
    #    Se asume que en el context, ExtractCompaniesStep guarda los datos en "companies_json"
    #    y ExtractProjectsStep en "projects_json"
    store_companies_step = StoreDataInPostgresStep(
        pg_repository=pg_repository,
        context_key="companies_json",  # clave donde se guardan las compañías
        table_name="companies_bc",     # nombre de la tabla en Postgres
        convert_json_to_df=True,       # si es JSON, se convierte a DF
        if_exists="append"
    )
    store_projects_step = StoreDataInPostgresStep(
        pg_repository=pg_repository,
        context_key="projects_json",   # clave donde se guardan los proyectos
        table_name="projects_bc",      # nombre de la tabla en Postgres
        convert_json_to_df=True,
        if_exists="append"
    )

    # 7. Definir la secuencia de steps
    steps = [
        step_extract_companies,   # extrae compañías -> "companies_json"
        step_extract_projects,    # extrae proyectos  -> "projects_json"
        check_pg_step,            # verifica la conexión a PostgreSQL
        store_companies_step,     # guarda "companies_json" en la tabla "companies_bc"
        store_projects_step       # guarda "projects_json"   en la tabla "projects_bc"
    ]

    # 8. Crear el controlador y ejecutar la pipeline
    controller = ETLController(steps)
    controller.run_etl_process()

if __name__ == "__main__":
    main()
