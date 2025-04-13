"""
interface_adapters/controllers/pipeline_store.py
(Versión Simplificada - Sin Lógica Incremental Explícita en el Step)
"""

import logging
from typing import Any, Dict, Optional
import pandas as pd

from infrastructure.postgresql.pg_repository import PGRepository

from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, IntegrityError

class ETLStepInterface:
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class StoreDataInPostgresStep(ETLStepInterface):
    """
    Paso ETL para almacenar datos de un DataFrame en una tabla PostgreSQL.

    Lógica Simplificada:
    1. Convierte los datos del contexto a DataFrame.
    2. Verifica/Crea la Base de Datos si no existe.
    3. Verifica si la tabla de destino existe.
    4. Si la tabla NO existe, la crea usando pg_repository.create_table_from_df
       (pasando la primary_key si está definida para que se cree la constraint PK).
    5. Si la tabla SÍ existe, simplemente loguea un mensaje.
    6. Llama a pg_repository.insert_table para añadir los datos del DataFrame actual.
       - Usa el modo 'if_exists' configurado (por defecto 'append').
       - ¡ATENCIÓN! Si se usa 'append' y la tabla tiene PK, fallará si
         el DataFrame contiene claves duplicadas (ya existentes o internas).
         Este step ya NO maneja lógica incremental para evitar duplicados.
    """
    def __init__(
        self,
        pg_repository: PGRepository,
        context_key: str,
        table_name: str,
        convert_json_to_df: bool = True,
        if_exists: str = "append", # Modo para pandas.to_sql ('append', 'replace', 'fail')
        primary_key: Optional[str] = None # PK para la CREACIÓN de la tabla
    ):
        """
        :param pg_repository: instancia de PGRepository
        :param context_key: clave del context donde están los datos
        :param table_name: nombre de la tabla en PostgreSQL
        :param convert_json_to_df: si True, convierte JSON a DF
        :param if_exists: Cómo actuar si la tabla existe al *insertar* ('append', 'replace', 'fail')
        :param primary_key: Columna a usar como PK *si la tabla se crea*. Si es None, se crea sin PK.
                            NOTA: Este step ya NO realiza inserción incremental inteligente.
        """
        self.pg_repository = pg_repository
        self.context_key = context_key
        self.table_name = table_name
        self.convert_json_to_df = convert_json_to_df
        self.if_exists = if_exists
        self.primary_key = primary_key
        self.logger = logging.getLogger(__name__) # Logger específico

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Almacenar en tabla '{self.table_name}' ---")
        data = context.get(self.context_key)
        if data is None:
            self.logger.warning(f"Context_key '{self.context_key}' no encontrado. Omitiendo step.")
            return context

        # Convertir a DataFrame
        df = self._to_dataframe(data)
        if df is None or df.empty:
            self.logger.error(f"DataFrame vacío o inválido para '{self.context_key}'. No se guardará en '{self.table_name}'.")
            return context # No continuar si no hay datos válidos

        self.logger.info(f"DataFrame para '{self.table_name}' (Shape: {df.shape}). Iniciando operaciones de BD.")

        try:
            # 1. Asegurar que la BD existe
            self.logger.info(f"Verificando/Creando base de datos '{self.pg_repository.sa_client.dbname}'...")
            self.pg_repository.create_database_if_not_exists()
            self.logger.info("Base de datos OK.")

            # 2. Verificar si la tabla existe y crearla si es necesario
            if not self.pg_repository.table_exists(self.table_name):
                self.logger.info(f"Tabla '{self.table_name}' no existe. Intentando crearla...")
                # Llamar a create_table_from_df. Pasar la PK si está definida.
                # Esta función lanzará error si df está vacío o la PK no existe en df.
                self.pg_repository.create_table_from_df(
                    table_name=self.table_name,
                    df=df, # Pasar DF con datos para validación
                    primary_key=self.primary_key # Pasar la PK definida (o None)
                )
                # Si create_table_from_df no lanzó error, la tabla fue creada (con o sin PK)
                self.logger.info(f"Tabla '{self.table_name}' creada exitosamente"
                                 f"{f' con PK en [{self.primary_key}]' if self.primary_key else ' (sin PK definida)'}.")
            else:
                self.logger.info(f"Tabla '{self.table_name}' ya existe. No se requiere creación.")

            # --- 3. Insertar los Datos ---
            # Ahora simplemente insertamos usando el modo if_exists configurado.
            # Ya no hay lógica incremental aquí.
            self.logger.info(f"Intentando insertar {len(df)} filas en tabla '{self.table_name}' usando modo '{self.if_exists}'...")

            # ANTES de insertar, si el modo es 'append' y hay PK, es buena idea quitar duplicados internos
            df_to_insert = df
            if self.if_exists == 'append' and self.primary_key and not df.empty:
                 initial_rows = len(df)
                 # Quitar duplicados INTERNOS del lote actual basado en la PK
                 df_to_insert = df.drop_duplicates(subset=[self.primary_key], keep='first')
                 final_rows = len(df_to_insert)
                 if initial_rows != final_rows:
                      self.logger.warning(f"Se eliminaron {initial_rows - final_rows} duplicados internos del lote actual "
                                         f"para tabla '{self.table_name}' antes de insertar.")
                 if df_to_insert.empty:
                      self.logger.info(f"Después de eliminar duplicados internos, no quedan filas para insertar en '{self.table_name}'.")
                      return context # No hay nada que insertar

            # Llamar a insert_table con el DataFrame (potencialmente sin duplicados internos)
            self.pg_repository.insert_table(
                table_name=self.table_name,
                df=df_to_insert,
                if_exists=self.if_exists # Usar el modo configurado
            )
            self.logger.info(f"Inserción en tabla '{self.table_name}' (modo='{self.if_exists}') completada.")


        except IntegrityError as ie:
             # Capturar específicamente errores de integridad (como violación de PK si se usa 'append')
             self.logger.error(f"Error de Integridad al insertar en tabla '{self.table_name}': {ie.orig}", exc_info=False) # No mostrar traceback largo por defecto
             self.logger.warning(f"Esto puede ocurrir si se usa 'append' en una tabla con PK y los datos entrantes "
                                f"contienen claves que ya existen O si if_exists='fail' y la tabla ya tiene datos.")
             # Decidir si relanzar o continuar
             raise RuntimeError(f"Fallo de integridad al procesar tabla '{self.table_name}'") from ie
        except (ConnectionError, ValueError, RuntimeError, PermissionError, SQLAlchemyError, ProgrammingError) as e:
            self.logger.error(f"Error de base de datos procesando tabla '{self.table_name}': {e}", exc_info=True)
            raise RuntimeError(f"Fallo al procesar tabla '{self.table_name}'") from e
        except Exception as e:
            self.logger.exception(f"Error inesperado procesando tabla '{self.table_name}': {e}")
            raise RuntimeError(f"Fallo inesperado procesando tabla '{self.table_name}'") from e

        self.logger.info(f"--- Step finalizado: Almacenar en tabla '{self.table_name}' ---")
        return context

    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        """Convierte varios tipos de datos a DataFrame. Devuelve DF vacío en error."""
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