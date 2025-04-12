"""
interface_adapters/controllers/pipeline_extract.py

Clases para cada etapa (step) del pipeline ETL, con posibilidad
de imprimir en consola, exportar a CSV opcionalmente,
y un paso final para almacenar datos en PostgreSQL.
"""

from typing import Any, Dict
import pandas as pd

from infrastructure.postgresql.pg_repository import PGRepository

class ETLStepInterface:
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError


class StoreDataInPostgresStep(ETLStepInterface):
    """
    Paso que toma datos (JSON o DataFrame) del context y los
    inserta en una tabla PostgreSQL usando PGRepository.

    Acciones:
    1) Verificar/crear la BD si no existe
    2) Verificar/crear la tabla si no existe
    3) Insertar los datos
    """

    def __init__(
            self,
            pg_repository: PGRepository,
            context_key: str,
            table_name: str,
            convert_json_to_df: bool = True,
            if_exists: str = "append"
    ):
        """
        :param pg_repository: instancia de PGRepository
        :param context_key: clave del context donde están los datos
        :param table_name: nombre de la tabla en PostgreSQL
        :param convert_json_to_df: si True, data es JSON y se convierte a DF;
                                   si False, asumimos data es DataFrame
        :param if_exists: "append", "replace", "fail"
        """
        self.pg_repository = pg_repository
        self.context_key = context_key
        self.table_name = table_name
        self.convert_json_to_df = convert_json_to_df
        self.if_exists = if_exists

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # 1. Verificar si hay data en el context
        data = context.get(self.context_key)
        if data is None:
            print(f"[StoreDataInPostgresStep] No hay datos en '{self.context_key}'.")
            return context

        # 2. Convertir a DataFrame si es JSON
        if self.convert_json_to_df:
            if isinstance(data, dict) and "value" in data:
                df = pd.DataFrame(data["value"])
            elif isinstance(data, dict):
                df = pd.DataFrame([data])
            else:
                df = pd.DataFrame(data)
        else:
            # asumimos data ya es DataFrame
            df = data

        if df.empty:
            print(f"[StoreDataInPostgresStep] DataFrame vacío, no guardamos en '{self.table_name}'.")
            return context

        # 3. Verificar / crear la BD si no existe
        self.pg_repository.create_database_if_not_exists()

        # 4. Verificar si la tabla existe; si no, crearla a partir del schema de df
        if not self.pg_repository.table_exists(self.table_name):
            # Crear la tabla con 0 filas (para el schema). Podrías usar df.head(0).
            print(f"[StoreDataInPostgresStep] La tabla '{self.table_name}' no existe. Creándola...")
            self.pg_repository.create_table_from_df(self.table_name, df.head(0))

        # 5. Insertar datos en la tabla
        # Usa if_exists según tu preferencia ("append", "replace", o "fail").
        self.pg_repository.insert_table(self.table_name, df, if_exists=self.if_exists)

        return context


class CheckPostgresConnectionStep(ETLStepInterface):
    """
    Step que simplemente verifica la conexión a PostgreSQL.
    """

    def __init__(self, pg_repository: PGRepository):
        self.pg_repository = pg_repository

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        print("[CheckPostgresConnectionStep] Verificando conexión a PostgreSQL...")
        self.pg_repository.check_connection()
        print("[CheckPostgresConnectionStep] Conexión verificada con éxito.")
        return context

