# infrastructure/postgresql/pg_repository.py

import logging
import pandas as pd
from sqlalchemy import inspect, text, create_engine # Añadir create_engine aquí si se usa en C_DB_I_N_E
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, IntegrityError # Añadir IntegrityError
from sqlalchemy.engine import Engine
from typing import Optional, Set # Añadir Set

# Asumiendo cliente accesible
try:
    from infrastructure.postgresql.pg_client import SqlAlchemyClient
except ImportError as e:
     logging.critical(f"Error importando SqlAlchemyClient en PGRepository: {e}")
     SqlAlchemyClient = None

class PGRepository:
    """
    Repositorio PostgreSQL con logging y manejo de errores mejorado.
    Interactúa con SqlAlchemyClient para obtener engines.
    """

    def __init__(self, sa_client: SqlAlchemyClient):
        """
        Inicializa con una instancia de SqlAlchemyClient.

        :param sa_client: Cliente SQLAlchemy configurado.
        :raises TypeError: Si sa_client no es instancia de SqlAlchemyClient.
        """
        if SqlAlchemyClient is None: raise ImportError("Clase SqlAlchemyClient no importada.")
        if not isinstance(sa_client, SqlAlchemyClient): raise TypeError("sa_client debe ser instancia de SqlAlchemyClient.")
        self.sa_client = sa_client
        self.logger = logging.getLogger(__name__) # Logger específico
        self.logger.info("PGRepository inicializado.")

    # --- Métodos para obtener/desechar Engine (privados o no) ---
    # Es mejor obtener el engine justo cuando se necesita y desecharlo después
    # para evitar problemas de conexión obsoleta, especialmente con DDL.

    def _execute_ddl(self, sql_statement: str, operation_desc: str):
        """Helper para ejecutar DDL con manejo de errores y recursos."""
        engine = None
        conn = None
        try:
            engine = self.sa_client.get_engine() # Obtener engine fresco
            conn = engine.connect()
            # La transacción explícita es crucial para DDL en algunos contextos
            trans = conn.begin()
            try:
                 conn.execute(text(sql_statement)) # Usar text() aunque sea f-string por claridad
                 trans.commit()
                 self.logger.info(f"Operación DDL '{operation_desc}' ejecutada y confirmada con éxito.")
                 return True
            except (SQLAlchemyError, ProgrammingError) as e:
                 self.logger.error(f"Error ejecutando DDL '{operation_desc}': {e}")
                 try:
                      trans.rollback()
                      self.logger.info("Rollback realizado tras error DDL.")
                 except Exception as rb_err:
                      self.logger.error(f"Error durante rollback tras error DDL: {rb_err}")
                 # Relanzar el error original para que el llamador sepa
                 raise e from e # Relanza el error original (SQLAlchemyError o ProgrammingError)
        finally:
             if conn and not conn.closed: conn.close()
             if engine: engine.dispose() # Desechar engine después de la operación

    # --- Métodos Principales ---

    def check_connection(self) -> None:
        """Verifica la conexión a la base de datos."""
        self.logger.info(f"Verificando conexión a BD: {self.sa_client.dbname} en {self.sa_client.host}")
        engine = None
        try:
            engine = self.sa_client.get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT current_database();"))
                db_actual = result.scalar()
                self.logger.info(f"Conexión exitosa a la base de datos '{db_actual}'.")
        except (SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de conexión a PostgreSQL: {e}")
            raise ConnectionError(f"No se pudo conectar a la BD: {e}") from e
        except Exception as e:
            self.logger.error(f"Error inesperado al conectar a PostgreSQL: {e}")
            raise ConnectionError(f"Error inesperado conectando a la BD: {e}") from e
        finally:
            if engine: engine.dispose()

    def create_database_if_not_exists(self) -> None:
        """Crea la base de datos si no existe."""
        dbname = self.sa_client.dbname
        self.logger.info(f"Verificando/Creando base de datos '{dbname}'...")
        # Validar que tenemos todos los datos para conectar a 'postgres'
        if not all([self.sa_client.user, self.sa_client.host, self.sa_client.port]):
             msg = "Faltan datos (user/host/port) para conectar a la BD 'postgres' y verificar/crear."
             self.logger.error(msg)
             raise ValueError(msg)

        # Conectar a 'postgres'
        default_conn_str = (
            f"postgresql://{self.sa_client.user}:{self.sa_client.password or ''}"
            f"@{self.sa_client.host}:{self.sa_client.port}/postgres"
        )
        temp_engine = None
        try:
            temp_engine = create_engine(default_conn_str, isolation_level='AUTOCOMMIT')
            with temp_engine.connect() as conn:
                query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
                result = conn.execute(query, {"dbname": dbname})
                exists = result.scalar() is not None

                if not exists:
                    self.logger.info(f"Base de datos '{dbname}' no existe. Creando...")
                    # CREATE DATABASE no permite parámetros, asegurarse que dbname es 'seguro'
                    conn.execute(text(f'CREATE DATABASE "{dbname}"'))
                    self.logger.info(f"Base de datos '{dbname}' creada.")
                else:
                    self.logger.info(f"Base de datos '{dbname}' ya existe.")
        except ProgrammingError as pe:
             self.logger.error(f"Error de permisos/sintaxis SQL al verificar/crear BD '{dbname}': {pe}")
             raise PermissionError(f"No se pudo crear/verificar BD '{dbname}'. Verifica permisos.") from pe
        except SQLAlchemyError as e:
            self.logger.error(f"Error de BD al verificar/crear BD '{dbname}': {e}")
            raise ConnectionError(f"Error de BD operando sobre '{dbname}': {e}") from e
        except Exception as e:
            self.logger.error(f"Error inesperado al verificar/crear BD '{dbname}': {e}")
            raise RuntimeError(f"Error inesperado con BD '{dbname}': {e}") from e
        finally:
            if temp_engine: temp_engine.dispose()


    def database_exists(self) -> bool:
        """Devuelve True/False si la BD existe."""
        dbname = self.sa_client.dbname
        self.logger.info(f"Verificando existencia de BD '{dbname}'...")
        if not all([self.sa_client.user, self.sa_client.host, self.sa_client.port]):
            msg = "Faltan datos (user/host/port) para conectar a 'postgres' y verificar existencia de BD."
            self.logger.error(msg)
            raise ValueError(msg)

        default_conn_str = (
             f"postgresql://{self.sa_client.user}:{self.sa_client.password or ''}"
             f"@{self.sa_client.host}:{self.sa_client.port}/postgres"
        )
        temp_engine = None
        try:
            temp_engine = create_engine(default_conn_str)
            with temp_engine.connect() as conn:
                query = text("SELECT 1 FROM pg_database WHERE datname = :dbname")
                result = conn.execute(query, {"dbname": dbname})
                exists = result.scalar() is not None
            self.logger.info(f"BD '{dbname}' {'existe' if exists else 'no existe'}.")
            return exists
        except (SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de BD verificando existencia de BD '{dbname}': {e}")
            raise ConnectionError(f"Error de BD verificando '{dbname}'") from e
        except Exception as e:
            self.logger.error(f"Error inesperado verificando existencia de BD '{dbname}': {e}")
            raise RuntimeError(f"Error inesperado verificando BD '{dbname}'") from e
        finally:
            if temp_engine: temp_engine.dispose()

    def table_exists(self, table_name: str) -> bool:
        """Verifica si la tabla existe en la BD principal."""
        self.logger.info(f"Verificando existencia de tabla '{table_name}'...")
        engine = None
        try:
            engine = self.sa_client.get_engine()
            inspector = inspect(engine)
            exists = inspector.has_table(table_name)
            self.logger.info(f"Tabla '{table_name}' {'existe' if exists else 'no existe'}.")
            return exists
        except (SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de BD verificando tabla '{table_name}': {e}")
            raise ConnectionError(f"Error de BD verificando tabla '{table_name}'") from e
        except Exception as e:
             self.logger.error(f"Error inesperado verificando tabla '{table_name}': {e}")
             raise RuntimeError(f"Error inesperado verificando tabla '{table_name}'") from e
        finally:
            if engine: engine.dispose()

    def create_table_from_df(self, table_name: str, df: pd.DataFrame, primary_key: Optional[str] = None) -> None:
        """
        Crea tabla según schema de df. Lanza error si df vacío o PK no válida. Añade PK si se especifica.
        """
        self.logger.info(f"Intentando crear tabla '{table_name}'"
                         f"{f' con PK en [{primary_key}]' if primary_key else ' (sin PK)'}...")
        if df.empty:
            msg = f"DataFrame vacío proporcionado para crear tabla '{table_name}'."
            self.logger.error(msg)
            raise ValueError(msg)
        if primary_key and primary_key not in df.columns:
             msg = f"Columna PK '{primary_key}' no existe en DataFrame para tabla '{table_name}'."
             self.logger.error(msg)
             raise ValueError(msg)

        engine = None
        try:
            engine = self.sa_client.get_engine()
            # Paso 1: Crear tabla usando df.head(0)
            self.logger.debug(f"Ejecutando df.head(0).to_sql para '{table_name}'...")
            df.head(0).to_sql(table_name, engine, if_exists='fail', index=False)
            self.logger.info(f"Tabla '{table_name}' creada (schema base).")

            # Paso 2: Añadir PK si se especificó
            if primary_key:
                self.logger.info(f"Añadiendo constraint PRIMARY KEY en '{primary_key}'...")
                constraint_name = f"{table_name}_{primary_key}_pk"
                # Usar helper _execute_ddl para manejar transacción y errores
                sql_add_pk = (
                    f'ALTER TABLE "{table_name}" '
                    f'ADD CONSTRAINT "{constraint_name}" PRIMARY KEY ("{primary_key}");'
                )
                # _execute_ddl ya maneja commit/rollback/logging/dispose
                try:
                    self._execute_ddl(sql_add_pk, f"ADD PRIMARY KEY a {table_name}")
                    self.logger.info(f"PRIMARY KEY añadida exitosamente para '{table_name}'.")
                except (SQLAlchemyError, ProgrammingError) as pk_err:
                    # Si falla añadir PK, intentamos limpiar la tabla creada
                    self.logger.error(f"Fallo al añadir PK a '{table_name}'. Intentando eliminar tabla...")
                    try:
                         # Necesitamos DDL con autocommit para DROP
                         sql_drop = f'DROP TABLE "{table_name}";'
                         # Podríamos crear un helper _execute_ddl_autocommit o hacerlo aquí
                         drop_engine = self.sa_client.get_engine()
                         try:
                              with drop_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as drop_conn:
                                   drop_conn.execute(text(sql_drop))
                              self.logger.info(f"Tabla '{table_name}' eliminada tras fallo de PK.")
                         finally:
                              if drop_engine: drop_engine.dispose()
                    except Exception as drop_err:
                         self.logger.error(f"Error adicional al intentar eliminar tabla '{table_name}' tras fallo de PK: {drop_err}")
                    # Relanzar el error original de la PK
                    raise RuntimeError(f"Fallo al añadir PK a tabla '{table_name}'") from pk_err

        except ValueError as ve:
             # Error de validación (DF vacío, PK no existe) o tabla ya existe
             self.logger.error(f"Error de validación/existencia al crear tabla '{table_name}': {ve}")
             if "already exists" in str(ve):
                 self.logger.warning(f"Tabla '{table_name}' ya existía, no se creó de nuevo.")
                 # Podríamos retornar aquí si no es un error fatal
             else:
                 raise # Relanzar otros ValueErrors
        except (SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de BD al crear tabla '{table_name}': {e}", exc_info=True)
            raise ConnectionError(f"Error de BD creando tabla '{table_name}'") from e
        except Exception as e:
             self.logger.error(f"Error inesperado creando tabla '{table_name}': {e}", exc_info=True)
             raise RuntimeError(f"Error inesperado creando tabla '{table_name}'") from e
        finally:
            # Asegurar que el engine principal obtenido al inicio se deseche
            if engine: engine.dispose()


    def insert_table(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append') -> None:
        """Inserta un DataFrame en la tabla."""
        self.logger.info(f"Intentando insertar {len(df)} filas en tabla '{table_name}' (modo={if_exists})...")
        if df.empty:
            self.logger.warning(f"DataFrame vacío, no se insertan datos en '{table_name}'.")
            return

        engine = None
        try:
            engine = self.sa_client.get_engine()
            self.logger.debug(f"Ejecutando df.to_sql para '{table_name}'...")
            # Usar chunksize para cargas grandes
            df.to_sql(table_name, engine, if_exists=if_exists, index=False, chunksize=1000, method='multi')
            self.logger.info(f"Insertados {len(df)} registros en '{table_name}' (modo='{if_exists}').")
        except IntegrityError as ie:
             # Error específico de violación de constraint (PK, FK, Unique)
             self.logger.error(f"Error de integridad al insertar en '{table_name}': {ie.orig}", exc_info=False) # Mostrar error original de DB
             # No relanzar como ConnectionError, sino como un error de datos/integridad
             raise ValueError(f"Violación de constraint al insertar en '{table_name}'") from ie
        except (SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de BD al insertar datos en '{table_name}': {e}", exc_info=True)
            raise ConnectionError(f"Error de BD insertando en '{table_name}'") from e
        except Exception as e:
             self.logger.error(f"Error inesperado insertando en '{table_name}': {e}", exc_info=True)
             raise RuntimeError(f"Error inesperado insertando en '{table_name}'") from e
        finally:
             if engine: engine.dispose()


    def incremental_insert_table(
            self,
            table_name: str,
            df: pd.DataFrame,
            primary_key: str
    ) -> None:
        """
        Inserta filas incrementalmente. Crea tabla con PK si no existe.
        Maneja duplicados en la carga inicial y filtra vs existentes.
        """
        self.logger.info(f"Iniciando inserción incremental para tabla '{table_name}' (PK='{primary_key}')...")
        if df.empty:
            self.logger.warning(f"DataFrame vacío proporcionado para inserción incremental en '{table_name}'.")
            return

        engine = None # Para operaciones de consulta PK
        try:
            # 1) Crear tabla si no existe (con PK) e insertar datos únicos iniciales
            if not self.table_exists(table_name):
                self.logger.info(f"Tabla '{table_name}' no existe. Procediendo con creación y carga inicial...")
                # create_table_from_df lanza error si df vacío o PK inválida
                self.create_table_from_df(table_name=table_name, df=df, primary_key=primary_key)

                # Preparar carga inicial (sin duplicados internos)
                self.logger.info(f"Preparando carga inicial para '{table_name}' (eliminando duplicados internos)...")
                initial_rows = len(df)
                df_initial_load = df.drop_duplicates(subset=[primary_key], keep='first')
                final_rows = len(df_initial_load)
                if initial_rows != final_rows:
                     self.logger.warning(f"Carga inicial '{table_name}': Eliminados {initial_rows - final_rows} duplicados internos.")

                # Insertar
                if final_rows > 0:
                    self.insert_table(table_name, df_initial_load, if_exists='append') # insert_table loguea éxito
                    self.logger.info(f"Carga inicial completada para '{table_name}'.")
                else:
                    self.logger.info(f"Carga inicial '{table_name}': No quedaron filas tras eliminar duplicados.")
                return # Termina aquí

            # 2) Lógica Incremental (Tabla ya existe)
            self.logger.info(f"Tabla '{table_name}' existe. Realizando filtrado incremental...")

            # Validaciones del DataFrame de entrada
            if primary_key not in df.columns:
                 msg = f"Columna PK '{primary_key}' no encontrada en DataFrame para tabla '{table_name}'."
                 self.logger.error(msg)
                 raise ValueError(msg)
            if df[primary_key].isnull().any():
                 self.logger.warning(f"DataFrame para tabla '{table_name}' contiene nulos en PK '{primary_key}'. Se excluirán.")
                 df_valid_pk = df.dropna(subset=[primary_key]).copy()
                 if df_valid_pk.empty:
                      self.logger.info(f"No hay filas con PK válida en DataFrame para '{table_name}'. Nada que insertar.")
                      return
            else:
                 df_valid_pk = df.copy()

            # Obtener PKs existentes
            existing_pks: Set = set()
            engine = self.sa_client.get_engine()
            try:
                self.logger.debug(f"Consultando PKs existentes en '{table_name}'...")
                with engine.connect() as conn:
                    query_pk = text(f'SELECT "{primary_key}" FROM "{table_name}"')
                    result = conn.execute(query_pk)
                    existing_pks = set(row[0] for row in result)
                self.logger.debug(f"Se encontraron {len(existing_pks)} PKs existentes en '{table_name}'.")
            except (SQLAlchemyError, ProgrammingError) as e:
                 self.logger.error(f"Error obteniendo PKs existentes de '{table_name}': {e}", exc_info=True)
                 raise ConnectionError(f"Fallo al consultar PKs existentes en '{table_name}'") from e
            finally:
                 if engine: engine.dispose() # Desechar engine usado para SELECT

            # Filtrar DataFrame para obtener filas nuevas
            before_count = len(df_valid_pk)
            df_incremental = df_valid_pk[~df_valid_pk[primary_key].isin(existing_pks)].copy()
            after_count = len(df_incremental)

            if after_count == 0:
                self.logger.info(f"No hay filas nuevas para insertar en '{table_name}' (comparado con {len(existing_pks)} existentes).")
                return

            # Insertar filas nuevas
            omitted_count = before_count - after_count
            self.logger.info(f"Se insertarán {after_count} filas nuevas en '{table_name}'. {omitted_count} filas ya existían o tenían PK nula.")
            # Llamar a insert_table para la inserción final
            self.insert_table(table_name, df_incremental, if_exists='append')
            self.logger.info(f"Inserción incremental en '{table_name}' completada.")

        except (ValueError, ConnectionError, SQLAlchemyError, RuntimeError, PermissionError, ProgrammingError, IntegrityError) as e:
            # Capturar todos los errores posibles de los sub-métodos o de esta lógica
            self.logger.error(f"Error general durante incremental_insert_table para tabla '{table_name}' PK '{primary_key}': {e}", exc_info=True)
            # Relanzar para indicar fallo en el step
            raise RuntimeError(f"Fallo en inserción incremental para tabla '{table_name}'") from e
        # No necesitamos finally aquí si los engines se desechan internamente


    def close_connection(self) -> None:
        """Intenta desechar el engine cacheado en el cliente (si existe)."""
        # Esta función ahora debería llamar al cliente si queremos cerrar el pool global
        self.logger.debug("Llamada a PGRepository.close_connection(). Delegando a sa_client.dispose_engine().")
        try:
             self.sa_client.dispose_engine()
        except Exception as e:
             self.logger.warning(f"Error al intentar desechar engine via sa_client: {e}", exc_info=False)