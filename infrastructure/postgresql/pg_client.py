# infrastructure/postgresql/pg_client.py

import logging
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError # Para errores de conexión/engine
from typing import Optional

# Asumiendo que settings.py está en config/ y accesible
try:
    from config.settings import settings
except ImportError:
     logging.critical("Error CRÍTICO: No se pudo importar 'settings' desde config.settings en SqlAlchemyClient.")
     # Definir un objeto settings dummy para evitar NameErrors
     class DummySettings:
         PG_HOST=None; PG_DBNAME=None; PG_USER=None; PG_PASSWORD=None; PG_PORT=5432; PG_CONNECTION_STRING=None
     settings = DummySettings()

class SqlAlchemyClient:
    """
    Cliente que crea y gestiona el Engine de SQLAlchemy para PostgreSQL.
    Lee la configuración desde la instancia global 'settings'.
    Crea el engine bajo demanda y lo cachea.
    """

    def __init__(self):
        """
        Inicializa el cliente cargando la configuración desde 'settings'
        y validando los parámetros necesarios.
        NO crea el engine aquí, se crea bajo demanda.
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Inicializando SqlAlchemyClient...")

        # Cargar configuración desde la instancia settings
        self.host: Optional[str] = getattr(settings, 'PG_HOST', None)
        self.dbname: Optional[str] = getattr(settings, 'PG_DBNAME', None)
        self.user: Optional[str] = getattr(settings, 'PG_USER', None)
        self.password: Optional[str] = getattr(settings, 'PG_PASSWORD', None) # Puede ser None o ''
        self.port: Optional[int] = getattr(settings, 'PG_PORT', 5432) # Obtener el int directamente
        # Podríamos usar la connection string pre-construida o construirla aquí
        self.connection_string: Optional[str] = getattr(settings, 'PG_CONNECTION_STRING', None)

        # --- Validación de Configuración Esencial ---
        missing_configs = []
        if not self.host: missing_configs.append('PG_HOST')
        if not self.dbname: missing_configs.append('PG_DBNAME')
        if not self.user: missing_configs.append('PG_USER')
        # La contraseña puede ser opcional dependiendo de la autenticación PG (ej. trust)
        # if self.password is None: missing_configs.append('PG_PASSWORD')
        if self.port is None: missing_configs.append('PG_PORT')

        if missing_configs:
            msg = f"SqlAlchemyClient: Faltan configuraciones PostgreSQL esenciales: {', '.join(missing_configs)}"
            self.logger.error(msg)
            raise ValueError(msg)

        # Alternativa: Construir la cadena de conexión aquí si no viene de settings
        if not self.connection_string:
             user_part = self.user or "" # Asegurar que no sea None
             # Añadir ':' solo si hay contraseña
             password_part = f":{self.password}" if self.password else ""
             self.connection_string = (
                 f"postgresql+psycopg2://{user_part}{password_part}"
                 f"@{self.host}:{self.port}/{self.dbname}"
             )
             self.logger.debug("Cadena de conexión PostgreSQL construida internamente.")

        self._engine: Optional[Engine] = None # Cache para el engine (creado bajo demanda)
        self.logger.info("SqlAlchemyClient inicializado correctamente.")


    def _create_engine(self) -> Optional[Engine]:
        """
        Método privado para crear un NUEVO Engine de SQLAlchemy.
        Retorna el Engine o None si falla la creación.
        """
        self.logger.info(f"Creando nuevo engine SQLAlchemy para PostgreSQL: {self.user}@{self.host}:{self.port}/{self.dbname}")
        if not self.connection_string:
            self.logger.error("No se puede crear el engine: la cadena de conexión no está disponible.")
            return None
        try:
            # pool_size, max_overflow, etc., pueden configurarse aquí si es necesario
            # engine = create_engine(self.connection_string, pool_size=5, max_overflow=10)
            engine = create_engine(self.connection_string)
            # Podríamos hacer una prueba de conexión simple aquí, pero puede ralentizar
            # engine.connect().close()
            self.logger.info("Engine SQLAlchemy creado con éxito.")
            return engine
        except ImportError as imp_err:
             # Común si falta psycopg2
             self.logger.critical(f"Error de importación al crear engine (¿falta psycopg2?): {imp_err}", exc_info=True)
             raise ImportError("Driver DBAPI de PostgreSQL (psycopg2) no encontrado o no instalable.") from imp_err
        except SQLAlchemyError as db_err:
             # Errores al parsear URL, conectar inicialmente (depende del driver)
             self.logger.error(f"Error de SQLAlchemy al crear el engine para '{self.connection_string}': {db_err}", exc_info=True)
             return None # O relanzar si la creación fallida es crítica
        except Exception as e:
            self.logger.error(f"Error inesperado al crear el engine SQLAlchemy: {e}", exc_info=True)
            return None # O relanzar

    def get_engine(self) -> Engine:
        """
        Devuelve el engine SQLAlchemy cacheado. Si no existe, intenta crearlo.
        Lanza RuntimeError si no se puede crear/obtener el engine.
        """
        # Usar el engine cacheado si ya existe y está "vivo" (no desechado)
        # La comprobación de "vivo" es compleja, nos conformamos con la caché simple
        if self._engine is None:
            self.logger.debug("Engine no cacheado, intentando crear uno nuevo.")
            self._engine = self._create_engine() # Crear bajo demanda

        # Si después de intentar crear, sigue siendo None, lanzar error
        if self._engine is None:
             msg = "No se pudo crear o obtener el engine de SQLAlchemy."
             self.logger.critical(msg)
             raise RuntimeError(msg)

        # self.logger.debug("Devolviendo engine cacheado.")
        return self._engine

    def dispose_engine(self) -> None:
        """
        Desecha el pool de conexiones del engine si existe.
        Útil al final de la aplicación o en tests para liberar recursos.
        """
        if self._engine is not None:
            self.logger.info("Desechando el pool de conexiones del engine SQLAlchemy...")
            try:
                self._engine.dispose()
                self._engine = None # Resetear la caché
                self.logger.info("Pool de conexiones desechado.")
            except Exception as e:
                self.logger.error(f"Error al desechar el engine: {e}", exc_info=True)
        else:
            self.logger.debug("No hay engine cacheado para desechar.")