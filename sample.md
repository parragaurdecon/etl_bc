¡Entendido! Vamos a añadir la extracción y carga de la tabla `Customers` de forma similar a como hicimos con `Projects`, usando la estructura existente y la clase `ExtractMultiCompanyStep`.

Aquí están los pasos detallados:

**Paso 1: Verificar/Añadir Método en `BCRepository` para Obtener Clientes**

Necesitamos asegurarnos de que tu repositorio de Business Central (`infrastructure/business_central/bc_repository.py`) tenga un método para obtener los clientes (customers) de una compañía específica. Este método llamará al método correspondiente en `BCClient`.

*   **Abre `infrastructure/business_central/bc_client.py`:**
    *   Añade un nuevo método `fetch_customers`:
        ```python
        # En infrastructure/business_central/bc_client.py dentro de la clase BCClient

        def fetch_customers(self, company_id: str) -> Optional[Dict[str, Any]]:
            """Obtiene los clientes (customers) de una compañía."""
            self.logger.info(f"BCClient: Obteniendo clientes para compañía ID: {company_id}")
            if not company_id:
                 self.logger.warning("fetch_customers llamado sin company_id.")
                 return None
            # Ajusta el nombre del endpoint si es diferente en tu API de BC (puede ser 'customers' o similar)
            endpoint = "customers"
            url = f"{self.base_api_url}/companies({company_id})/{endpoint}"
            return self._call_get(url)

        ```
*   **Abre `infrastructure/business_central/bc_repository.py`:**
    *   Añade un nuevo método `get_customers` que use el método del cliente:
        ```python
        # En infrastructure/business_central/bc_repository.py dentro de la clase BCRepository

        def get_customers(self, company_id: str) -> Dict[str, Any]:
            """Obtiene clientes para una compañía. Devuelve {"value": []} si falla."""
            self.logger.info(f"Repositorio: Obteniendo clientes para compañía ID: {company_id}")
            if not company_id:
                self.logger.warning("get_customers llamado sin company_id.")
                return {"value": []}
            try:
                data = self.bc_client.fetch_customers(company_id)
                # Usar el helper para manejar respuesta None
                return self._handle_client_response(data, f"fetch_customers({company_id})")
            except Exception as e:
                self.logger.error(f"Error inesperado en get_customers para {company_id}: {e}", exc_info=True)
                return {"value": []}

        ```
*   **Abre `domain/repositories/interfaces.py` (si existe):**
    *   Añade `get_customers` a la interfaz `BusinessCentralRepositoryInterface`:
        ```python
        # En domain/repositories/interfaces.py dentro de BusinessCentralRepositoryInterface
        @abstractmethod
        def get_customers(self, company_id: str) -> Dict[str, Any]:
            pass
        ```

**Paso 2: Añadir Método en `BCUseCases` para Obtener Clientes**

Ahora, exponemos la funcionalidad a través de los casos de uso.

*   **Abre `application/use_cases/bc_use_cases.py`:**
    *   Añade un nuevo método `get_company_customers`:
        ```python
        # En application/use_cases/bc_use_cases.py dentro de la clase BCUseCases

        def get_company_customers(self, company_id: str) -> Dict[str, Any]:
            """
            Obtiene el JSON con los clientes de una compañía.
            (Podría incluir transformaciones futuras aquí).
            """
            self.logger.info(f"Iniciando caso de uso: Obtener Clientes para Compañía ID: {company_id}")
            try:
                if not company_id or not isinstance(company_id, str):
                     self.logger.error("company_id inválido proporcionado para get_company_customers.")
                     return {"value": []}
                self.logger.debug(f"Llamando a BCRepository.get_customers para '{company_id}'...")
                customers_data = self.bc_repository.get_customers(company_id)
                self.logger.info(f"Clientes obtenidos para '{company_id}': {len(customers_data.get('value',[]))} registros.")

                # --- Punto Potencial para Transformación de Clientes ---
                # customers_data = self.transform_service.clean_customer_data(customers_data)
                # self.logger.info("Transformación de datos de clientes aplicada.")
                # --------------------------------------------------------

                return customers_data
            except Exception as e:
                self.logger.error(f"Error en caso de uso get_company_customers para ID '{company_id}': {e}", exc_info=True)
                return {"value": []}
        ```

**Paso 3: Añadir Steps al Pipeline en `main.py`**

Ahora integramos la nueva extracción y carga en el flujo principal.

*   **Abre `main.py`:**
    *   **Define un nuevo Step de Extracción Multi-Compañía para Clientes:** Justo después de definir `step_extract_multi_projects`, añade:
        ```python
        # En main.py, sección 4 (o donde definas steps de extracción)

        step_extract_multi_customers = ExtractMultiCompanyStep(
            companies_context_key="companies_json",  # Usa las compañías filtradas
            extract_func=bc_use_cases.get_company_customers, # ¡Usa la nueva función!
            out_context_key="customers_json", # Nueva clave para guardar clientes
            company_col="CompanyId", # Mantener consistencia si aplica
            # print_to_console=False # Ya no necesario
        )
        logger.debug("... Step 'ExtractMultiCompanyStep' para Customers definido.")
        ```
    *   **Define un nuevo Step de Almacenamiento para Clientes:** En la sección 6, después de `store_projects_step`, añade:
        ```python
        # En main.py, sección 6 (o donde definas steps de almacenamiento)

        store_customers_step = StoreDataInPostgresStep(
            pg_repository=pg_repository,
            context_key="customers_json",  # Usa la clave donde guardamos los clientes
            table_name="customers_bc",      # Nuevo nombre de tabla para clientes
            convert_json_to_df=True,
            primary_key="id"  # Asume que los clientes también tienen un 'id' único como PK
                              # ¡¡Verifica esto en tus datos de BC!! Podría ser 'no' u otra columna.
                              # Si no hay PK clara, pon primary_key=None
        )
        logger.debug("... Step 'StoreDataInPostgresStep' para customers_bc definido.")
        ```
    *   **Añade los nuevos Steps a la Secuencia:** Modifica la lista `steps` para incluir los nuevos pasos en el orden deseado. Probablemente después de extraer proyectos y antes (o después) de almacenarlos:
        ```python
        # En main.py, sección 7

        steps = [
            step_extract_companies,         # -> context['companies_json'] (filtrado)
            step_extract_multi_projects,    # -> context['projects_json']
            step_extract_multi_customers,   # -> context['customers_json'] ¡NUEVO!
            check_pg_step,                  # Verifica conexión
            store_companies_step,           # Guarda compañías
            store_projects_step,            # Guarda proyectos
            store_customers_step            # Guarda clientes ¡NUEVO!
        ]
        logger.info(f"Secuencia del pipeline actualizada con {len(steps)} steps.")
        ```

**Paso 4: Ejecutar y Verificar**

1.  **Revisar `primary_key` para Clientes:** **¡MUY IMPORTANTE!** Verifica cuál es la columna que identifica unívocamente a un cliente en tu Business Central. ¿Es `id`, `no`, `systemId`? Ajusta el parámetro `primary_key="id"` en la definición de `store_customers_step` en `main.py` al nombre correcto de la columna PK. Si no hay una buena clave primaria única, establece `primary_key=None`.
2.  **Eliminar Tablas (Opcional):** Si quieres probar la creación desde cero, elimina las tablas `companies_bc`, `projects_bc` y `customers_bc` (si existe de pruebas anteriores) de tu base de datos PostgreSQL.
3.  **Ejecutar `main.py`:** Lanza el script.
4.  **Observar Logs:**
    *   Busca los logs de `ExtractMultiCompanyStep` indicando que se extrajeron registros de clientes para cada compañía.
    *   Busca los logs de `StoreDataInPostgresStep` para `customers_bc`.
    *   Si es la primera ejecución, busca los logs de `PGRepository` indicando que `customers_bc` se creó (ojalá con la PK correcta si la definiste).
    *   Busca el log de `drop_duplicates` si definiste una PK (puede que no haya duplicados en los clientes).
    *   Busca el log de `insert_table` indicando cuántos registros se insertaron en `customers_bc`.
5.  **Verificar Base de Datos:** Conéctate a PostgreSQL y comprueba:
    *   Que la tabla `customers_bc` exista.
    *   Que tenga las columnas esperadas (las que vienen de la API de BC).
    *   Que tenga la restricción `PRIMARY KEY` definida en la columna correcta (si especificaste una).
    *   Que contenga los datos de los clientes extraídos.
6.  **Ejecutar de Nuevo:** Ejecuta `main.py` una segunda vez. Ahora, los logs para `customers_bc` deberían indicar que la tabla ya existe y que la inserción incremental (si definiste PK) encontró 0 filas nuevas (o las que realmente sean nuevas si los datos cambiaron).

¡Eso es todo! Siguiendo estos pasos, habrás añadido la extracción y carga de la tabla de clientes a tu pipeline ETL.