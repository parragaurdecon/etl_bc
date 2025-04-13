# infrastructure/postgresql/pg_repository.py

import logging
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError # Asegúrate que ProgrammingError está importado
from sqlalchemy.engine import Engine
from typing import Optional

from infrastructure.postgresql.pg_client import SqlAlchemyClient

class PGRepository:
    # ... (init, check_connection, create_database_if_not_exists, etc. sin cambios) ...
    def __init__(self, sa_client: SqlAlchemyClient):
        self.sa_client = sa_client
        # No engine como atributo

    def check_connection(self) -> None:
        engine = self.sa_client.get_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT current_database();"))
                db_actual = result.scalar()
                logging.info(f"Conexión exitosa a la base de datos '{db_actual}'.")
        # ... (manejo de errores como antes) ...
        except (SQLAlchemyError, ProgrammingError) as e:
            logging.error(f"Error de conexión a PostgreSQL: {e}")
            raise ConnectionError(f"No se pudo conectar a la BD: {e}") from e
        except Exception as e:
            logging.error(f"Error inesperado al conectar a PostgreSQL: {e}")
            raise ConnectionError(f"Error inesperado conectando a la BD: {e}") from e
        finally:
            if engine: engine.dispose()

    def create_database_if_not_exists(self) -> None:
        # ... (código como antes) ...
        dbname = self.sa_client.dbname
        user = self.sa_client.user
        password = self.sa_client.password
        host = self.sa_client.host
        port = self.sa_client.port
        default_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        temp_engine = None
        try:
            temp_engine = create_engine(default_conn_str, isolation_level='AUTOCOMMIT')
            with temp_engine.connect() as conn:
                query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
                result = conn.execute(query, {"dbname": dbname})
                exists = result.scalar() is not None
                if not exists:
                    logging.info(f"La base de datos '{dbname}' no existe. Creando...")
                    conn.execute(text(f'CREATE DATABASE "{dbname}"'))
                    logging.info(f"Base de datos PostgreSQL '{dbname}' creada.")
                else:
                    logging.info(f"La base de datos '{dbname}' ya existe.")
        # ... (manejo de errores como antes) ...
        except ProgrammingError as pe:
             logging.error(f"Error de permisos o sintaxis SQL al verificar/crear BD '{dbname}': {pe}")
             raise PermissionError(f"No se pudo crear/verificar la BD '{dbname}'. Verifica permisos.") from pe
        except SQLAlchemyError as e:
            logging.error(f"Error de base de datos al verificar/crear BD '{dbname}': {e}")
            raise ConnectionError(f"Error de BD al operar sobre '{dbname}': {e}") from e
        except Exception as e:
            logging.error(f"Error inesperado al verificar/crear BD '{dbname}': {e}")
            raise RuntimeError(f"Error inesperado con la BD '{dbname}': {e}") from e
        finally:
            if temp_engine: temp_engine.dispose()


    def database_exists(self) -> bool:
        # ... (código como antes) ...
        dbname = self.sa_client.dbname
        user = self.sa_client.user
        password = self.sa_client.password
        host = self.sa_client.host
        port = self.sa_client.port
        default_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        temp_engine = None
        try:
            temp_engine = create_engine(default_conn_str)
            with temp_engine.connect() as conn:
                query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
                result = conn.execute(query, {"dbname": dbname})
                exists = result.scalar() is not None
            return exists
        # ... (manejo de errores como antes) ...
        except (SQLAlchemyError, ProgrammingError) as e:
            logging.error(f"Error de base de datos al verificar existencia de BD '{dbname}': {e}")
            raise ConnectionError(f"Error de BD verificando '{dbname}'") from e
        except Exception as e:
            logging.error(f"Error inesperado al verificar existencia de BD '{dbname}': {e}")
            raise RuntimeError(f"Error inesperado verificando BD '{dbname}'") from e
        finally:
            if temp_engine: temp_engine.dispose()

    def table_exists(self, table_name: str) -> bool:
        # ... (código como antes) ...
        engine = self.sa_client.get_engine()
        try:
            inspector = inspect(engine)
            return inspector.has_table(table_name)
        # ... (manejo de errores como antes) ...
        except (SQLAlchemyError, ProgrammingError) as e:
            logging.error(f"Error al verificar la tabla '{table_name}': {e}")
            raise ConnectionError(f"Error de BD verificando tabla '{table_name}'") from e
        finally:
            if engine: engine.dispose()

    # --- create_table_from_df (Asegúrate que esta es la versión con COMMIT) ---
    def create_table_from_df(self, table_name: str, df: pd.DataFrame, primary_key: Optional[str] = None) -> None:
        """
        Crea la tabla según el schema del DataFrame. Lanza ValueError si df está vacío o PK no existe.
        Añade PK si se especifica.
        """
        # --- CORRECCIÓN: Lanzar error si el DF está vacío ---
        # (Esta validación ya estaba bien en tu código pegado)
        print('entrando en create table')
        print(df.columns)
        if df.empty:
            msg = f"DataFrame vacío proporcionado para crear tabla '{table_name}'. Se requiere un DataFrame con columnas."
            logging.error(msg)
            raise ValueError(msg)

        # Validar que la columna PK existe ANTES de crear
        if primary_key and primary_key not in df.columns:
             msg = f"Columna PK '{primary_key}' especificada no existe en DataFrame para tabla '{table_name}'."
             logging.error(msg)
             raise ValueError(msg)

        engine = self.sa_client.get_engine()
        conn = None
        try:
            # Paso 1: Crear la tabla usando df.head(0)
            logging.debug(f"Creando tabla '{table_name}' usando schema de df.head(0)...")
            # Es importante usar head(0) aquí para SÓLO crear la estructura
            df.head(0).to_sql(table_name, engine, if_exists='fail', index=False)
            logging.info(f"Tabla '{table_name}' creada (schema base).")

            # Paso 2: Añadir PK si se especificó
            if primary_key:
                logging.info(f"Añadiendo PRIMARY KEY en '{primary_key}' para tabla '{table_name}'...")
                constraint_name = f"{table_name}_{primary_key}_pk"
                sql_add_pk = text(
                    f'ALTER TABLE "{table_name}" ADD CONSTRAINT "{constraint_name}" PRIMARY KEY ("{primary_key}");'
                )
                conn = engine.connect()
                trans = conn.begin()
                try:
                    conn.execute(sql_add_pk)
                    trans.commit() # <<<--- COMMIT ES CLAVE
                    logging.info(f"PRIMARY KEY añadida en '{primary_key}' para tabla '{table_name}'.")
                except (SQLAlchemyError, ProgrammingError) as pk_err:
                    # ... (manejo de error, rollback, drop tabla como antes) ...
                    logging.error(f"Error al añadir PK a '{table_name}': {pk_err}")
                    try: trans.rollback()
                    except: pass
                    try:
                        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as cleanup_conn:
                            cleanup_conn.execute(text(f'DROP TABLE "{table_name}"'))
                            logging.info(f"Tabla '{table_name}' eliminada tras fallo de PK.")
                    except Exception as drop_err:
                        logging.error(f"Error al limpiar tabla '{table_name}': {drop_err}")
                    raise RuntimeError(f"Fallo al añadir PK a tabla '{table_name}'") from pk_err
                # No necesitamos finally conn.close() si usamos 'with conn:'

        # ... (manejo de excepciones ValueError, SQLAlchemyError, etc. como antes) ...
        except ValueError as ve:
             logging.error(f"Error de validación al crear tabla '{table_name}': {ve}")
             if "already exists" in str(ve): logging.warning(f"Tabla '{table_name}' ya existe.")
             else: raise
        except (SQLAlchemyError, ProgrammingError) as e:
            logging.error(f"Error de BD al crear tabla/PK '{table_name}': {e}")
            raise ConnectionError(f"Error de BD creando tabla/PK '{table_name}'") from e
        except Exception as e:
             logging.error(f"Error inesperado creando tabla/PK '{table_name}': {e}")
             raise RuntimeError(f"Error inesperado creando tabla/PK '{table_name}'") from e
        finally:
            if conn and not conn.closed: conn.close()
            if engine: engine.dispose()


    def insert_table(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append') -> None:
        print('entrando en insert table')
        print(df.columns)

        if df.empty:
            logging.info(f"DataFrame vacío, no se insertan datos en '{table_name}'.")
            return
        engine = self.sa_client.get_engine()
        try:
            logging.debug(f"Insertando {len(df)} filas en '{table_name}' (modo={if_exists})...")
            df.to_sql(table_name, engine, if_exists=if_exists, index=False, chunksize=1000)
            logging.info(f"Insertados {len(df)} registros en '{table_name}' (modo='{if_exists}').")
        # ... (manejo de errores como antes) ...
        except (SQLAlchemyError, ProgrammingError) as e:
            logging.error(f"Error de BD al insertar datos en '{table_name}': {e}")
            # from sqlalchemy.exc import IntegrityError # Importar si quieres ser específico
            # if isinstance(e, IntegrityError): logging.error(f"Detalle (IntegrityError): {e.orig}")
            raise ConnectionError(f"Error de BD insertando en '{table_name}'") from e
        except Exception as e:
             logging.error(f"Error inesperado insertando en '{table_name}': {e}")
             raise RuntimeError(f"Error inesperado insertando en '{table_name}'") from e
        finally:
             if engine: engine.dispose()

    # --- incremental_insert_table (CORREGIDO) ---
    def incremental_insert_table(
            self,
            table_name: str,
            df: pd.DataFrame, # DataFrame CON DATOS
            primary_key: str
    ) -> None:
        print('entrando en incremental table')
        print(df.columns)
        if df.empty:
            logging.info(f"[PGRepository] DataFrame vacío para {table_name}. No se inserta nada.")
            return

        try:
            if not self.table_exists(table_name):
                logging.info(f"Tabla '{table_name}' no existe. Creándola con PK en '{primary_key}'.")
                # --- CORRECCIÓN AQUÍ: Pasar 'df' COMPLETO ---
                # create_table_from_df necesita el df con datos para validar la columna PK
                # aunque internamente use head(0) para crear el schema.
                self.create_table_from_df(
                    table_name=table_name,
                    df=df, # <--- PASAR EL DATAFRAME ORIGINAL
                    primary_key=primary_key
                )
                # Ahora la tabla existe CON PK. Proceder a insertar datos únicos.
                logging.info(f"Realizando carga inicial en '{table_name}'. Verificando duplicados internos PK='{primary_key}'...")
                initial_rows = len(df)
                df_initial_load = df.drop_duplicates(subset=[primary_key], keep='first')
                final_rows = len(df_initial_load)
                if initial_rows != final_rows:
                     logging.warning(f"Se encontraron {initial_rows - final_rows} duplicados internos en DF para carga inicial de '{table_name}'.")

                if final_rows > 0:
                    self.insert_table(table_name, df_initial_load, if_exists='append')
                    logging.info(f"Carga inicial completada para '{table_name}' ({final_rows} filas únicas insertadas).")
                else:
                    logging.info(f"No hay filas únicas para la carga inicial de '{table_name}'.")
                return # Termina aquí

            # --- Lógica Incremental (Tabla ya existe) ---
            logging.info(f"Tabla '{table_name}' existe. Realizando inserción incremental PK='{primary_key}'.")
            # ... (Resto de la lógica incremental: validar PK en df, validar nulos,
            #      obtener existing_pks, filtrar df_incremental, insertar df_incremental) ...
            # (El código para esta parte ya parecía correcto en tu versión)
            if primary_key not in df.columns: raise ValueError(f"Columna PK '{primary_key}' no encontrada.")
            df_valid_pk = df.dropna(subset=[primary_key]).copy() if df[primary_key].isnull().any() else df.copy()
            if df_valid_pk.empty: logging.info(f"No hay filas con PK válida para {table_name}."); return

            engine_inc = self.sa_client.get_engine()
            try:
                with engine_inc.connect() as conn_inc:
                    query_pk = text(f'SELECT "{primary_key}" FROM "{table_name}"')
                    result = conn_inc.execute(query_pk)
                    existing_pks = set(row[0] for row in result)
            finally:
                if engine_inc: engine_inc.dispose()

            before_count = len(df_valid_pk)
            df_incremental = df_valid_pk[~df_valid_pk[primary_key].isin(existing_pks)].copy()
            after_count = len(df_incremental)

            if after_count == 0:
                logging.info(f"No hay filas nuevas para insertar en {table_name}.")
                return

            omitted_count = before_count - after_count
            logging.info(f"Insertando {after_count} filas nuevas en '{table_name}'. {omitted_count} omitidas.")
            self.insert_table(table_name, df_incremental, if_exists='append')


        except (ValueError, ConnectionError, SQLAlchemyError, RuntimeError, PermissionError, ProgrammingError) as e:
            logging.error(f"Error durante incremental_insert_table tabla '{table_name}' PK '{primary_key}': {e}")
            raise

    # ... (close_connection) ...
    def close_connection(self) -> None:
        logging.debug("Llamada a close_connection.")
        # No hay engine persistente que cerrar en esta versión
        pass