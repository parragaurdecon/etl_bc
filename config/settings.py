# config/settings.py

"""
config/settings.py
Lee credenciales desde variables de entorno (.env) y configuración adicional
desde un archivo YAML (config.yaml).
"""
import os
import logging
import yaml # Necesitarás: pip install PyYAML
from dotenv import load_dotenv
from typing import Optional, List, Dict, Any, Set

# Cargar variables de entorno desde .env al inicio
load_dotenv()

# Configurar un logger básico para este módulo (opcional pero útil)
logger = logging.getLogger(__name__)

# --- Ubicación del Archivo YAML ---
# Asume que config.yaml está en el MISMO directorio que este settings.py
# Ajusta la ruta si está en otro lugar (p.ej., raíz del proyecto)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # Raíz del proyecto (si settings está en config/)
# CONFIG_YAML_PATH = os.path.join(BASE_DIR, 'config.yaml')
CONFIG_YAML_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')

class Settings:
    """
    Clase Singleton (por instancia global 'settings') para acceder a la configuración.
    Lee de variables de entorno y de config.yaml.
    """
    _instance = None
    _yaml_config: Optional[Dict[str, Any]] = None

    def __new__(cls, *args, **kwargs):
        # Implementación básica de Singleton para asegurar una única instancia
        if not cls._instance:
            cls._instance = super(Settings, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self):
        # Evitar re-inicialización si ya existe la instancia (Singleton)
        if hasattr(self, '_initialized') and self._initialized:
            return
        logger.info("Inicializando configuración (Settings)...")

        # -----------------------------
        # Business Central (desde .env)
        # -----------------------------
        self.BC_TENANT_ID: Optional[str] = os.getenv('BC_TENANT_ID')
        self.BC_CLIENT_ID: Optional[str] = os.getenv('BC_CLIENT_ID')
        self.BC_CLIENT_SECRET: Optional[str] = os.getenv('BC_CLIENT_SECRET')
        # Validar que las credenciales esenciales de BC existan
        if not all([self.BC_TENANT_ID, self.BC_CLIENT_ID, self.BC_CLIENT_SECRET]):
             logger.warning("Faltan una o más variables de entorno para Business Central (BC_TENANT_ID, BC_CLIENT_ID, BC_CLIENT_SECRET).")
             # Podrías lanzar un error aquí si son indispensables:
             # raise ValueError("Credenciales de Business Central incompletas en .env")

        self.BC_SCOPE: str = "https://api.businesscentral.dynamics.com/.default" # Generalmente fijo
        self.BC_ENVIRONMENT: Optional[str] = os.getenv('BC_ENVIRONMENT')
        # BC_COMPANY_ID puede no ser necesario aquí si trabajas con múltiples compañías
        # self.BC_COMPANY_ID: Optional[str] = os.getenv('BC_COMPANY_ID')
        logger.debug("Configuración de Business Central cargada desde .env.")

        # -----------------------------
        # PostgreSQL (desde .env)
        # -----------------------------
        self.PG_HOST: str = os.getenv('PG_HOST', 'localhost')
        self.PG_DBNAME: str = os.getenv('PG_DBNAME', 'postgres') # Cambiar default si es necesario
        self.PG_USER: Optional[str] = os.getenv('PG_USER')
        self.PG_PASSWORD: Optional[str] = os.getenv('PG_PASSWORD', '') # Default a cadena vacía
        self.PG_PORT_STR: Optional[str] = os.getenv('PG_PORT', '5432')

        # Validar y convertir puerto
        try:
            self.PG_PORT: int = int(self.PG_PORT_STR)
        except (ValueError, TypeError):
            logger.error(f"Valor de PG_PORT ('{self.PG_PORT_STR}') inválido en .env. Usando 5432 por defecto.")
            self.PG_PORT = 5432

        # Validar credenciales esenciales de PG
        if not all([self.PG_HOST, self.PG_DBNAME, self.PG_USER]):
             logger.warning("Faltan una o más variables de entorno para PostgreSQL (PG_HOST, PG_DBNAME, PG_USER).")
             # Podrías lanzar error si son indispensables

        # Cadena de conexión (se genera bajo demanda o aquí)
        # Generarla aquí puede ser útil, pero asegura que las variables no sean None
        user = self.PG_USER or ""
        password = self.PG_PASSWORD or ""
        host = self.PG_HOST
        port = self.PG_PORT
        dbname = self.PG_DBNAME
        self.PG_CONNECTION_STRING: str = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"
        logger.debug("Configuración de PostgreSQL cargada desde .env.")

        # -----------------------------
        # Carga de config.yaml
        # -----------------------------
        # Cargar solo una vez usando la variable de clase _yaml_config
        if Settings._yaml_config is None:
            Settings._yaml_config = self._load_yaml_config()

        # -----------------------------
        # Acceso a datos específicos de YAML
        # -----------------------------
        # Crear atributos o métodos para acceder a la configuración YAML
        # Ejemplo: IDs excluidos
        yaml_data = Settings._yaml_config or {} # Usar dict vacío si la carga falló

        excluded_list = yaml_data.get('excluded_company_ids', [])
        if not isinstance(excluded_list, list):
            logger.warning("'excluded_company_ids' en config.yaml no es una lista válida. Se usará un set vacío.")
            self.EXCLUDED_COMPANY_IDS: Set[str] = set()
        else:
            self.EXCLUDED_COMPANY_IDS: Set[str] = set(excluded_list)
        logger.debug(f"IDs excluidos cargados desde YAML: {self.EXCLUDED_COMPANY_IDS}")

        # --- Marcar como inicializado ---
        self._initialized = True
        logger.info("Configuración (Settings) inicializada.")

    def _load_yaml_config(self) -> Optional[Dict[str, Any]]:
        """Método privado para cargar el archivo YAML."""
        logger.info(f"Intentando cargar configuración YAML desde: {CONFIG_YAML_PATH}")
        if not os.path.exists(CONFIG_YAML_PATH):
            logger.warning(f"Archivo de configuración YAML no encontrado en: {CONFIG_YAML_PATH}. Se omitirá.")
            return None # O devolver {} si prefieres un diccionario vacío

        try:
            with open(CONFIG_YAML_PATH, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None: # Archivo vacío
                     logger.warning(f"Archivo de configuración YAML '{CONFIG_YAML_PATH}' está vacío.")
                     return {}
                if not isinstance(config, dict):
                     logger.error(f"El contenido de '{CONFIG_YAML_PATH}' no es un diccionario YAML.")
                     return None # O lanzar TypeError
                logger.info("Configuración YAML cargada exitosamente.")
                return config
        except yaml.YAMLError as e:
            logger.error(f"Error al parsear el archivo YAML '{CONFIG_YAML_PATH}': {e}", exc_info=True)
            return None # O lanzar ValueError
        except IOError as e:
            logger.error(f"Error al leer el archivo YAML '{CONFIG_YAML_PATH}': {e}", exc_info=True)
            return None # O lanzar IOError
        except Exception as e:
            logger.error(f"Error inesperado al cargar configuración YAML: {e}", exc_info=True)
            return None # O lanzar RuntimeError

    # --- Métodos getter opcionales para configuración YAML ---
    # Podrías añadir métodos para obtener otras configuraciones del YAML
    # def get_yaml_config(self, key: str, default: Any = None) -> Any:
    #     """Obtiene un valor del diccionario YAML cargado."""
    #     if Settings._yaml_config is None:
    #         return default
    #     return Settings._yaml_config.get(key, default)


# --- Instancia Global (Singleton) ---
# Crear la instancia única al importar el módulo
try:
    settings = Settings()
except Exception as e:
     # Capturar errores durante la inicialización inicial
     logger.critical(f"¡Error CRÍTICO al inicializar la configuración!: {e}", exc_info=True)
     # Podrías definir 'settings' como None o un objeto dummy para evitar NameErrors
     # pero lo mejor es asegurar que la inicialización básica no falle.
     settings = None # O salir: sys.exit(1)