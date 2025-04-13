# ETL Business Central a PostgreSQL

![ETL Pipeline](https://img.shields.io/badge/ETL-Pipeline-blue)
![Python](https://img.shields.io/badge/Python-3.12%2B-blue)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-PostgreSQL-orange)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Handling-yellow)
![License](https://img.shields.io/badge/License-MIT-green)

Este proyecto implementa un **proceso ETL (Extract, Transform, Load)** diseñado para extraer datos de **Microsoft Dynamics 365 Business Central**, aplicar transformaciones y cargarlos en una base de datos **PostgreSQL**. La arquitectura sigue los principios de **Clean Architecture** y **SOLID** para promover la mantenibilidad, testabilidad y separación de responsabilidades.

---

## 🌟 Características Principales

*   **Extracción desde Business Central:** Se conecta a la API de BC v2.0 usando OAuth2 (Client Credentials Flow).
*   **Carga en PostgreSQL:** Utiliza SQLAlchemy y `pandas.to_sql` para interactuar con la base de datos PostgreSQL.
*   **Arquitectura Limpia:** Separación clara entre Dominio, Aplicación, Adaptadores de Interfaz e Infraestructura.
*   **Pipeline Basado en Steps:** El flujo ETL se define como una secuencia de pasos (Steps) orquestados por un controlador, facilitando la extensión.
*   **Transformación Centralizada:** La lógica de limpieza, filtrado y enriquecimiento de datos se ubica en servicios dedicados.
*   **Inserción Incremental:** Soporte para cargar datos en PostgreSQL evitando duplicados basados en una clave primaria definida.
*   **Configuración Flexible:** Uso de archivos `.env` para credenciales y `config.yaml` para otras configuraciones.
*   **Logging Integrado:** Registro detallado de eventos y errores durante la ejecución del pipeline.
*   **Tests Unitarios (con Pytest):** Incluye ejemplos de tests unitarios para validar componentes clave usando mocks.

---

## 🏗️ Estructura del Proyecto

```plaintext
etl_bc/
├── .env                   # Variables de entorno (¡NO versionar!)
├── config.yaml            # Configuración adicional (ej. IDs excluidos)
├── requirements.txt       # Dependencias Python
├── config/
│   └── settings.py        # Carga .env y config.yaml, expone settings
├── domain/
│   ├── repositories/
│   │   └── interfaces.py  # Interfaces para los repositorios (abstracciones)
│   └── services/
│       └── transform_service.py # Lógica de transformación de datos
├── infrastructure/
│   ├── business_central/
│   │   ├── bc_client.py     # Cliente HTTP y autenticación con API BC
│   │   └── bc_repository.py # Implementación del repo BC usando el cliente
│   └── postgresql/
│       ├── pg_client.py     # Gestiona el engine de SQLAlchemy
│       └── pg_repository.py # Implementación del repo PG usando SQLAlchemy
├── application/
│   └── use_cases/
│       ├── bc_use_cases.py        # Orquesta llamadas a repos y servicios para lógica de BC
│       └── csv_export_service.py  # Servicio para exportar a CSV (opcional)
├── interface_adapters/
│   └── controllers/
│       ├── etl_controller.py      # Orquesta la ejecución del pipeline (lista de steps)
│       ├── pipeline_extract.py    # Steps relacionados con la extracción (E)
│       └── pipeline_store.py      # Steps relacionados con la carga (L) y conexión
├── tests/                   # Tests unitarios (pytest)
│   ├── test_transform_service.py
│   ├── test_bc_use_cases.py
│   └── test_pipeline_store.py
│   └── ...
└── main.py                # Punto de entrada, configuración del pipeline e inyección de dependencias
```

## 📚 Descripción de Componentes Clave

*   **`config/settings.py` & `config.yaml`**: Gestionan toda la configuración. `settings.py` lee credenciales de `.env` y configuraciones generales de `config.yaml`. Se accede a través de la instancia `settings`.
*   **`domain/`**: El núcleo del negocio.
    *   **`repositories/interfaces.py`**: Define los "contratos" que la infraestructura debe cumplir (ej., qué métodos debe tener un repositorio de BC).
    *   **`services/transform_service.py`**: Contiene la lógica pura de transformación (filtrar, limpiar, enriquecer datos), independiente de dónde vengan o a dónde vayan. Lee configuración específica (como IDs a excluir) desde `settings`.
*   **`infrastructure/`**: Detalles técnicos de cómo interactuar con sistemas externos.
    *   **`business_central/`**: Clases para hablar con la API de BC (`bc_client`) y la implementación concreta del repositorio (`bc_repository`) que usa el cliente.
    *   **`postgresql/`**: Clases para manejar la conexión y operaciones con PostgreSQL usando SQLAlchemy (`pg_client`, `pg_repository`). `pg_repository` implementa métodos para crear tablas (con PK), insertar datos y realizar cargas incrementales.
*   **`application/use_cases/`**: Orquesta el flujo de datos entre repositorios y servicios de dominio para cumplir objetivos específicos (ej., `get_companies` obtiene datos del repo BC y los pasa al `transform_service` para filtrar).
*   **`interface_adapters/controllers/`**: Adaptan las llamadas y orquestan el flujo general del ETL.
    *   **`etl_controller.py`**: Define la interfaz `ETLStepInterface` y la clase `ETLController` que ejecuta una lista de steps secuencialmente, pasando un diccionario de `context` entre ellos.
    *   **`pipeline_extract.py` / `pipeline_store.py`**: Contienen las implementaciones concretas de `ETLStepInterface` para cada paso del pipeline (Extraer Compañías, Extraer Proyectos, Verificar Conexión PG, Almacenar Datos PG). Estos steps usan los `BCUseCases` y `PGRepository`.
*   **`main.py`**: Punto de entrada. Configura el logging, instancia todas las clases necesarias (clientes, repositorios, servicios, casos de uso, steps) e **inyecta las dependencias**. Define la secuencia de steps y lanza el `ETLController`.
*   **`tests/`**: Contiene los tests unitarios escritos con `pytest` y `unittest.mock` para verificar el comportamiento aislado de los servicios, casos de uso y steps.

---

## ⚙️ Requisitos Previos

*   **Python 3.10+** (recomendado 3.12+)
*   **pip** y **venv** (recomendado para entornos virtuales)
*   Acceso a un servidor **PostgreSQL** (local o remoto)
*   **Credenciales de Aplicación Registrada en Azure AD** con permisos para la API de Business Central.

---

## 🚀 Instalación y Configuración

1.  **Clonar el repositorio:**
    ```bash
    git clone <url_del_repositorio>
    cd <nombre_del_repositorio>
    ```

2.  **(Recomendado) Crear y activar un entorno virtual:**
    ```bash
    python -m venv .venv
    # Linux/Mac
    source .venv/bin/activate
    # Windows (cmd/powershell)
    .venv\Scripts\activate
    ```

3.  **Instalar dependencias:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Asegúrate de que `requirements.txt` incluya `requests`, `python-dotenv`, `pandas`, `SQLAlchemy`, `psycopg2-binary` (o `psycopg2`), `PyYAML`, `pytest`, `pytest-mock`)*

4.  **Configurar `.env`:**
    Crea un archivo `.env` en la raíz del proyecto y añade tus credenciales:
    ```dotenv
    # --- Business Central ---
    BC_TENANT_ID=TU_TENANT_ID_AZURE
    BC_CLIENT_ID=TU_CLIENT_ID_APLICACION
    BC_CLIENT_SECRET=TU_CLIENT_SECRET_APLICACION
    BC_ENVIRONMENT=production # O sandbox, etc.

    # --- PostgreSQL ---
    PG_HOST=localhost # O la IP/hostname de tu servidor PG
    PG_DBNAME=business_central # Nombre de la BD destino
    PG_USER=postgres # Usuario de la BD
    PG_PASSWORD=tu_password_segura
    PG_PORT=5432 # Puerto estándar de PG
    ```

5.  **Configurar `config.yaml`:**
    Crea/edita el archivo `config.yaml` (en la misma carpeta que `settings.py`, normalmente `config/`) para definir configuraciones como los IDs de compañías a excluir:
    ```yaml
    # config.yaml
    excluded_company_ids:
      - "ID_EMPRESA_A_EXCLUIR_1"
      - "ID_EMPRESA_A_EXCLUIR_2"
    # otras_configs: valor
    ```

---

## ▶️ Ejecución

Una vez configurado, ejecuta el pipeline desde la raíz del proyecto:

```bash
python main.py
```

El script realizará los siguientes pasos (según la configuración actual en `main.py`):

1.  **Configurará el logging.**
2.  **Instanciará las dependencias** necesarias (clientes, repositorios, servicios, casos de uso).
3.  **Extraerá Compañías:** Obtendrá la lista de compañías desde Business Central y aplicará el filtrado definido en `config.yaml` a través de `TransformService`. Opcionalmente, guardará las compañías *filtradas* en un archivo CSV (`companies_filtered_export.csv`).
4.  **Extraerá Proyectos:** Obtendrá los datos de proyectos correspondientes únicamente a las compañías *filtradas* en el paso anterior.
5.  **Verificará Conexión PG:** Realizará una prueba de conexión a la base de datos PostgreSQL configurada.
6.  **Almacenará Compañías:** Utilizará la lógica de inserción incremental (`incremental_insert_table`):
    *   Si la tabla `companies_bc` no existe, la creará definiendo la columna `id` como Primary Key e insertará las filas únicas del DataFrame de compañías.
    *   Si la tabla `companies_bc` ya existe, consultará los `id` existentes e insertará únicamente las compañías del DataFrame actual cuyos `id` no se encuentren en la tabla.
7.  **Almacenará Proyectos:** Realizará el mismo proceso incremental para la tabla `projects_bc`, usando también la columna `id` como Primary Key.

*Observa la salida de la consola para ver los logs informativos (`INFO`, `DEBUG`, `WARNING`, `ERROR`) que detallan cada paso y cualquier problema encontrado.*

---

## 🧪 Ejecución de Tests

Para ejecutar los tests unitarios (asegúrate de haber instalado `pytest` y `pytest-mock`):

```bash
pytest
```
O para ejecutar los tests de un archivo específico:
```bash
pytest tests/test_transform_service.py
```

# 🧩 Extensibilidad

El diseño basado en Steps permite añadir fácilmente nueva funcionalidad al pipeline:

1. **Define la Lógica:**  
   Implementa la nueva funcionalidad de extracción, transformación o carga dentro de las capas apropiadas (Repositorio, Servicio, Caso de Uso).

2. **Crea un Nuevo Step:**  
   Define una nueva clase en `pipeline_extract.py`, `pipeline_store.py` (o crea un `pipeline_transform.py`) que herede de `ETLStepInterface`.

3. **Implementa `run(self, context)`:**  
   Escribe el código dentro del método `run` de tu nuevo Step. Llama a los Casos de Uso necesarios, lee/escribe en el diccionario `context` y devuelve el `context` actualizado.

4. **Añade el Step a `main.py`:**  
   Instancia tu nuevo step en `main.py` y añádelo a la lista `steps` en la posición deseada dentro de la secuencia del pipeline.

# 📜 Principios y Patrones

- **Clean Architecture / SOLID:**  
  Se busca separar las preocupaciones (negocio, aplicación, infraestructura), reducir el acoplamiento y aumentar la cohesión, facilitando el mantenimiento y la evolución del código.

- **Inyección de Dependencias:**  
  Las dependencias (objetos que una clase necesita para funcionar) se crean en el punto de entrada (`main.py`) y se "inyectan" a las clases a través de sus constructores. Esto mejora la testabilidad y flexibilidad.

- **Patrón Repositorio:**  
  Abstrae los detalles del acceso a los datos (cómo hablar con la API de BC o con la BD PG), proporcionando una interfaz limpia a la capa de aplicación.

- **Patrón Servicio:**  
  Encapsula lógica de negocio reutilizable o procesos de transformación complejos (por ejemplo, `TransformService`).

- **Pipeline (Steps + Controller):**  
  Modela el proceso ETL como una cadena de pasos discretos y bien definidos, orquestados por un controlador (`ETLController`), lo que facilita la comprensión y modificación del flujo.
