import logging
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError, OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database, drop_database

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Credenciales (ajusta si es necesario) ---
PG_HOST = 'localhost'
PG_DEFAULT_DBNAME = 'postgres' # Conectamos a esta DB para poder crear la nueva
PG_TARGET_DBNAME = 'business_central' # La DB que queremos crear
PG_USER = 'postgres'
PG_PASSWORD = 'admin'
PG_PORT = 5432

# --- Cadenas de Conexión ---
# Conexión a la base de datos por defecto (generalmente 'postgres') para tareas administrativas
DEFAULT_DB_URL = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DEFAULT_DBNAME}"
# Conexión a la base de datos objetivo que queremos crear/usar
TARGET_DB_URL = f"postgresql+psycopg2://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_TARGET_DBNAME}"

def check_and_create_db(engine_default_db, db_name):
    """Verifica si una base de datos existe y la crea si no."""
    if not database_exists(engine_default_db.url):
        logging.info(f"La base de datos '{db_name}' no existe. Intentando crearla...")
        try:
            create_database(engine_default_db.url)
            logging.info(f"Base de datos '{db_name}' creada exitosamente.")
        except ProgrammingError as e:
            logging.error(f"Error de permisos al intentar crear la base de datos '{db_name}': {e}")
            logging.error("Asegúrate de que el usuario 'postgres' tenga permisos para crear bases de datos.")
            raise
        except Exception as e:
            logging.error(f"Error inesperado al crear la base de datos '{db_name}': {e}")
            raise
    else:
        logging.info(f"La base de datos '{db_name}' ya existe.")

def test_connection(engine, db_name):
    """Prueba la conexión a una base de datos específica."""
    logging.info(f"Probando conexión a la base de datos '{db_name}'...")
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version();"))
            version = result.scalar()
            logging.info(f"Conexión a '{db_name}' exitosa. Versión PostgreSQL: {version}")
            return True
    except OperationalError as e:
        logging.error(f"No se pudo conectar a la base de datos '{db_name}': {e}")
        logging.error("Verifica que el servidor esté corriendo, las credenciales sean correctas y la DB exista.")
        return False
    except Exception as e:
        logging.error(f"Error inesperado al conectar a '{db_name}': {e}")
        return False

if __name__ == "__main__":
    logging.info("--- Iniciando Script de Prueba de Conexión y Creación de BBDD PostgreSQL ---")

    # 1. Crear engine para conectar a la base de datos por defecto ('postgres')
    logging.info(f"Conectando a la base de datos por defecto '{PG_DEFAULT_DBNAME}' para tareas administrativas...")
    engine_default = None
    try:
        # Usamos isolation_level='AUTOCOMMIT' para poder ejecutar CREATE DATABASE fuera de una transacción
        engine_default = create_engine(DEFAULT_DB_URL, isolation_level='AUTOCOMMIT')
        # Probamos la conexión inicial
        if not test_connection(engine_default, PG_DEFAULT_DBNAME):
             exit(1) # Salir si no se puede conectar a la DB por defecto

        # 2. Verificar y crear la base de datos objetivo si no existe
        # Construimos la URL objetivo para que sqlalchemy_utils sepa qué crear
        target_url_for_creation = TARGET_DB_URL
        target_engine_for_creation = create_engine(target_url_for_creation, isolation_level='AUTOCOMMIT')
        check_and_create_db(target_engine_for_creation, PG_TARGET_DBNAME)

        # 3. Crear engine para la base de datos objetivo y probar conexión
        logging.info(f"Creando engine para la base de datos objetivo '{PG_TARGET_DBNAME}'...")
        engine_target = create_engine(TARGET_DB_URL)
        test_connection(engine_target, PG_TARGET_DBNAME)

        logging.info("--- Script de Prueba Finalizado ---")

    except Exception as e:
        logging.error(f"Error general durante la ejecución del script: {e}")

    finally:
        # Limpiar engines si fueron creados
        if engine_default:
            engine_default.dispose()
            logging.info(f"Engine para '{PG_DEFAULT_DBNAME}' cerrado.")
        if 'engine_target' in locals() and engine_target:
            engine_target.dispose()
            logging.info(f"Engine para '{PG_TARGET_DBNAME}' cerrado.")