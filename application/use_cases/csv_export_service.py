# application/use_cases/csv_export_service.py
import pandas as pd
from typing import Dict, Any

class CSVExportService:
    """
    Servicio que exporta un dict JSON a un CSV de forma genérica.
    """

    def export_json_to_csv(self, data_json: Dict[str, Any], file_path: str, array_key: str = None) -> pd.DataFrame:
        """
        Convierte 'data_json' en DataFrame y lo exporta a CSV.
        :param data_json: un dict con la info (a veces con 'value', otras no).
        :param file_path: ruta del CSV de salida.
        :param array_key: si la info está en data_json['value'], pasarlo; si no, None.
        :return: El DataFrame resultante.
        """
        if array_key and array_key in data_json:
            df = pd.DataFrame(data_json[array_key])
        else:
            # Caso: data_json es un objeto dict o una lista
            if isinstance(data_json, dict):
                df = pd.DataFrame([data_json])
            else:
                df = pd.DataFrame(data_json)

        df.to_csv(file_path, index=False, encoding='utf-8')
        return df
