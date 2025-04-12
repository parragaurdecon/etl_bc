"""
main.py
Punto de entrada de la aplicación. Construye la lista de Steps ETL y la ejecuta.
"""

from infrastructure.business_central.bc_client import BCClient
from infrastructure.business_central.bc_repository import BCRepository

from domain.services.transform_service import TransformService
from application.use_cases.bc_use_cases import BCUseCases
from application.use_cases.csv_export_service import CSVExportService

from interface_adapters.controllers.etl_controller import ETLController

# Importamos los steps refactorizados con banderas:
from interface_adapters.controllers.pipeline_steps import (
    ExtractCompaniesStep,
    ExtractCompanyRawDataStep,
    ExtractCompanyTablesStep,
    ExtractProjectsStep,
    ExtractProjectTasksStep
)


def main():
    # Ejemplo de IDs
    company_id = "4a0799a1-96cd-ef11-8a6d-7c1e527596b1"
    project_id = "0221f95c-8114-f011-9346-7c1e526011ed"

    # 1. Infraestructura
    bc_client = BCClient()
    bc_repository = BCRepository(bc_client)

    # 2. Servicios / Casos de uso
    transform_service = TransformService()
    bc_use_cases = BCUseCases(bc_repository, transform_service)

    # 3. Servicio de exportación a CSV
    csv_exporter = CSVExportService()

    # 4. Definir los Steps
    #   A) Extrae las compañías, las imprime y las exporta a CSV
    step_extract_companies = ExtractCompaniesStep(
        bc_use_cases=bc_use_cases,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=True,
        csv_file_path="companies_export.csv"
    )

    #   B) Extrae datos "raw" de la compañía, sin imprimir y sin exportar
    step_extract_company_raw = ExtractCompanyRawDataStep(
        bc_use_cases=bc_use_cases,
        company_id=company_id,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=True
    )

    #   C) Extrae las tablas (entityDefinitions) y solo las imprime (no exporta)
    step_extract_company_tables = ExtractCompanyTablesStep(
        bc_use_cases=bc_use_cases,
        company_id=company_id,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=True
    )

    #   D) Extrae los proyectos, los imprime y los exporta
    step_extract_projects = ExtractProjectsStep(
        bc_use_cases=bc_use_cases,
        company_id=company_id,
        csv_export_service=csv_exporter,
        print_to_console=True,
        export_to_csv=True,
        csv_file_path="projects_data.csv"
    )

    #   E) Extrae las tareas de un proyecto, sin imprimir y exportando a CSV
    # step_extract_project_tasks = ExtractProjectTasksStep(
    #     bc_use_cases=bc_use_cases,
    #     company_id=company_id,
    #     project_id=project_id,
    #     csv_export_service=csv_exporter,
    #     print_to_console=False,
    #     export_to_csv=True,
    #     csv_file_path="project_tasks_data.csv"
    # )

    # 5. Definir el pipeline de steps
    steps = [
        step_extract_companies,
        step_extract_company_raw,
        step_extract_company_tables,
        step_extract_projects,
        # step_extract_project_tasks
    ]

    # 6. Orquestador ETL con la lista de pasos
    controller = ETLController(steps)

    # 7. Ejecutar el pipeline
    controller.run_etl_process()


if __name__ == "__main__":
    main()
