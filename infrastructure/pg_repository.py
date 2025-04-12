# infrastructure/postgresql/pg_repository.py

import pandas as pd
from infrastructure.postgresql.pg_client import SqlAlchemyClient

class PGRepository:
    """
    Repositorio que maneja la inserción de DataFrames en PostgreSQL
    usando SQLAlchemy + pandas.to_sql.
    """

    def __init__(self, sa_client: SqlAlchemyClient):
        self.sa_client = sa_client

    def save_dataframe(self, df: pd.DataFrame, table_name: str, if_exists: str = "append"):
        """
        Inserta el DataFrame en la tabla dada, usando pandas.to_sql.
        :param df: DataFrame a guardar
        :param table_name: nombre de la tabla en PostgreSQL
        :param if_exists: comportamiento si la tabla existe ("append", "replace", "fail")
        """
        if df.empty:
            print(f"[PGRepository] DataFrame vacío. Nada que insertar en {table_name}.")
            return

        engine = self.sa_client.get_engine()
        df.to_sql(
            name=table_name,
            con=engine,
            if_exists=if_exists,
            index=False
        )
        print(f"[PGRepository] Insertados {len(df)} registros en la tabla '{table_name}'.")
