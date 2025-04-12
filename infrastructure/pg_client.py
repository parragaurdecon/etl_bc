from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from typing import Optional
from config.settings import settings  # Asumiendo credenciales en .env o similar

class SqlAlchemyClient:
    """
    Cliente que crea y gestiona el Engine de SQLAlchemy para PostgreSQL.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        port: int = 5432
    ):
        self.host = host or settings.PG_HOST
        self.dbname = dbname or settings.PG_DBNAME
        self.user = user or settings.PG_USER
        self.password = password or settings.PG_PASSWORD
        self.port = port or settings.PG_PORT

        self.engine = self._create_engine()

    def _create_engine(self) -> Engine:
        """
        Crea el Engine de SQLAlchemy para PostgreSQL.
        """
        connection_url = (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.dbname}"
        )
        return create_engine(connection_url)

    def get_engine(self) -> Engine:
        """
        Devuelve el engine para su uso externo (por ejemplo, df.to_sql).
        """
        return self.engine