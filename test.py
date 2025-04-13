# test_create_table_with_pk.py

import os
import logging
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import inspect, text
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError

# --- Ajusta esta ruta si tu estructura de proyecto es diferente ---
try:
    from infrastructure.postgresql.pg_client import SqlAlchemyClient
    from infrastructure.postgresql.pg_repository import PGRepository
except ImportError:
    logging.error("Error: No se pudieron importar SqlAlchemyClient o PGRepository.")
    logging.error("Asegúrate de que el script se ejecuta desde una ubicación donde pueda encontrar 'infrastructure/postgresql'")
    exit(1)

# --- Configuración del Test ---
if not load_dotenv():
     logging.warning("Advertencia: No se encontró el archivo .env.")

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - [%(module)s.%(funcName)s] - %(message)s')

TEST_TABLE_NAME = "test"
PK_COLUMN_NAME = "item_id"

# --- Datos de Prueba ---
def create_sample_dataframe() -> pd.DataFrame:
    """Crea un DataFrame simple para la prueba."""
    data = {
        PK_COLUMN_NAME: [1001, 1002, 1003],
        "item_name": ["Widget", "Gadget", "Thingamajig"],
        "stock_level": [50, 0, 120],
        "last_updated": pd.to_datetime(['2023-01-10', '2023-01-15', '2023-01-12'])
    }
    return pd.DataFrame(data)

# --- Función Principal de Prueba ---
def run_test():
    """Ejecuta la prueba de creación de tabla con PK."""
    logging.info("--- Iniciando Test: Creación de Tabla con PK ---")

    pg_host = os.getenv("PG_HOST")
    pg_port_str = os.getenv("PG_PORT")
    pg_user = os.getenv("PG_USER")
    pg_password = os.getenv("PG_PASSWORD")
    pg_dbname = os.getenv("PG_DBNAME")

    if not all([pg_host, pg_port_str, pg_user, pg_password, pg_dbname]):
        logging.error("Error: Faltan variables de entorno PostgreSQL. Verifica .env")
        return

    try:
         pg_port = int(pg_port_str)
    except ValueError:
         logging.error(f"Error: PG_PORT ('{pg_port_str}') no es un número válido.")
         return

    sa_client = SqlAlchemyClient(host=pg_host, port=pg_port, user=pg_user, password=pg_password, dbname=pg_dbname)
    pg_repository = PGRepository(sa_client)
    engine = None # Para manejar el engine en finally

    try:
        logging.info(f"Asegurando que la base de datos '{sa_client.dbname}' existe...")
        pg_repository.create_database_if_not_exists()
        logging.info("Base de datos lista.")

        # --- CORRECCIÓN AQUÍ ---
        # Obtener engine para operaciones directas usando el cliente
        engine = pg_repository.sa_client.get_engine()
        logging.info(f"Intentando eliminar la tabla '{TEST_TABLE_NAME}' si existe (limpieza previa)...")
        with engine.connect() as conn:
            try:
                conn.execute(text(f'DROP TABLE IF EXISTS "{TEST_TABLE_NAME}" CASCADE;').execution_options(autocommit=True))
                logging.info(f"Tabla '{TEST_TABLE_NAME}' eliminada o no existía.")
            except (ProgrammingError, SQLAlchemyError) as drop_err:
                 logging.warning(f"No se pudo eliminar la tabla '{TEST_TABLE_NAME}': {drop_err}")

        sample_df = create_sample_dataframe()
        logging.info(f"DataFrame de ejemplo creado con columnas: {sample_df.columns.tolist()}")
        if PK_COLUMN_NAME not in sample_df.columns:
            logging.error(f"Error de configuración: La PK '{PK_COLUMN_NAME}' no está en el DF.")
            if engine: engine.dispose()
            return

        logging.info(f"Llamando a create_table_from_df para '{TEST_TABLE_NAME}' con PK='{PK_COLUMN_NAME}'...")
        pg_repository.create_table_from_df(
            table_name=TEST_TABLE_NAME,
            df=sample_df,
            primary_key=PK_COLUMN_NAME # Usa 'primary_key' según tu repo
        )
        logging.info("Llamada a create_table_from_df completada.")

        logging.info("Verificando si la tabla y la PK fueron creadas correctamente...")
        # --- CORRECCIÓN AQUÍ ---
        # Reobtener engine fresco usando el cliente
        if engine: engine.dispose() # Desechar el anterior
        engine = pg_repository.sa_client.get_engine()
        inspector = inspect(engine)

        if not inspector.has_table(TEST_TABLE_NAME):
            logging.error(f"¡FALLO! La tabla '{TEST_TABLE_NAME}' NO fue encontrada.")
            if engine: engine.dispose()
            return
        logging.info(f"Tabla '{TEST_TABLE_NAME}' encontrada.")

        pk_constraint = None
        try:
            pk_constraint = inspector.get_pk_constraint(TEST_TABLE_NAME)
        except Exception as inspect_err:
             logging.error(f"Error al obtener la PK de '{TEST_TABLE_NAME}': {inspect_err}")
             if engine: engine.dispose()
             return

        if not pk_constraint or not pk_constraint.get('constrained_columns'):
            logging.error(f"¡FALLO! No se encontró PRIMARY KEY en '{TEST_TABLE_NAME}'. Constraint: {pk_constraint}")
            if engine: engine.dispose()
            return

        pk_columns = pk_constraint['constrained_columns']
        if PK_COLUMN_NAME not in pk_columns:
            logging.error(f"¡FALLO! PK encontrada {pk_columns}, se esperaba '{PK_COLUMN_NAME}'.")
            if engine: engine.dispose()
            return

        logging.info(f"PRIMARY KEY encontrada en columna(s): {pk_columns}")
        logging.info("¡ÉXITO! Tabla creada y PK verificada.")

        logging.info(f"Intentando insertar datos de ejemplo en '{TEST_TABLE_NAME}'...")
        pg_repository.insert_table(TEST_TABLE_NAME, sample_df)
        logging.info("Datos de ejemplo insertados.")

        with engine.connect() as conn:
            count = None
            try:
                count_result = conn.execute(text(f'SELECT COUNT(*) FROM "{TEST_TABLE_NAME}"'))
                count = count_result.scalar()
                logging.info(f"Verificación de conteo: {count} filas encontradas (esperado: {len(sample_df)}).")
                if count != len(sample_df):
                     logging.warning("El conteo de filas post-inserción no coincide.")
            except Exception as count_err:
                 logging.error(f"Error al verificar conteo de filas: {count_err}")

    except (ConnectionError, ValueError, RuntimeError, PermissionError, SQLAlchemyError, ProgrammingError) as e:
        logging.error(f"Error durante la prueba: {e}", exc_info=True)
    except Exception as e:
        logging.exception(f"Error inesperado durante la prueba: {e}")
    finally:
        if engine:
            logging.info(f"Intentando eliminar tabla '{TEST_TABLE_NAME}' (limpieza final)...")
            try:
                 with engine.connect() as conn:
                      conn.execute(text(f'DROP TABLE IF EXISTS "{TEST_TABLE_NAME}" CASCADE;').execution_options(autocommit=True))
                      logging.info("Tabla de prueba eliminada.")
            except Exception as final_clean_e:
                 logging.error(f"Error en la limpieza final: {final_clean_e}")
            finally:
                 engine.dispose()
        logging.info("--- Test Finalizado ---")


# --- Punto de Entrada ---
if __name__ == "__main__":
    run_test()