# tests/test_transform_service.py
import pytest
from unittest.mock import MagicMock # Aún podemos usar MagicMock
import logging
from typing import Dict, Any, List, Set

# Asumiendo rutas correctas
from domain.services.transform_service import TransformService
# Necesitamos mockear 'settings' que es importado por el servicio
# from config import settings # No importamos el real, lo mockeamos

# Desactivar logging excesivo durante tests (opcional)
# logging.disable(logging.CRITICAL)

# Fixture para crear una instancia del servicio con settings mockeados
@pytest.fixture
def transform_service(mocker) -> TransformService:
    """Fixture que mockea 'settings' y crea una instancia de TransformService."""
    # Mockear la instancia 'settings' importada por transform_service.py
    mock_settings_instance = MagicMock()
    # Configurar el atributo que usa el servicio
    mock_settings_instance.EXCLUDED_COMPANY_IDS = {"ID_EXCLUIDA_1", "ID_EXCLUIDA_3"}
    # Usar mocker.patch para reemplazar la instancia 'settings' en el módulo del servicio
    mocker.patch('domain.services.transform_service.settings', mock_settings_instance)

    # Ahora instanciar el servicio, leerá el mock
    service = TransformService()
    # Pasar el mock también por si el test necesita modificarlo después
    return service, mock_settings_instance

# --- Tests ---

def test_filter_companies_success(transform_service):
    """Prueba el filtrado exitoso de compañías."""
    service, mock_settings = transform_service # Desempaquetar fixture

    test_data = {
        "value": [
            {"id": "ID_VALIDA_1", "name": "Compañía Valida 1"},
            {"id": "ID_EXCLUIDA_1", "name": "Compañía Excluida 1"},
            {"id": "ID_VALIDA_2", "name": "Compañía Valida 2"},
            {"id": "ID_EXCLUIDA_3", "name": "Compañía Excluida 3"},
            {"id": "ID_OTRA_VALIDA", "name": "Otra Valida"},
        ]
    }
    expected_value = [
        {"id": "ID_VALIDA_1", "name": "Compañía Valida 1"},
        {"id": "ID_VALIDA_2", "name": "Compañía Valida 2"},
        {"id": "ID_OTRA_VALIDA", "name": "Otra Valida"},
    ]

    result = service.filter_companies(test_data)

    assert result["value"] == expected_value
    # Opcional: verificar que los IDs excluidos en settings se usaron
    assert service.excluded_ids == {"ID_EXCLUIDA_1", "ID_EXCLUIDA_3"}

def test_filter_companies_no_exclusions_match(transform_service):
    """Prueba cuando ningún ID coincide con la lista de exclusión."""
    service, mock_settings = transform_service
    # Modificar el mock *después* de la inicialización del servicio
    # y actualizar el atributo del servicio directamente
    new_excluded_ids = {"ID_NO_EXISTENTE"}
    mock_settings.EXCLUDED_COMPANY_IDS = new_excluded_ids
    service.excluded_ids = new_excluded_ids # Actualizar el estado interno del servicio

    test_data = {
        "value": [
            {"id": "ID_VALIDA_1", "name": "Compañía Valida 1"},
            {"id": "ID_VALIDA_2", "name": "Compañía Valida 2"},
        ]
    }
    expected_value = test_data["value"]

    result = service.filter_companies(test_data)
    assert result["value"] == expected_value

def test_filter_companies_empty_input_list(transform_service):
    """Prueba con una lista de compañías vacía en la entrada."""
    service, _ = transform_service
    test_data = {"value": []}
    expected_value = []
    result = service.filter_companies(test_data)
    assert result["value"] == expected_value

# Usar parametrize para probar múltiples entradas inválidas
@pytest.mark.parametrize("invalid_data", [
    None,
    {},
    {"valor": []},
    [],
    {"value": "no es una lista"}
])
def test_filter_companies_invalid_input_format(transform_service, invalid_data):
    """Prueba con formatos de entrada inválidos."""
    service, _ = transform_service
    expected_value = []
    result = service.filter_companies(invalid_data)
    assert result["value"] == expected_value

def test_filter_companies_no_id_field(transform_service):
    """Prueba con datos de compañía que no tienen campo 'id'."""
    service, mock_settings = transform_service
    # Asegurar que el mock está configurado como esperamos
    mock_settings.EXCLUDED_COMPANY_IDS = {"ID_EXCLUIDA_1"}
    service.excluded_ids = {"ID_EXCLUIDA_1"}

    test_data = {
        "value": [
            {"name": "Sin ID 1"}, # No tiene 'id', no debería ser filtrada
            {"id": "ID_EXCLUIDA_1", "name": "Compañía Excluida 1"},
            {"id": "ID_VALIDA_2", "name": "Compañía Valida 2"},
        ]
    }
    expected_value = [
        {"name": "Sin ID 1"}, # Se mantiene
        {"id": "ID_VALIDA_2", "name": "Compañía Valida 2"},
    ]
    result = service.filter_companies(test_data)
    assert result["value"] == expected_value