# main.py

import logging
import sys

# --- Importaciones (Asegúrate que todas son correctas) ---
try:
    from infrastructure.business_central.bc_client import BCClient
    from infrastructure.business_central.bc_repository import BCRepository
    from infrastructure.postgresql.pg_client import SqlAlchemyClient
    from infrastructure.postgresql.pg_repository import PGRepository
    from domain.services.transform_service import TransformService
    from application.use_cases.bc_use_cases import BCUseCases
    from application.use_cases.csv_export_service import CSVExportService
    # Importar el ETLController MODIFICADO
    from interface_adapters.controllers.etl_controller import ETLController
    # Importar Steps de Extracción
    from interface_adapters.controllers.pipeline_extract import (
        ExtractCompaniesStep,
        ExtractMultiCompanyStep,
    )
    # Importar Steps de Almacenamiento
    from interface_adapters.controllers.pipeline_store import (
        CheckPostgresConnectionStep,
        StoreDataInPostgresStep
    )
except ImportError as import_err:
     print(f"Error crítico de importación: {import_err}")
     sys.exit(1)

# --- CONFIGURACIÓN DE LOGGING (Mantener como estaba) ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)
# -----------------------------

def main():
    logger.info("=============================================")
    logger.info("--- Iniciando Pipeline ETL: BC a PostgreSQL ---")
    logger.info("=============================================")

    final_status_message = "--- Pipeline ETL finalizado ---"
    exit_code = 0
    issue_summary = "Sin problemas registrados."
    # Necesitamos inicializar issue_counter fuera del try para el finally
    issue_counter = None

    try:
        # --- 1. Configuración de Dependencias (sin cambios) ---
        logger.info("1. Configurando dependencias...")
        # ... (instanciar bc_client, bc_repository, transform_service, etc.) ...
        bc_client = BCClient()
        bc_repository = BCRepository(bc_client)
        transform_service = TransformService()
        bc_use_cases = BCUseCases(bc_repository, transform_service)
        csv_exporter = CSVExportService()
        sa_client = SqlAlchemyClient()
        pg_repository = PGRepository(sa_client)
        logger.info("Dependencias configuradas.")

        # --- 2. Definición de los Pasos del Pipeline (CON ARGUMENTOS) ---
        logger.info("2. Definiendo los pasos del pipeline ETL...")

        # Paso 1: Extraer Compañías (Filtradas por Use Case)
        step_extract_companies = ExtractCompaniesStep(
            bc_use_cases=bc_use_cases,
            csv_export_service=csv_exporter,
            export_to_csv=True,
            csv_file_path="companies_filtered_export.csv"
            # context_key por defecto es 'companies_json'
        )
        logger.debug("... Step 'ExtractCompaniesStep' definido.")

        # Paso 2: Extraer Proyectos para las compañías filtradas
        step_extract_multi_projects = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_projects, # <--- Argumento requerido
            out_context_key="projects_json",              # <--- Argumento requerido
            company_col="CompanyId"                       # Argumento opcional
        )
        logger.debug("... Step 'ExtractMultiCompanyStep' para Proyectos definido.")

        # Paso 3: Extraer Clientes para las compañías filtradas
        step_extract_multi_customers = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_customers, # <--- Argumento requerido
            out_context_key="customers_json",             # <--- Argumento requerido
            company_col="CompanyId"
        )
        logger.debug("... Step 'ExtractMultiCompanyStep' para Clientes definido.")

        # Paso 4: Verificar Conexión a PostgreSQL
        check_pg_step = CheckPostgresConnectionStep(
            pg_repository=pg_repository
        )
        logger.debug("... Step 'CheckPostgresConnectionStep' definido.")

        # Paso 5: Almacenar Compañías (Modo Incremental)
        store_companies_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="companies_json",
            table_name="companies_bc",
            convert_json_to_df=True,
            primary_key="id" # Activa modo incremental
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para companies_bc definido.")

        # Paso 6: Almacenar Proyectos (Modo Incremental)
        store_projects_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="projects_json",
            table_name="projects_bc",
            convert_json_to_df=True,
            primary_key="id" # Activa modo incremental
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para projects_bc definido.")

        # Paso 7: Almacenar Clientes (Modo Incremental)
        store_customers_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="customers_json",
            table_name="customers_bc",
            convert_json_to_df=True,
            primary_key="id" # O la PK correcta para clientes
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para customers_bc definido.")

        logger.info("Pasos del pipeline definidos.")

        # --- 3. Definir la Secuencia ---
        steps = [
            step_extract_companies,
            step_extract_multi_projects,
            step_extract_multi_customers,
            check_pg_step,
            store_companies_step,
            store_projects_step,
            store_customers_step
        ]
        logger.info(f"Secuencia del pipeline establecida con {len(steps)} steps.")

        # --- 4. Ejecutar el Pipeline ---
        logger.info("4. Ejecutando el controlador ETL...")
        controller = ETLController(steps)
        # Ejecutar y capturar el contador de problemas
        final_context, issue_counter = controller.run_etl_process() # issue_counter puede ser None si falla la importación del handler

        # --- 5. Verificar si hubo problemas registrados por el handler ---
        if issue_counter and issue_counter.has_errors: # Comprobar si issue_counter existe
            final_status_message = f"--- Pipeline ETL finalizado con ERRORES ({issue_counter.issue_summary}) ---"
            exit_code = 1
        elif issue_counter and issue_counter.has_warnings:
            final_status_message = f"--- Pipeline ETL finalizado con ADVERTENCIAS ({issue_counter.issue_summary}) ---"
        else:
            final_status_message = f"--- Pipeline ETL finalizado con ÉXITO ({issue_summary}) ---"


    except RuntimeError as e:
         final_status_message = f"--- Pipeline ETL DETENIDO por ERROR FATAL: {e} ---"
         exit_code = 1
         # El traceback ya se logueó en el controller
    except ImportError as e:
         logger.critical(f"Error fatal de importación: {e}", exc_info=True)
         final_status_message = "--- Pipeline ETL DETENIDO por ERROR DE IMPORTACIÓN ---"
         exit_code = 1
    except Exception as e:
        logger.exception("Error INESPERADO no capturado durante la configuración o ejecución del pipeline en main:")
        final_status_message = "--- Pipeline ETL finalizado con ERRORES INESPERADOS ---"
        exit_code = 1

    # --- Mensaje Final ---
    logger.info("====================================================")
    log_level = logging.INFO
    if exit_code != 0:
        log_level = logging.ERROR
    elif issue_counter and issue_counter.has_warnings:
        log_level = logging.WARNING

    logger.log(log_level, final_status_message) # Usar nivel calculado
    logger.info("====================================================")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()