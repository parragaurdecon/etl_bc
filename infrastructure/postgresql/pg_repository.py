# infrastructure/postgresql/pg_repository.py

import logging
import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from typing import Optional, List

from infrastructure.postgresql.pg_client import SqlAlchemyClient

class PGRepository:
    """
    Repositorio que maneja la creación/uso de la BD,
    la inserción de DataFrames en PostgreSQL usando SQLAlchemy + pandas.to_sql,
    y métodos auxiliares para consultar tablas.
    """

    def __init__(self, sa_client: SqlAlchemyClient):
        """
        :param sa_client: instancia de SqlAlchemyClient con .host, .port, .user, .password, .dbname
        """
        self.sa_client = sa_client
        self.engine: Optional[Engine] = None

    def check_connection(self) -> None:
        """
        Verifica la conexión a la base de datos realizando una consulta simple.
        Si hay problema de credenciales o DB inexistente, lanza excepción.
        """
        engine = self.sa_client.get_engine()
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT current_database();"))
                db_actual = result.scalar()
                logging.info(f"Conexión exitosa a la base de datos '{db_actual}'.")
        except SQLAlchemyError as e:
            logging.error(f"Error de conexión a PostgreSQL: {e}")
            raise
        except Exception as e:
            logging.error(f"Error inesperado al conectar a PostgreSQL: {e}")
            raise

    def create_database_if_not_exists(self) -> None:
        """
        Crea la base de datos si no existe, conectando temporalmente a la BD 'postgres'.
        """
        from sqlalchemy import create_engine, text

        dbname = self.sa_client.dbname
        user = self.sa_client.user
        password = self.sa_client.password
        host = self.sa_client.host
        port = self.sa_client.port

        default_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        try:
            temp_engine = create_engine(default_conn_str, isolation_level='AUTOCOMMIT')
            with temp_engine.connect() as conn:
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{dbname}'"))
                exists = result.scalar() is not None
                if not exists:
                    conn.execute(text(f"CREATE DATABASE {dbname}"))
                    logging.info(f"Base de datos PostgreSQL '{dbname}' creada.")
                else:
                    logging.info(f"La base de datos '{dbname}' ya existe.")
            temp_engine.dispose()
        except Exception as e:
            logging.error(f"Error creando/verificando la BD '{dbname}': {e}")
            raise

    def database_exists(self) -> bool:
        """
        Devuelve True/False si la BD existe, conectándose a 'postgres' para verificar.
        """
        from sqlalchemy import create_engine, text

        dbname = self.sa_client.dbname
        user = self.sa_client.user
        password = self.sa_client.password
        host = self.sa_client.host
        port = self.sa_client.port

        default_conn_str = f"postgresql://{user}:{password}@{host}:{port}/postgres"
        try:
            temp_engine = create_engine(default_conn_str, isolation_level='AUTOCOMMIT')
            with temp_engine.connect() as conn:
                result = conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname='{dbname}'"))
                exists = result.scalar() is not None
            temp_engine.dispose()
            return exists
        except Exception as e:
            logging.error(f"Error al verificar existencia de BD '{dbname}': {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """
        Verifica si la tabla existe en la BD principal.
        """
        engine = self.sa_client.get_engine()
        try:
            inspector = inspect(engine)
            return inspector.has_table(table_name)
        except SQLAlchemyError as e:
            logging.error(f"Error al verificar la tabla '{table_name}': {e}")
            raise

    def create_table_from_df(self, table_name: str, df: pd.DataFrame) -> None:
        """
        Crea la tabla según el schema del DataFrame (sin filas).
        Usa if_exists='fail', lanza error si ya existe.
        """
        if df.empty:
            logging.info(f"DataFrame vacío, no se crea la tabla '{table_name}'.")
            return
        engine = self.sa_client.get_engine()
        try:
            # Solo las columnas, sin insertar filas: df.head(0)
            df.head(0).to_sql(table_name, engine, if_exists='fail', index=False)
            logging.info(f"Tabla '{table_name}' creada a partir del schema del DataFrame.")
        except SQLAlchemyError as e:
            logging.error(f"Error al crear la tabla '{table_name}': {e}")
            raise

    def insert_table(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append') -> None:
        """
        Inserta un DataFrame en la tabla.
        :param table_name: Nombre de la tabla
        :param df: DataFrame a insertar
        :param if_exists: "append", "replace", "fail"
        """
        if df.empty:
            logging.info(f"DataFrame vacío, no se insertan datos en '{table_name}'.")
            return
        engine = self.sa_client.get_engine()
        try:
            df.to_sql(table_name, engine, if_exists=if_exists, index=False)
            logging.info(f"Insertados {len(df)} registros en '{table_name}' (if_exists='{if_exists}').")
        except SQLAlchemyError as e:
            logging.error(f"Error al insertar datos en '{table_name}': {e}")
            raise

    def save_dataframe(self, table_name: str, df: pd.DataFrame, if_exists: str = 'append') -> None:
        """
        Alias que:
         - si la tabla no existe, crea la estructura (df.head(0))
         - luego hace append de los datos
        """
        engine = self.sa_client.get_engine()
        if df.empty:
            logging.info(f"DataFrame vacío, nada que guardar en '{table_name}'.")
            return

        # Si no existe la tabla, la creamos con el schema
        if not self.table_exists(table_name):
            try:
                df.head(0).to_sql(table_name, engine, if_exists='fail', index=False)
                logging.info(f"Tabla '{table_name}' creada (schema) al no existir.")
            except SQLAlchemyError as e:
                logging.error(f"Error al crear la tabla '{table_name}': {e}")
                raise
        # Insertar filas
        try:
            df.to_sql(table_name, engine, if_exists='append', index=False)
            logging.info(f"Insertados {len(df)} registros en '{table_name}'.")
        except SQLAlchemyError as e:
            logging.error(f"Error insertando datos en '{table_name}': {e}")
            raise

    def close_connection(self) -> None:
        """
        Cierra la conexión de SqlAlchemyClient.
        """
        engine = self.sa_client.get_engine()
        try:
            engine.dispose()
            logging.info("Conexión a PostgreSQL cerrada correctamente.")
        except Exception as e:
            logging.error(f"Error al cerrar la conexión a PostgreSQL: {e}")
            raise
