"""
interface_adapters/controllers/pipeline_store.py
(Versión MUY Simplificada: Crear y Cargar UNA VEZ si no existe)
"""

import logging
from typing import Any, Dict, Optional
import pandas as pd
from infrastructure.postgresql.pg_repository import PGRepository
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, IntegrityError

# Configuración de logging (si no se hace en main.py)
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s')

class ETLStepInterface:
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class StoreDataInPostgresStep(ETLStepInterface):
    """
    Paso ETL para almacenar datos en PostgreSQL:
    - Crea la tabla CON PK (si primary_key se define) si NO existe.
    - Inserta los datos del DataFrame actual SÓLO si la tabla fue recién creada.
    - Si la tabla YA EXISTE, no hace NADA.
    """
    def __init__(
        self,
        pg_repository: PGRepository,
        context_key: str,
        table_name: str,
        convert_json_to_df: bool = True,
        # 'if_exists' ya no es relevante para esta lógica simplificada
        primary_key: Optional[str] = None # PK para la CREACIÓN
    ):
        """
        :param primary_key: Columna a usar como PK *si la tabla se crea*.
        """
        self.pg_repository = pg_repository
        self.context_key = context_key
        self.table_name = table_name
        self.convert_json_to_df = convert_json_to_df
        # self.if_exists = if_exists # Ya no se usa en esta lógica
        self.primary_key = primary_key
        self.logger = logging.getLogger(__name__)

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Almacenar UNA VEZ en tabla '{self.table_name}' ---")
        data = context.get(self.context_key)
        if data is None:
            self.logger.warning(f"Context_key '{self.context_key}' no encontrado. Omitiendo step.")
            return context

        # Convertir a DataFrame
        df = self._to_dataframe(data)
        if df is None or df.empty:
            self.logger.error(f"DataFrame vacío o inválido para '{self.context_key}'. No se procesará tabla '{self.table_name}'.")
            return context

        self.logger.info(f"DataFrame para '{self.table_name}' (Shape: {df.shape}). Verificando tabla...")

        try:
            # 1. Asegurar que la BD existe
            self.logger.debug(f"Verificando/Creando base de datos '{self.pg_repository.sa_client.dbname}'...")
            self.pg_repository.create_database_if_not_exists()
            self.logger.debug("Base de datos OK.")

            # --- LÓGICA SIMPLIFICADA ---
            if not self.pg_repository.table_exists(self.table_name):
                # La tabla NO existe: Crear E Insertar Datos Iniciales
                self.logger.info(f"Tabla '{self.table_name}' no existe. Creando e insertando datos iniciales...")

                # 1. Crear tabla (con PK si se especificó)
                # Esta función lanza error si df vacío o PK no existe en df.
                self.logger.debug(f"Llamando a create_table_from_df para '{self.table_name}'...")
                self.pg_repository.create_table_from_df(
                    table_name=self.table_name,
                    df=df, # Pasar df completo para validaciones
                    primary_key=self.primary_key
                )
                self.logger.info(f"Tabla '{self.table_name}' creada exitosamente"
                                 f"{f' con PK en [{self.primary_key}]' if self.primary_key else ' (sin PK definida)'}.")

                # 2. Insertar datos iniciales (manejando duplicados internos SI hay PK)
                df_to_insert = df
                if self.primary_key:
                    self.logger.info(f"Preparando carga inicial para '{self.table_name}', eliminando duplicados internos (PK='{self.primary_key}')...")
                    initial_rows = len(df)
                    df_to_insert = df.drop_duplicates(subset=[self.primary_key], keep='first')
                    final_rows = len(df_to_insert)
                    if initial_rows != final_rows:
                        self.logger.warning(f"Se eliminaron {initial_rows - final_rows} duplicados internos del lote inicial para '{self.table_name}'.")

                if not df_to_insert.empty:
                    self.logger.info(f"Insertando {len(df_to_insert)} filas únicas iniciales en '{self.table_name}'...")
                    # Usamos 'append' porque la tabla está garantizado que está vacía aquí
                    self.pg_repository.insert_table(
                        table_name=self.table_name,
                        df=df_to_insert,
                        if_exists='append'
                    )
                    self.logger.info(f"Carga inicial en '{self.table_name}' completada.")
                else:
                    self.logger.warning(f"No quedaron filas para la carga inicial de '{self.table_name}' después de eliminar duplicados.")

            else:
                # La tabla YA existe: No hacer nada
                self.logger.info(f"Tabla '{self.table_name}' ya existe. No se realiza ninguna acción.")

        # --- Manejo de Excepciones ---
        except (ConnectionError, ValueError, RuntimeError, PermissionError, SQLAlchemyError, ProgrammingError, IntegrityError) as e:
             # Capturar todos los errores esperados del repositorio o BD
             self.logger.error(f"Error de base de datos procesando tabla '{self.table_name}': {e}", exc_info=True)
             # Relanzar para detener el pipeline si ocurre un error en la creación/inserción inicial
             raise RuntimeError(f"Fallo al procesar tabla '{self.table_name}'") from e
        except Exception as e:
            # Capturar cualquier otro error inesperado
            self.logger.exception(f"Error inesperado procesando tabla '{self.table_name}': {e}")
            raise RuntimeError(f"Fallo inesperado procesando tabla '{self.table_name}'") from e

        self.logger.info(f"--- Step finalizado: Almacenar UNA VEZ en tabla '{self.table_name}' ---")
        return context

    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        # ... (mantener igual, devuelve DF vacío en error) ...
        self.logger.debug(f"Intentando convertir datos de tipo '{type(data)}' a DataFrame para tabla '{self.table_name}'.")
        df = pd.DataFrame()
        try:
            if isinstance(data, pd.DataFrame): df = data
            elif isinstance(data, list): df = pd.DataFrame(data) if data else df
            elif isinstance(data, dict) and "value" in data and isinstance(data["value"], list):
                 df = pd.DataFrame(data["value"]) if data["value"] else df
            elif isinstance(data, dict): df = pd.DataFrame([data])
            else:
                 self.logger.warning(f"Tipo inesperado '{type(data)}' para tabla '{self.table_name}'. Intentando conversión.")
                 df = pd.DataFrame(data)
            if df.empty: self.logger.debug(f"Conversión resultó en DataFrame vacío para '{self.table_name}'.")
            else: self.logger.debug(f"Conversión exitosa para '{self.table_name}'. Shape: {df.shape}")
            return df
        except Exception as e:
             self.logger.error(f"Fallo al convertir datos a DataFrame para '{self.table_name}': {e}", exc_info=True)
             return df # Devuelve DF vacío


class CheckPostgresConnectionStep(ETLStepInterface):
    # ... (sin cambios, mantener el logger si quieres) ...
    def __init__(self, pg_repository: PGRepository):
        self.pg_repository = pg_repository
        self.logger = logging.getLogger(__name__)
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Verificando conexión a PostgreSQL...")
        try:
            self.pg_repository.check_connection()
            self.logger.info("Conexión verificada con éxito.")
        except ConnectionError as e:
             self.logger.error(f"Fallo de conexión a PostgreSQL: {e}", exc_info=True)
             raise RuntimeError("Fallo de conexión a PostgreSQL, pipeline detenido.") from e
        return context