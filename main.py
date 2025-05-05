# main.py

import logging
import sys
import pandas as pd # Importar pandas para mostrar DataFrames

# --- Importaciones de tu aplicación ---
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
    from interface_adapters.controllers.pipeline_store import (
        CheckPostgresConnectionStep,
        StoreDataInPostgresStep
    )

    from interface_adapters.controllers.pipeline_transform import (
        DropColumnsStep, ConcatColumnsStep
    )

except ImportError as import_err:
     print(f"Error crítico de importación: {import_err}")
     sys.exit(1)

# --- CONFIGURACIÓN DE LOGGING ---
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
    issue_counter = None
    final_context = {} # Inicializar contexto final

    try:
        # --- 1. Configuración de Dependencias ---
        logger.info("1. Configurando dependencias...")
        bc_client = BCClient()
        bc_repository = BCRepository(bc_client)
        transform_service = TransformService()
        bc_use_cases = BCUseCases(bc_repository, transform_service)
        csv_exporter = CSVExportService()
        sa_client = SqlAlchemyClient()
        pg_repository = PGRepository(sa_client)
        logger.info("Dependencias configuradas.")

        # --- 2. Definición de los Pasos del Pipeline ---
        logger.info("2. Definiendo los pasos del pipeline ETL...")

        # --- Extracción ---
        step_extract_companies = ExtractCompaniesStep(
            bc_use_cases=bc_use_cases,
            csv_export_service=csv_exporter,
            export_to_csv=True, # Exportar compañías filtradas
            csv_file_path="companies_filtered_export.csv"
        )
        logger.debug("... Step ExtractCompaniesStep definido.")

        # API v2 Steps (usan ID)
        step_extract_multi_projects = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_projects,
            out_context_key="projects_json",
            company_col="CompanyId",
            # identifier_key="id" # Explícito para claridad
        )
        logger.debug("... Step ExtractMultiCompanyStep (Projects API v2) definido.")

        step_extract_multi_customers_apiv2 = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_customers,
            out_context_key="customers_apiv2_json", # Nueva clave para distinguir
            company_col="CompanyId",
            # identifier_key="id"
        )
        logger.debug("... Step ExtractMultiCompanyStep (Customers API v2) definido.")

        step_extract_multi_purchase_invoices  = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_purchase_invoices,
            out_context_key="purchase_invoices_json",  # Nueva clave para distinguir
            company_col="CompanyId",
            # identifier_key="id"
        )
        logger.debug("... Step ExtractMultiCompanyStep (Customers API v2) definido.")

        step_extract_multi_purchase_invoices_lines = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_purchase_invoice_lines,
            out_context_key="purchase_invoices_lines_json",  # Nueva clave para distinguir
            company_col="CompanyId",
            # identifier_key="id"
        )
        logger.debug("... Step ExtractMultiCompanyStep (Customers API v2) definido.")

        # ODataV4 Steps (usan Nombre)
        step_extract_multi_job_ledger = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_job_ledger_entries,
             out_context_key="job_ledger_entries_json",
             company_col="CompanyId",
             # identifier_key="name" # Pasar nombre
        )
        logger.debug("... Step ExtractMultiCompanyStep (JobLedger OData) definido.")

        step_extract_multi_job_list = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_job_list,
             out_context_key="job_list_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (JobList OData) definido.")

        step_extract_multi_job_plan_lines = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_job_planning_lines,
             out_context_key="job_planning_lines_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (JobPlanningLines OData) definido.")

        step_extract_multi_job_task_lines = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_job_task_lines,
             out_context_key="job_task_lines_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (JobTaskLines OData) definido.")

        step_extract_multi_job_task_lines_subform = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_job_task_line_subform,
            out_context_key="job_task_lines_subform_json",
            company_col="CompanyId",
            # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (JobTaskLines OData) definido.")

        step_extract_multi_customer_list = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_customer_list,
            out_context_key="customer_list_json", # Clave específica
            company_col="CompanyId",
            # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (CustomerList OData) definido.")

        step_extract_multi_cle = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_customer_ledger_entries,
            out_context_key="customer_ledger_entries_json",
            company_col="CompanyId",
            # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (CustLedgerEntries OData) definido.")

        step_extract_multi_vendor_list = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_vendor_list,
             out_context_key="vendor_list_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (VendorList OData) definido.")

        step_extract_multi_vle = ExtractMultiCompanyStep(
            companies_context_key="companies_json",
            extract_func=bc_use_cases.get_company_vendor_ledger_entries,
            out_context_key="vendor_ledger_entries_json",
            company_col="CompanyId",
            # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (VendLedgerEntries OData) definido.")

        step_extract_multi_purchase_docs = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_purchase_documents,
             out_context_key="purchase_documents_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (PurchaseDocs OData) definido.")

        step_extract_multi_sales_docs = ExtractMultiCompanyStep(
             companies_context_key="companies_json",
             extract_func=bc_use_cases.get_company_sales_documents,
             out_context_key="sales_documents_json",
             company_col="CompanyId",
             # identifier_key="name"
        )
        logger.debug("... Step ExtractMultiCompanyStep (SalesDocs OData) definido.")

        step_drop_job_list = DropColumnsStep(
            transform_service,
            context_key="job_list_json",
            columns={"Person_Responsible", "Project_Manager"}
        )

        step_concat_job_list = ConcatColumnsStep(
            transform_service,
            context_key="job_list_json",
            new_col="Id",
            cols=["No", "CompanyId"]
        )

        step_concat_job_task_lines = ConcatColumnsStep(
            transform_service,
            context_key="job_task_lines_json",
            new_col="project_company",
            cols=["Job_No", "CompanyId"]
        )

        step_concat_job_ledger_entries = ConcatColumnsStep(
            transform_service,
            context_key="job_ledger_entries_json",
            new_col="project_company",
            cols=["Job_No", "CompanyId"]
        )

        # --- Almacenamiento (Solo para tablas existentes) ---
        check_pg_step = CheckPostgresConnectionStep(pg_repository)
        logger.debug("... Step 'CheckPostgresConnectionStep' definido.")

        store_companies_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="companies_json",
            table_name="companies_bc",
            convert_json_to_df=True,
            primary_key="id"
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para companies_bc definido.")

        store_projects_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="projects_json",
            table_name="projects_bc",
            convert_json_to_df=True,
            primary_key="id"
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para projects_bc definido.")

        # Mantenemos el step de customers API v2 por ahora, comentar si se reemplaza por customer_list
        store_customers_apiv2_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="customers_apiv2_json", # Usar la nueva clave
            table_name="customers_bc", # Podría ir a la misma tabla o una nueva
            convert_json_to_df=True,
            primary_key="id"
        )
        # --- NUEVOS Steps de Almacenamiento (ODataV4) ---
        store_job_ledger_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="job_ledger_entries_json",
            table_name="job_ledger_entries_bc", primary_key="Entry_No"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para job_ledger_entries_bc definido.")

        store_job_list_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="job_list_json",
            table_name="job_list_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para job_list_bc definido.")

        store_job_list_subform_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="job_task_lines_subform_json",
            table_name="job_task_lines_subform_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para job_task_lines_subform_bc definido.")

        store_job_planning_lines_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="job_planning_lines_json",
            table_name="job_planning_lines_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para job_planning_lines_bc definido.")

        store_job_task_lines_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="job_task_lines_json",
            table_name="job_task_lines_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para job_task_lines_bc definido.")

        store_customer_list_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="customer_list_json",
            table_name="customer_list_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para customer_list_bc definido.")

        store_cle_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="customer_ledger_entries_json",
            table_name="customer_ledger_entries_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para customer_ledger_entries_bc definido.")

        store_vendor_list_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="vendor_list_json",
            table_name="vendor_list_bc", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para vendor_list_bc definido.")

        store_vle_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="vendor_ledger_entries_json",
            table_name="vendor_ledger_entries_bc", primary_key="Entry_No"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para vendor_ledger_entries_bc definido.")

        store_purchase_docs_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="purchase_documents_json",
            table_name="purchase_documents_bc", primary_key="id"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para purchase_documents_bc definido.")

        store_sales_docs_step = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="sales_documents_json",
            table_name="sales_documents_bc", primary_key="id"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para sales_documents_bc definido.")

        store_purchase_invoices = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="purchase_invoices_lines",
            table_name="purchase_invoices", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para sales_documents_bc definido.")

        store_purchase_invoices_lines = StoreDataInPostgresStep(
            pg_repository=pg_repository, context_key="purchase_invoices_lines_json",
            table_name="purchase_invoices_lines", primary_key="@odata.etag"  # PK especificada
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para sales_documents_bc definido.")

        logger.info("Pasos del pipeline definidos.")

        # --- 3. Definir la Secuencia ---
        steps = [
            # Extracción
            step_extract_companies,
            step_extract_multi_projects,
            step_extract_multi_customers_apiv2,
            step_extract_multi_job_ledger,
            step_extract_multi_job_list,
            step_extract_multi_job_plan_lines,
            step_extract_multi_job_task_lines,
            step_extract_multi_customer_list,
            step_extract_multi_cle,
            step_extract_multi_vendor_list,
            step_extract_multi_vle,
            step_extract_multi_purchase_docs,
            step_extract_multi_sales_docs,
            step_extract_multi_job_task_lines_subform,
            # step_extract_multi_purchase_invoices,
            # step_extract_multi_purchase_invoices_lines,

            # Verificación y Carga
            check_pg_step,

            step_drop_job_list,
            step_concat_job_list,
            step_concat_job_task_lines,
            step_concat_job_ledger_entries,

            store_companies_step,
            store_projects_step,
            store_customers_apiv2_step,  # O el step para customer_list_bc si lo prefieres
            # Añadir los nuevos steps de almacenamiento
            store_job_ledger_step,
            store_job_list_step,
            store_job_planning_lines_step,
            store_job_task_lines_step,
            store_customer_list_step,
            store_cle_step,
            store_vendor_list_step,
            store_vle_step,
            store_purchase_docs_step,
            store_sales_docs_step,
            store_job_list_subform_step,
        ]
        logger.info(f"Secuencia del pipeline establecida con {len(steps)} steps.")

        # --- 4. Ejecutar el Pipeline ---
        logger.info("4. Ejecutando el controlador ETL...")
        controller = ETLController(steps)
        final_context, issue_counter = controller.run_etl_process()

        # --- 5. Verificar Resultados y Estado Final ---
        if issue_counter and issue_counter.has_errors:
            final_status_message = f"--- Pipeline ETL finalizado con ERRORES ({issue_counter.issue_summary}) ---"
            exit_code = 1
        elif issue_counter and issue_counter.has_warnings:
            final_status_message = f"--- Pipeline ETL finalizado con ADVERTENCIAS ({issue_counter.issue_summary}) ---"
        else:
            # Comprobar si issue_counter existe antes de acceder a issue_summary
            summary = issue_counter.issue_summary if issue_counter else "Sin contador de problemas."
            final_status_message = f"--- Pipeline ETL finalizado con ÉXITO ({summary}) ---"

        # # --- 6. Imprimir Muestra de Nuevos Datos (Opcional) ---
        # logger.info("--- Muestra de Datos Extraídos (Nuevas Tablas OData) ---")
        # new_keys_to_print = [
        #     "job_ledger_entries_json", "job_list_json", "job_planning_lines_json",
        #     "job_task_lines_json", "customer_list_json", "customer_ledger_entries_json",
        #     "vendor_list_json", "vendor_ledger_entries_json",
        #     "purchase_documents_json", "sales_documents_json"
        # ]
        # for key in new_keys_to_print:
        #     if key in final_context:
        #         data = final_context[key]
        #         if isinstance(data, dict) and 'value' in data and isinstance(data['value'], list):
        #              records = data['value']
        #              logger.info(f"\n*** Datos para '{key}' (Total: {len(records)}):")
        #              if records:
        #                   # Convertir a DF para mostrar más bonito
        #                   try:
        #                       df_sample = pd.DataFrame(records)
        #                       logger.info(f"\n{df_sample.head().to_string()}") # Imprimir las primeras 5 filas
        #                   except Exception as e:
        #                        logger.warning(f"No se pudo convertir '{key}' a DataFrame para mostrar: {e}")
        #                        logger.info(str(records[:2])) # Imprimir los primeros 2 diccionarios como fallback
        #              else:
        #                   logger.info("(Vacío)")
        #         else:
        #              logger.warning(f"Contenido inesperado para '{key}' en el contexto: {type(data)}")
        #     else:
        #          logger.warning(f"Clave '{key}' no encontrada en el contexto final.")
        # logger.info("-------------------------------------------------------")


    # --- Manejo de Excepciones (como antes) ---
    except RuntimeError as e:
         final_status_message = f"--- Pipeline ETL DETENIDO por ERROR FATAL: {e} ---"
         exit_code = 1
    except ImportError as e:
         logger.critical(f"Error fatal de importación: {e}", exc_info=True)
         final_status_message = "--- Pipeline ETL DETENIDO por ERROR DE IMPORTACIÓN ---"
         exit_code = 1
    except Exception as e:
        logger.exception("Error INESPERADO no capturado durante la ejecución:")
        final_status_message = "--- Pipeline ETL finalizado con ERRORES INESPERADOS ---"
        exit_code = 1

    # --- Mensaje Final (como antes) ---
    logger.info("====================================================")
    log_level = logging.INFO
    if exit_code != 0 : log_level = logging.ERROR
    elif issue_counter and issue_counter.has_warnings: log_level = logging.WARNING
    logger.log(log_level, final_status_message)
    logger.info("====================================================")

    sys.exit(exit_code)

if __name__ == "__main__":
    main()