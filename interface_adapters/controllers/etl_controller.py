# interface_adapters/controllers/etl_controller.py
import logging
# --- CORRECCIÓN AQUÍ: Añadir Optional ---
from typing import Any, Dict, List, Optional

# --- DEFINICIÓN DE LA INTERFAZ BASE AQUÍ ---
class ETLStepInterface:
    """Interfaz base para todos los pasos del pipeline ETL."""
    def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecuta la lógica del paso y actualiza/devuelve el contexto."""
        raise NotImplementedError
# ------------------------------------------

class ETLController:
    """Orquesta la ejecución de una secuencia de pasos ETL."""
    def __init__(self, steps: List[ETLStepInterface]):
        """
        Inicializa el controlador con una lista de pasos ETL.

        :param steps: Lista de objetos que implementan ETLStepInterface.
        :raises ValueError: Si la lista de steps está vacía.
        """
        if not steps:
            raise ValueError("La lista de steps no puede estar vacía.")
        # Validar que todos los steps implementen la interfaz (opcional pero bueno)
        for i, step in enumerate(steps):
             if not isinstance(step, ETLStepInterface):
                  raise TypeError(f"El objeto en la posición {i} de la lista de steps ('{step.__class__.__name__}') no implementa ETLStepInterface.")
        self.steps = steps
        self.logger = logging.getLogger(__name__)

    # --- La firma de este método usa Optional ---
    def run_etl_process(self, initial_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Ejecuta la secuencia de steps, pasando el contexto entre ellos.

        :param initial_context: Un diccionario opcional para iniciar el contexto.
        :return: El diccionario de contexto final después de ejecutar todos los steps.
        :raises RuntimeError: Si algún step falla durante la ejecución.
        """
        context = initial_context if initial_context is not None else {}
        self.logger.info(f"Iniciando ejecución del pipeline con {len(self.steps)} steps.")
        for i, step in enumerate(self.steps):
            step_name = step.__class__.__name__ # Obtener nombre de la clase del step
            self.logger.info(f"--- Ejecutando Step {i+1}/{len(self.steps)}: {step_name} ---")
            try:
                # Cada step recibe el contexto y devuelve el contexto (potencialmente modificado)
                context = step.run(context)
                self.logger.info(f"--- Step {step_name} completado ---")
            except Exception as e:
                # Capturar cualquier excepción del step.run()
                self.logger.error(f"Error fatal ejecutando el step {step_name}: {e}", exc_info=True)
                # Relanzar para detener el pipeline
                raise RuntimeError(f"Fallo en el step {step_name}") from e

        self.logger.info("Ejecución del pipeline completada.")
        # Loguear solo las claves para evitar logs enormes si el contexto es grande
        self.logger.debug(f"Contexto final contiene claves: {list(context.keys())}")
        return context