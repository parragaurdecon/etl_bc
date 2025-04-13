# infrastructure/logging/error_counter_handler.py

"""
Manejador de logging personalizado para contar errores y warnings.
"""

import logging

class ErrorWarningCounterHandler(logging.Handler):
    """
    Un manejador de logging que simplemente cuenta la cantidad de mensajes
    de nivel ERROR y WARNING emitidos a través del sistema de logging.
    """
    def __init__(self, level=logging.WARNING):
        """
        Inicializa el manejador.
        :param level: El nivel mínimo de log a considerar (por defecto WARNING).
        """
        super().__init__(level=level)
        self.reset()

    def emit(self, record: logging.LogRecord):
        """
        Procesa un registro de log, incrementando los contadores si aplica.
        No formatea ni escribe el registro.
        """
        if record.levelno >= logging.ERROR:
            self.error_count += 1
        # Usar elif para no contar errores también como warnings
        elif record.levelno >= logging.WARNING:
            self.warning_count += 1

    def reset(self):
        """Resetea los contadores a cero."""
        self.warning_count = 0
        self.error_count = 0

    @property
    def has_errors(self) -> bool:
        """Devuelve True si se registró al menos un error."""
        return self.error_count > 0

    @property
    def has_warnings(self) -> bool:
         """Devuelve True si se registró al menos un warning (y no es un error)."""
         # Podrías querer que esto sea True incluso si hay errores, depende de tu necesidad.
         # Esta versión solo reporta warnings si NO hay errores.
         # return self.warning_count > 0
         # Esta versión reporta si hay warnings, independientemente de los errores:
         return self.warning_count > 0

    @property
    def has_issues(self) -> bool:
        """Devuelve True si hubo errores o warnings."""
        return self.error_count > 0 or self.warning_count > 0

    @property
    def issue_summary(self) -> str:
        """Devuelve un resumen textual de los problemas encontrados."""
        if not self.has_issues:
            return "Sin errores ni warnings registrados."
        parts = []
        if self.error_count > 0:
            parts.append(f"{self.error_count} ERROR{'s' if self.error_count > 1 else ''}")
        if self.warning_count > 0:
            parts.append(f"{self.warning_count} WARNING{'s' if self.warning_count > 1 else ''}")
        return f"Resumen: {', '.join(parts)}."