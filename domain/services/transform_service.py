# domain/services/transform_service.py
"""
TransformService: lógica de transformación de datos desacoplada.
Aplicable antes de guardar en Postgres.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

# --- Importar settings ---
try:
    from config.settings import settings
except ImportError:
    logging.critical("Error CRÍTICO: No se pudo importar 'settings'. Usando configuración dummy.")
    class DummySettings:
        EXCLUDED_COMPANY_IDS: Set[str] = set()
    settings = DummySettings()

class TransformService:
    """
    Servicio para aplicar transformaciones genéricas a datos de Business Central antes
    de su almacenamiento en Postgres.
    """
    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self.excluded_ids: Set[str] = getattr(settings, 'EXCLUDED_COMPANY_IDS', set())
        self.logger.info(f"TransformService inicializado. Excluyendo {len(self.excluded_ids)} IDs de compañías si procede.")

    def filter_companies(self, companies_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filtra compañías según IDs excluidos en settings.
        """
        if not companies_data or 'value' not in companies_data:
            self.logger.warning("Formato inválido en filter_companies.")
            return {'value': []}
        original = companies_data['value']
        filtered = [c for c in original if c.get('id') not in self.excluded_ids]
        removed = len(original) - len(filtered)
        if removed:
            self.logger.info(f"Se filtraron {removed} compañías según configuración.")
        return {'value': filtered}

    def drop_columns(self, data: Dict[str, Any], columns: Set[str]) -> Dict[str, Any]:
        """
        Elimina claves específicas de cada registro en data['value'].
        """
        if not data or 'value' not in data:
            self.logger.warning("Formato inválido en drop_columns.")
            return {'value': []}
        result: List[Dict[str, Any]] = []
        for record in data['value']:
            new_rec = {k: v for k, v in record.items() if k not in columns}
            result.append(new_rec)
        self.logger.debug(f"Dropped columns {columns} de {len(result)} registros.")
        return {'value': result}

    def concat_columns(self, data: Dict[str, Any], new_col: str, cols: List[str], separator: str = '_') -> Dict[str, Any]:
        """
        Añade un campo resultante de concatenar valores de columnas existentes.

        :param data: {'value': [ ... ]}
        :param new_col: nombre de la nueva columna
        :param cols: lista de columnas a concatenar
        :param separator: separador entre valores
        """
        if not data or 'value' not in data:
            self.logger.warning("Formato inválido en concat_columns.")
            return {'value': []}
        result: List[Dict[str, Any]] = []
        for record in data['value']:
            values = [str(record.get(c, '')) for c in cols]
            record[new_col] = separator.join(values)
            result.append(record)
        self.logger.debug(f"Concat columnas {cols} en '{new_col}' para {len(result)} registros.")
        return {'value': result}

# Eliminar métodos específicos de tablas; en su lugar crear pipeline_transform.py para componer pasos.
