"""
main.py
Punto de entrada de la aplicación.
Configura el pipeline ETL:
1. Extrae compañías (ya filtradas por el caso de uso).
2. Extrae proyectos para las compañías válidas.
3. Verifica conexión a PostgreSQL.
4. Almacena compañías en PostgreSQL (modo incremental).
5. Almacena proyectos en PostgreSQL (modo incremental).
"""

import logging
import sys

# --- Importaciones de tu aplicación ---
# Asegúrate de que las rutas sean correctas para tu estructura de proyecto
try:
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
    # Importar la versión de StoreDataInPostgresStep que delega la lógica incremental
    from interface_adapters.controllers.pipeline_store import (
        CheckPostgresConnectionStep,
        StoreDataInPostgresStep
    )
except ImportError as import_err:
     print(f"Error crítico: No se pudieron importar módulos necesarios: {import_err}")
     print("Verifica la estructura de tu proyecto y las rutas de importación.")
     sys.exit(1) # Salir si las importaciones fallan


# --- CONFIGURACIÓN DE LOGGING ---
# Configurar al principio del script
logging.basicConfig(
    level=logging.INFO,  # Nivel mínimo a mostrar (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    format='%(asctime)s - %(levelname)s - [%(name)s:%(lineno)d] - %(message)s', # Formato mejorado con línea
    datefmt='%Y-%m-%d %H:%M:%S', # Formato de la fecha/hora
    stream=sys.stdout # Dirigir la salida a la consola estándar
    # Opcional: filename='etl_pipeline.log', filemode='a'
)

# Logger para main.py
logger = logging.getLogger(__name__)
# -----------------------------

def main():
    logger.info("=============================================")
    logger.info("--- Iniciando Pipeline ETL: BC a PostgreSQL ---")
    logger.info("=============================================")

    try:
        # --- 1. Configuración de Dependencias ---
        logger.info("1. Configurando dependencias...")

        # Business Central
        logger.debug("... Configurando cliente y repositorio BC")
        bc_client = BCClient() # Asume configuración interna (ej. .env)
        bc_repository = BCRepository(bc_client)

        # Servicios
        logger.debug("... Configurando servicios de dominio y aplicación")
        transform_service = TransformService()
        # Pasar el repositorio Y el servicio de transformación
        bc_use_cases = BCUseCases(bc_repository, transform_service)
        csv_exporter = CSVExportService()

        # PostgreSQL
        logger.debug("... Configurando cliente y repositorio PostgreSQL")
        # SqlAlchemyClient también debería leer de .env o config
        sa_client = SqlAlchemyClient()
        pg_repository = PGRepository(sa_client)
        logger.info("Dependencias configuradas.")

        # --- 2. Definición de los Pasos del Pipeline ---
        logger.info("2. Definiendo los pasos del pipeline ETL...")

        # Paso 1: Extraer Compañías (ya filtradas por el caso de uso)
        step_extract_companies = ExtractCompaniesStep(
            bc_use_cases=bc_use_cases,
            csv_export_service=csv_exporter,
            export_to_csv=True, # Mantener exportación CSV si se desea
            csv_file_path="companies_filtered_export.csv" # Nombre actualizado
            # 'print_to_console' ya no es necesario, usar logging
            # 'context_key' usa el default "companies_json"
        )
        logger.debug("... Step 'ExtractCompaniesStep' definido.")

        # Paso 2: Extraer Proyectos para las compañías filtradas
        step_extract_multi_projects = ExtractMultiCompanyStep(
            companies_context_key="companies_json", # Usa la salida del step anterior
            extract_func=bc_use_cases.get_company_projects, # Función del caso de uso
            out_context_key="projects_json", # Donde guardar el resultado
            company_col="CompanyId" # Nombre de columna para el ID de compañía
            # 'print_to_console' ya no es necesario
        )
        logger.debug("... Step 'ExtractMultiCompanyStep' definido.")

        # Paso 3: Verificar Conexión a PostgreSQL
        check_pg_step = CheckPostgresConnectionStep(pg_repository)
        logger.debug("... Step 'CheckPostgresConnectionStep' definido.")

        # Paso 4: Almacenar Compañías (Modo Incremental)
        store_companies_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="companies_json", # Usa las compañías filtradas
            table_name="companies_bc",
            convert_json_to_df=True,
            primary_key="id" # Activa el modo incremental en el repositorio
            # 'if_exists' no se necesita para el modo incremental gestionado por el repo
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para companies_bc definido.")

        # Paso 5: Almacenar Proyectos (Modo Incremental)
        store_projects_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="projects_json", # Usa los proyectos extraídos
            table_name="projects_bc",    # Nombre correcto de la tabla
            convert_json_to_df=True,
            primary_key="id" # Activa el modo incremental en el repositorio
            # 'if_exists' no se necesita
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para projects_bc definido.")

        logger.info("Pasos del pipeline definidos.")

        # --- 3. Definir la Secuencia ---
        steps = [
            step_extract_companies,
            step_extract_multi_projects,
            check_pg_step,
            store_companies_step,
            store_projects_step
        ]
        logger.info(f"Secuencia del pipeline establecida con {len(steps)} steps.")

        # --- 4. Ejecutar el Pipeline ---
        logger.info("4. Ejecutando el controlador ETL...")
        controller = ETLController(steps)
        controller.run_etl_process() # run_etl_process debería manejar errores internos de steps si es necesario

        logger.info("==============================================")
        logger.info("--- Pipeline ETL finalizado con éxito ---")
        logger.info("==============================================")

    except ImportError as e:
         # Captura errores de importación que podrían no haber sido atrapados antes
         logger.critical(f"Error fatal de importación al configurar dependencias: {e}", exc_info=True)
         sys.exit(1)
    except RuntimeError as e:
         # Captura errores relanzados por los steps (ej. fallo de conexión PG)
         logger.error(f"==============================================")
         logger.error(f"--- Pipeline ETL detenido debido a un error: {e} ---", exc_info=False) # No mostrar traceback aquí si ya se logueó antes
         logger.error(f"==============================================")
         sys.exit(1) # Salir con código de error
    except Exception as e:
        # Capturar cualquier otro error inesperado en el flujo principal de main
        logger.error("====================================================")
        logger.error("--- Pipeline ETL finalizado con ERRORES INESPERADOS ---")
        logger.error("====================================================")
        logger.exception("Error no capturado durante la configuración o ejecución del pipeline en main:") # Loguea el traceback completo
        sys.exit(1) # Salir con código de error


if __name__ == "__main__":
    main()