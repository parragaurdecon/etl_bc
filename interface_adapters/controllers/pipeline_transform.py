# interface_adapters/controllers/pipeline_transform.py
"""
Define pasos de transformación reutilizables para el pipeline ETL.
Cada Step implementa `ETLStepInterface` para integrarse con `ETLController`.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Set

from domain.services.transform_service import TransformService
from interface_adapters.controllers.etl_controller import ETLStepInterface

LOGGER = logging.getLogger(__name__)


class TransformStep(ETLStepInterface):
    """Base para pasos de transformación genéricos."""

    def __init__(
        self,
        service: TransformService,
        context_key: str,
        out_context_key: str | None = None,
    ) -> None:
        self.service = service
        self.context_key = context_key
        self.out_context_key = out_context_key or context_key

    # Por defecto cada subclase implementará run
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        raise NotImplementedError


class DropColumnsStep(TransformStep):
    """Elimina columnas indicadas de un JSON OData en el contexto."""

    def __init__(
        self,
        service: TransformService,
        context_key: str,
        columns: Set[str],
        out_context_key: str | None = None,
    ) -> None:
        super().__init__(service, context_key, out_context_key)
        self.columns = columns

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        data = context.get(self.context_key, {})
        transformed = self.service.drop_columns(data, self.columns)
        context[self.out_context_key] = transformed
        LOGGER.info(
            "DropColumnsStep: eliminadas %s de '%s'.",
            self.columns,
            self.context_key,
        )
        return context


class ConcatColumnsStep(TransformStep):
    """Concatena columnas para crear un nuevo campo en cada registro."""

    def __init__(
        self,
        service: TransformService,
        context_key: str,
        new_col: str,
        cols: List[str],
        separator: str = "_",
        out_context_key: str | None = None,
    ) -> None:
        super().__init__(service, context_key, out_context_key)
        self.new_col = new_col
        self.cols = cols
        self.separator = separator

    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:  # noqa: D401
        data = context.get(self.context_key, {})
        transformed = self.service.concat_columns(
            data, self.new_col, self.cols, self.separator
        )
        context[self.out_context_key] = transformed
        LOGGER.info(
            "ConcatColumnsStep: creada columna '%s' en '%s'.",
            self.new_col,
            self.context_key,
        )
        return context
