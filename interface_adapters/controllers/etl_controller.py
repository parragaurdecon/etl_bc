# interface_adapters/controllers/etl_controller.py

import logging
from typing import Any, Dict, List, Optional

# --- Importar la nueva clase Handler y la Interfaz Base ---
try:
    # Asumiendo que el handler está en la ruta correcta
    from infrastructure.logging.error_counter_handler import ErrorWarningCounterHandler
except ImportError:
     logging.critical("Error crítico: No se pudo importar ErrorWarningCounterHandler.")
     # Definir placeholder
     class ErrorWarningCounterHandler:
         has_issues = False; error_count = 0; warning_count = 0
         def issue_summary(self): return "Handler no cargado"
         def reset(self): pass

class ETLStepInterface:
    """Interfaz base para todos los pasos del pipeline ETL."""
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError
# -----------------------------------------------------------

class ETLController:
    """Orquesta la ejecución de una secuencia de pasos ETL."""
    def __init__(self, steps: List[ETLStepInterface]):
        """
        Inicializa el controlador con una lista de pasos ETL.

        :param steps: Lista de objetos que implementan ETLStepInterface.
        :raises ValueError: Si la lista de steps está vacía.
        :raises TypeError: Si algún objeto en la lista no implementa la interfaz.
        """
        if not steps:
            raise ValueError("La lista de steps no puede estar vacía.")
        for i, step in enumerate(steps):
             if not isinstance(step, ETLStepInterface):
                  raise TypeError(f"Step {i} ('{step.__class__.__name__}') no implementa ETLStepInterface.")
        self.steps = steps
        self.logger = logging.getLogger(__name__)

    def run_etl_process(self, initial_context: Optional[Dict[str, Any]] = None) -> (Dict[str, Any], ErrorWarningCounterHandler): # Devuelve tupla
        """
        Ejecuta la secuencia de steps, pasando el contexto entre ellos.
        Añade temporalmente un handler para contar errores y warnings.

        :param initial_context: Diccionario opcional para iniciar el contexto.
        :return: Tupla conteniendo (contexto_final, instancia_del_handler_contador).
        :raises RuntimeError: Si algún step falla durante la ejecución.
        """
        context = initial_context if initial_context is not None else {}
        self.logger.info(f"Iniciando ejecución del pipeline con {len(self.steps)} steps.")

        # --- Añadir y quitar manejador contador ---
        counter_handler = ErrorWarningCounterHandler(level=logging.WARNING) # Contar WARNING y superior
        root_logger = logging.getLogger() # Obtener logger raíz
        # Guardar nivel original para restaurarlo después (buena práctica)
        original_level = root_logger.level
        # Asegurar que el logger raíz procesa al menos el nivel del handler
        if root_logger.level > counter_handler.level:
             root_logger.setLevel(counter_handler.level)
        root_logger.addHandler(counter_handler)
        self.logger.debug(f"Handler contador de errores/warnings añadido (Nivel: {logging.getLevelName(counter_handler.level)}).")
        # ---------------------------------------

        pipeline_failed = False
        try:
            for i, step in enumerate(self.steps):
                step_name = step.__class__.__name__
                self.logger.info(f"--- Ejecutando Step {i+1}/{len(self.steps)}: {step_name} ---")
                try:
                    context = step.run(context)
                    self.logger.info(f"--- Step {step_name} completado ---")
                except Exception as e:
                    # El error fatal del step será logueado aquí Y contado por el handler
                    self.logger.error(f"Error fatal ejecutando el step {step_name}: {e}", exc_info=True)
                    pipeline_failed = True
                    # Relanzar para detener el pipeline
                    raise RuntimeError(f"Fallo en el step {step_name}") from e

            # Mensaje final del controlador (solo si no hubo fallos fatales)
            if not pipeline_failed:
                self.logger.info("Ejecución del pipeline completada por el controlador.")
                self.logger.debug(f"Contexto final contiene claves: {list(context.keys())}")

        finally:
            # --- Asegurar que quitamos el manejador y restauramos nivel ---
            self.logger.debug("Quitando handler contador de errores/warnings...")
            root_logger.removeHandler(counter_handler)
            # Restaurar nivel original del logger raíz
            root_logger.setLevel(original_level)
            self.logger.debug("Handler contador quitado y nivel del logger raíz restaurado.")
            # -----------------------------------------

        # Devolver siempre el contexto y el contador para que main decida el estado final
        return context, counter_handler