"""
interface_adapters/controllers/pipeline_store.py
(Versión Corregida con importación correcta de Interfaz)
"""

import logging
from typing import Any, Dict, Optional
import pandas as pd

# --- Importar Dependencias ---
# Asumiendo que PGRepository está accesible
try:
    from infrastructure.postgresql.pg_repository import PGRepository
except ImportError as e:
     logging.error(f"Error importando PGRepository: {e}. Asegúrate de que la ruta es correcta.")
     PGRepository = None # Placeholder

# Importar excepciones de SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError, IntegrityError

# --- Importar la Interfaz Base ---
# Asume que etl_controller.py está en el mismo directorio (paquete) controllers
try:
    from .etl_controller import ETLStepInterface
except ImportError:
    logging.critical("Error crítico: No se pudo importar ETLStepInterface desde .etl_controller.")
    # Definir un placeholder para evitar más errores de carga,
    # pero indica un problema estructural o de PYTHONPATH.
    class ETLStepInterface:
        def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
            logging.error("ETLStepInterface no fue importada correctamente!")
            raise NotImplementedError("Interfaz base no cargada")
# ---------------------------------------------------


class StoreDataInPostgresStep(ETLStepInterface): # HEREDA de la interfaz importada
    """
    Paso ETL para almacenar datos en PostgreSQL.
    - Si se define una primary_key, usa la lógica incremental del repositorio
      (que crea tabla con PK si no existe e inserta solo datos nuevos si ya existe).
    - Si primary_key es None, crea la tabla sin PK si no existe y luego inserta
      según el modo 'if_exists'.
    """
    def __init__(
        self,
        pg_repository: PGRepository, # Tipo esperado PGRepository
        context_key: str,
        table_name: str,
        convert_json_to_df: bool = True,
        if_exists: str = "append", # Usado solo si primary_key es None
        primary_key: Optional[str] = "id" # Clave para modo incremental Y creación
    ):
        """
        :param pg_repository: instancia de PGRepository
        :param context_key: clave del context donde están los datos
        :param table_name: nombre de la tabla en PostgreSQL
        :param convert_json_to_df: si True, convierte JSON a DF
        :param if_exists: Cómo actuar si la tabla existe al *insertar* en modo NO incremental ('append', 'replace', 'fail')
        :param primary_key: Columna PK. Si se define, activa el modo incremental. Si es None, modo normal.
        """
        # Validar dependencias
        if PGRepository is None:
             raise ImportError("Clase PGRepository no importada correctamente.")
        if not isinstance(pg_repository, PGRepository):
             raise TypeError("pg_repository debe ser una instancia de PGRepository.")

        self.pg_repository = pg_repository
        self.context_key = context_key
        self.table_name = table_name
        self.convert_json_to_df = convert_json_to_df
        self.if_exists = if_exists
        self.primary_key = primary_key
        self.logger = logging.getLogger(__name__) # Logger específico para la instancia

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info(f"--- Iniciando Step: Almacenar en tabla '{self.table_name}' ---")
        data = context.get(self.context_key)
        if data is None:
            self.logger.warning(f"Context_key '{self.context_key}' no encontrado en el contexto. Omitiendo step.")
            return context

        # Convertir a DataFrame
        df = self._to_dataframe(data)
        # _to_dataframe ahora devuelve DF vacío en error/vacío, verificar eso
        if df is None or df.empty:
            self.logger.error(f"DataFrame vacío o inválido obtenido de '{self.context_key}'. No se guardará en tabla '{self.table_name}'.")
            return context # No continuar si no hay datos válidos

        self.logger.info(f"DataFrame para '{self.table_name}' (Shape: {df.shape}). Iniciando operaciones de BD.")

        try:
            # 1. Asegurar que la BD existe (puede lanzar ConnectionError)
            self.logger.debug(f"Verificando/Creando base de datos '{self.pg_repository.sa_client.dbname}'...")
            self.pg_repository.create_database_if_not_exists()
            self.logger.debug("Base de datos OK.")

            # --- Lógica Principal: Incremental vs No Incremental ---
            if self.primary_key:
                # MODO INCREMENTAL: Dejar que incremental_insert_table maneje todo.
                self.logger.info(f"Ejecutando inserción INCREMENTAL (PK='{self.primary_key}') en tabla '{self.table_name}'.")
                # Esta función maneja internamente:
                # - Comprobar si tabla existe
                # - Llamar a create_table_from_df (con PK) si no existe
                # - Insertar datos únicos iniciales (drop_duplicates) si se creó
                # - O filtrar vs existentes e insertar nuevos si ya existía
                self.pg_repository.incremental_insert_table(
                    table_name=self.table_name,
                    df=df,
                    primary_key=self.primary_key
                )
                # Los logs detallados de creación/inserción vendrán del repositorio
                self.logger.info(f"Proceso incremental para '{self.table_name}' finalizado.")
            else:
                # MODO NO INCREMENTAL: Gestionar creación aquí, luego insertar normal.
                self.logger.info(f"Ejecutando inserción NO incremental (modo='{self.if_exists}') en tabla '{self.table_name}'.")
                # Crear tabla explícitamente SIN PK si no existe
                if not self.pg_repository.table_exists(self.table_name):
                     self.logger.info(f"La tabla '{self.table_name}' no existe. Creándola (sin PK)...")
                     # create_table_from_df lanza error si df está vacío o PK (si se pasara) no existe
                     self.pg_repository.create_table_from_df(
                         table_name=self.table_name,
                         df=df, # Pasar df completo para validación de schema
                         primary_key=None # Sin PK explícitamente
                     )
                     self.logger.info(f"Tabla '{self.table_name}' creada (sin PK).")
                else:
                     self.logger.info(f"Tabla '{self.table_name}' ya existe.")

                # Insertar datos usando if_exists configurado
                self.logger.info(f"Insertando datos en '{self.table_name}' (modo='{self.if_exists}')...")
                # No se necesitan duplicados aquí ya que no hay PK que proteger en este flujo
                self.pg_repository.insert_table(
                    table_name=self.table_name,
                    df=df, # Insertar el DF completo recibido
                    if_exists=self.if_exists
                )
                self.logger.info(f"Inserción NO incremental para '{self.table_name}' completada.")

        # --- Manejo de Excepciones ---
        except (ConnectionError, ValueError, RuntimeError, PermissionError, SQLAlchemyError, ProgrammingError, IntegrityError) as e:
             # Capturar todos los errores esperados del repositorio o BD
             self.logger.error(f"Error de base de datos procesando tabla '{self.table_name}': {e}", exc_info=True) # Loguear traceback
             # Relanzar para detener el pipeline
             raise RuntimeError(f"Fallo al procesar tabla '{self.table_name}'") from e
        except Exception as e:
            # Capturar cualquier otro error inesperado
            self.logger.exception(f"Error inesperado procesando tabla '{self.table_name}': {e}") # .exception loguea traceback
            raise RuntimeError(f"Fallo inesperado procesando tabla '{self.table_name}'") from e

        self.logger.info(f"--- Step finalizado: Almacenar en tabla '{self.table_name}' ---")
        return context

    def _to_dataframe(self, data: Any) -> pd.DataFrame:
        """Convierte varios tipos de datos a DataFrame. Devuelve DF vacío en error."""
        self.logger.debug(f"Intentando convertir datos de tipo '{type(data)}' a DataFrame para tabla '{self.table_name}'.")
        df = pd.DataFrame()
        try:
            if isinstance(data, pd.DataFrame):
                df = data
            elif isinstance(data, list):
                 df = pd.DataFrame(data) if data else df
            elif isinstance(data, dict) and "value" in data and isinstance(data["value"], list):
                 # Caso común OData
                 df = pd.DataFrame(data["value"]) if data["value"] else df
            elif isinstance(data, dict):
                # Diccionario simple, convertir a DF de una fila
                df = pd.DataFrame([data])
            else:
                 self.logger.warning(f"Tipo inesperado '{type(data)}' encontrado para tabla '{self.table_name}'. Se intentará conversión genérica.")
                 # Puede fallar o dar resultados inesperados
                 df = pd.DataFrame(data)

            if not isinstance(df, pd.DataFrame):
                 # Si la conversión falla y devuelve otra cosa
                 self.logger.error(f"La conversión de datos para '{self.table_name}' no resultó en un DataFrame (tipo: {type(df)}).")
                 return pd.DataFrame() # Devolver vacío

            if df.empty:
                 self.logger.debug(f"Conversión resultó en DataFrame vacío para '{self.table_name}'.")
            else:
                 self.logger.debug(f"Conversión exitosa para '{self.table_name}'. Shape: {df.shape}, Columnas: {df.columns.tolist()}")
            return df
        except Exception as e:
             self.logger.error(f"Fallo crítico al convertir datos a DataFrame para '{self.table_name}': {e}", exc_info=True)
             return pd.DataFrame() # Devuelve DF vacío


class CheckPostgresConnectionStep(ETLStepInterface): # HEREDA
    """
    Step que simplemente verifica la conexión a PostgreSQL.
    """
    def __init__(self, pg_repository: PGRepository):
        if PGRepository is None: raise ImportError("Clase PGRepository no importada.")
        if not isinstance(pg_repository, PGRepository): raise TypeError("pg_repository debe ser instancia de PGRepository.")
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