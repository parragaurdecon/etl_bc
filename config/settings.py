# config/settings.py

"""
config/settings.py
Lee las variables de entorno para las credenciales y la configuración.
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    def __init__(self):
        # -----------------------------
        # Business Central
        # -----------------------------
        self.BC_TENANT_ID = os.getenv('BC_TENANT_ID')
        self.BC_CLIENT_ID = os.getenv('BC_CLIENT_ID')
        self.BC_CLIENT_SECRET = os.getenv('BC_CLIENT_SECRET')
        self.BC_SCOPE = "https://api.businesscentral.dynamics.com/.default"
        self.BC_ENVIRONMENT = os.getenv('BC_ENVIRONMENT')
        self.BC_COMPANY_ID = os.getenv('BC_COMPANY_ID')

        # -----------------------------
        # PostgreSQL
        # -----------------------------
        self.PG_HOST = os.getenv('PG_HOST', 'localhost')
        self.PG_DBNAME = os.getenv('PG_DBNAME', 'postgres')
        self.PG_USER = os.getenv('PG_USER', 'postgres')
        self.PG_PASSWORD = os.getenv('PG_PASSWORD', '')
        self.PG_PORT = int(os.getenv('PG_PORT', 5432))

        # Cadena de conexión para SQLAlchemy + psycopg2
        self.PG_CONNECTION_STRING = (
            f"postgresql+psycopg2://{self.PG_USER}:{self.PG_PASSWORD}"
            f"@{self.PG_HOST}:{self.PG_PORT}/{self.PG_DBNAME}"
        )

# Instancia global de Settings
settings = Settings()
