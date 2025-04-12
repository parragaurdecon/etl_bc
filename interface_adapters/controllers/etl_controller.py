"""
interface_adapters/controllers/etl_controller.py
Controlador que orquesta el flujo ETL mediante una secuencia de Steps.
"""
from typing import List, Dict, Any
from interface_adapters.controllers.pipeline_extract import ETLStepInterface

class ETLController:
    """
    Controlador principal: ejecuta una lista de pasos ETL de forma secuencial.
    """
    def __init__(self, steps: List[ETLStepInterface]):
        """
        Recibe una lista de steps (por ejemplo, ListCompaniesStep, ListCustomersStep, etc.).
        """
        self.steps = steps

    def run_etl_process(self):
        """
        Ejecuta cada step secuencialmente, pasando el 'context' entre ellos.
        """
        context: Dict[str, Any] = {}
        for step in self.steps:
            context = step.run(context)
        # Al final, 'context' contiene todos los datos generados
        print("\nETL Finalizado. Contexto resultante:", context.keys())
