# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

Una aplicación web moderna y orientada a dispositivos móviles para gestionar tu biblioteca de libros electrónicos, que se integra con Calibre y proporciona un servidor WebDAV personal para tus dispositivos compatibles con Anx-reader.

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README_zh-Hans.md">简体中文</a></strong> |
  <strong><a href="README_zh-Hant.md">繁體中文</a></strong> |
  <strong><a href="README_es.md">Español</a></strong> |
  <strong><a href="README_fr.md">Français</a></strong> |
  <strong><a href="README_de.md">Deutsch</a></strong>
</p>

## ✨ Características

- **Soporte Multilingüe**: Soporte completo de internacionalización. La interfaz está disponible en inglés, chino simplificado (简体中文), chino tradicional (繁體中文), español, francés y alemán.
- **Interfaz Orientada a Móviles**: Una interfaz de usuario limpia y adaptable diseñada para un uso fácil en tu teléfono.
- **Soporte PWA**: Se puede instalar como una Aplicación Web Progresiva para una experiencia similar a la nativa.
- **Visualizador de libros en el navegador**: Previsualiza libros electrónicos directamente en tu navegador. Incluye función de texto a voz (TTS).
- **Generación de Audiolibros**: Convierte libros EPUB en audiolibros M4B con marcadores de capítulo, utilizando proveedores de Texto a Voz (TTS) configurables (por ejemplo, Microsoft Edge TTS). Los archivos M4B generados son totalmente compatibles con servidores de audiolibros como [Audiobookshelf](https://www.audiobookshelf.org/).
- **Reproductor de Audiolibros en Línea**: Escucha tus audiolibros M4B generados directamente en el navegador. Tu progreso de escucha se guarda y sincroniza automáticamente.
- **Preguntar a la IA**: Mantén conversaciones con tus libros. Esta función te permite chatear con cualquier libro de tu biblioteca, hacer preguntas sobre su contenido, obtener resúmenes o explorar temas a través de una interfaz impulsada por IA.
- **Integración con Calibre**: Se conecta a tu servidor Calibre existente para navegar y buscar en tu biblioteca.
- **Sincronización con KOReader**: Sincroniza tu progreso de lectura y tiempo de lectura con dispositivos KOReader.
- **Envío Inteligente a Kindle**: Maneja automáticamente los formatos al enviar a tu Kindle. Si existe un EPUB, se envía directamente. Si no, la aplicación **convierte el mejor formato disponible a EPUB** según tus preferencias antes de enviarlo, asegurando una compatibilidad óptima.
- **Enviar a Anx**: Envía libros de tu biblioteca de Calibre directamente a la carpeta de tu dispositivo Anx-reader personal.
- **Servidor WebDAV Integrado**: Cada usuario obtiene su propia carpeta WebDAV segura, compatible con Anx-reader y otros clientes WebDAV.
- **Servidor MCP**: Un servidor incorporado y compatible con el Protocolo de Contexto de Modelo (MCP), que permite a agentes de IA y herramientas externas interactuar de forma segura con tu biblioteca.
- **Gestión de Usuarios**: Sistema de gestión de usuarios simple e integrado con roles distintos:
    - **Administrador**: Control total sobre usuarios, configuraciones globales y todos los libros.
    - **Mantenedor**: Puede editar los metadatos de todos los libros.
    - **Usuario**: Puede subir libros, gestionar su propia biblioteca WebDAV, tokens MCP, enviar libros a Kindle y **editar los libros que ha subido**.
- **Registro solo por Invitación**: Los administradores pueden generar códigos de invitación para controlar el registro de usuarios. Esta función está habilitada por defecto para evitar registros no autorizados.
- **Libros Subidos Editables por el Usuario**: Los usuarios regulares ahora pueden editar los metadatos de los libros que han subido. Esta funcionalidad se basa en una columna personalizada de Calibre llamada `#library` (tipo: `Texto, con comas tratadas como etiquetas separadas`). Cuando un usuario sube un libro, su nombre de usuario se guarda automáticamente en este campo. Los usuarios pueden editar cualquier libro en el que figuren como propietarios en el campo `#library`.
    - **Recomendación para Usuarios de Docker**: Para habilitar esta función, asegúrate de tener una columna personalizada en tu biblioteca de Calibre llamada `#library` (sensible a mayúsculas y minúsculas) con el tipo `Texto, con comas tratadas como etiquetas separadas`.
- **Despliegue Fácil**: Desplegable como un único contenedor de Docker con soporte de localización multilingüe incorporado.
- **Estadísticas de Lectura**: Genera automáticamente una página personal de estadísticas de lectura, con un mapa de calor de lectura anual, una lista de libros que se están leyendo actualmente y una lista de libros terminados. La página se puede compartir públicamente o mantener privada.

## 📸 Capturas de Pantalla

<p align="center">
  <em>Interfaz Principal</em><br>
  <img src="screenshots/Screen Shot - MainPage.png">
</p>
<p align="center">
  <em>Página de Configuración</em><br>
  <img src="screenshots/Screen Shot - SettingPage.png">
</p>

<p align="center">
  <em>Configuración de MCP</em><br>
  <img src="screenshots/Screen Shot - MCPSetting.png">
</p>

| Chat de MCP | Chat de MCP | Chat de MCP | Chat de MCP |
| :---: | :---: | :---: | :---: |
| <img src="screenshots/Screen Shot - MCPChat.jpg" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-1.png" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-2.png" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-3.png" width="250"/> |

| Estado del Libro de Koreader | Sincronización de Koreader |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderBookStatus.jpg" width="400"/> | <img src="screenshots/Screen Shot - KoreaderSync.jpg" width="400"/> |

| Configuración de Koreader | WebDAV de Koreader |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderSetting.png" width="750"/> | <img src="screenshots/Screen Shot - KoreaderWebdav.jpg" width="250"/> |

<p align="center">
  <em>Página de Estadísticas</em><br>
  <img src="screenshots/Screen Shot - StatsPage.png">
</p>

| Lista de audiolibros | Reproductor de audiolibros |
| :---: | :---: |
| <img src="screenshots/Screen Shot - AudiobookList.png" width="400"/> | <img src="screenshots/Screen Shot - AudiobookPlayer.png" width="400"/> |

| Chatear con el libro | Chatear con el libro |
| :---: | :---: |
| <img src="screenshots/Screen Shot - ChatWithBook1.png" width="400"/> | <img src="screenshots/Screen Shot - ChatWithBook2.png" width="400"/> |

## 🚀 Despliegue

Esta aplicación está diseñada para ser desplegada usando Docker.

### Prerrequisitos

- [Docker](https://www.docker.com/get-started) instalado en tu servidor.
- Un servidor Calibre existente (opcional, pero necesario para la mayoría de las funciones). Recomendamos usar la imagen de Docker [linuxserver/calibre](https://hub.docker.com/r/linuxserver/calibre).

### Inicio Rápido (Docker Run)

Esta es la forma más sencilla de empezar.

1.  Crea dos directorios para los datos persistentes:
    ```bash
    mkdir -p ./config
    mkdir -p ./webdav
    ```

2.  Ejecuta el contenedor de Docker con este único comando:
    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -v $(pwd)/config:/config \
      -v $(pwd)/webdav:/webdav \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

3.  Accede a la aplicación en `http://localhost:5000`. El primer usuario que se registre se convertirá en el administrador. Puedes configurar la conexión al servidor de Calibre y otros ajustes desde la interfaz web más tarde.

### Configuración Avanzada

Aquí tienes un ejemplo más detallado de `docker-compose.yml` para usuarios que quieran conectarse a un servidor de Calibre y personalizar más opciones.

1.  **Encuentra tu ID de Usuario y Grupo (PUID/PGID):**
    Ejecuta `id $USER` en tu máquina anfitriona. Se recomienda para evitar problemas de permisos.

2.  **Crea un archivo `docker-compose.yml`:**
    ```yaml
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /ruta/a/tu/config:/config
          - /ruta/a/tu/webdav:/webdav
          - /ruta/a/tu/audiobooks:/audiobooks # Opcional
          - /ruta/a/tus/fuentes:/opt/share/fonts # Opcional
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=America/New_York
          - GUNICORN_WORKERS=2 # Opcional
          - SECRET_KEY=tu_clave_super_secreta # ¡Cambia esto!
          - CALIBRE_URL=http://ip-de-tu-servidor-calibre:8080
          - CALIBRE_USERNAME=tu_usuario_calibre
          - CALIBRE_PASSWORD=tu_contraseña_calibre
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    *Nota: Reemplaza `/ruta/a/tu/...` con las rutas reales en tu máquina anfitriona.*

3.  Ejecuta el contenedor:
    ```bash
    docker-compose up -d
    ```

### Fuentes Personalizadas

La herramienta de conversión de libros, `ebook-converter`, escanea el directorio `/opt/share/fonts` en busca de fuentes. Si encuentras problemas relacionados con las fuentes al convertir libros con caracteres especiales (por ejemplo, chino), puedes proporcionar fuentes personalizadas montando un directorio local que contenga tus archivos de fuentes (por ejemplo, `.ttf`, `.otf`) en la ruta `/opt/share/fonts` del contenedor.

### Configuración

La aplicación se configura a través de variables de entorno.

| Variable | Descripción | Predeterminado |
| --- | --- | --- |
| `PUID` | El ID de usuario con el que se ejecuta la aplicación. | `1001` |
| `PGID` | El ID de grupo con el que se ejecuta la aplicación. | `1001` |
| `TZ` | Tu zona horaria, ej., `America/New_York`. | `UTC` |
| `PORT` | El puerto en el que la aplicación escucha dentro del contenedor. | `5000` |
| `GUNICORN_WORKERS` | Opcional: El número de procesos de trabajo de Gunicorn. | `2` |
| `CONFIG_DIR` | El directorio para la base de datos y `settings.json`. | `/config` |
| `WEBDAV_DIR` | El directorio base para los archivos de usuario de WebDAV. | `/webdav` |
| `SECRET_KEY` | **Requerido.** Una cadena larga y aleatoria para la seguridad de la sesión. | `""` |
| `CALIBRE_URL` | La URL de tu servidor de contenido de Calibre. Consulta [Solución de Problemas](#1-por-qué-no-hay-libros-en-mi-lista-de-calibre) si tienes problemas de conexión. | `""` |
| `CALIBRE_USERNAME` | Nombre de usuario para tu servidor Calibre. Consulta [Solución de Problemas](#1-por-qué-no-hay-libros-en-mi-lista-de-calibre) si tienes problemas de conexión. | `""` |
| `CALIBRE_PASSWORD` | Contraseña para tu servidor Calibre. Consulta [Solución de Problemas](#1-por-qué-no-hay-libros-en-mi-lista-de-calibre) si tienes problemas de conexión. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | El ID de la biblioteca de Calibre predeterminada. Para más detalles, consulta [Cómo encuentro mi `library_id`](#4-cómo-encuentro-mi-library_id). | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Si se permite subir libros duplicados. | `false` |
| `REQUIRE_INVITE_CODE` | Si se requiere un código de invitación para el registro. | `true` |
| `SMTP_SERVER` | Servidor SMTP para enviar correos electrónicos (ej., para Kindle). | `""` |
| `SMTP_PORT` | Puerto SMTP. | `587` |
| `SMTP_USERNAME` | Nombre de usuario SMTP. | `""` |
| `SMTP_PASSWORD` | Contraseña SMTP. | `""` |
| `SMTP_ENCRYPTION` | Tipo de cifrado SMTP (`ssl`, `starttls`, `none`). | `ssl` |
| `DEFAULT_TTS_PROVIDER` | El proveedor de TTS predeterminado para la generación de audiolibros (`edge_tts` o `openai_tts`). | `edge_tts` |
| `DEFAULT_TTS_VOICE` | La voz predeterminada para el proveedor de TTS seleccionado. | `en-US-AriaNeural` |
| `DEFAULT_TTS_RATE` | La velocidad de habla predeterminada para el proveedor de TTS (por ejemplo, `+10%`). | `+0%` |
| `DEFAULT_OPENAI_API_KEY` | Tu clave de API de OpenAI (requerida si se usa `openai_tts`). | `""` |
| `DEFAULT_OPENAI_API_BASE_URL` | URL base personalizada para APIs compatibles con OpenAI. | `https://api.openai.com/v1` |
| `DEFAULT_OPENAI_API_MODEL` | El modelo de OpenAI a utilizar para TTS (por ejemplo, `tts-1`). | `tts-1` |
| `DEFAULT_LLM_BASE_URL` | La URL base para la API del Modelo de Lenguaje Grande (LLM), compatible con el formato de la API de OpenAI. | `""` |
| `DEFAULT_LLM_API_KEY` | La clave de API para el servicio LLM. | `""` |
| `DEFAULT_LLM_MODEL` | El modelo predeterminado a utilizar para el servicio LLM (por ejemplo, `gpt-4`). | `""` |

## 🔧 Solución de Problemas

Aquí hay algunos problemas comunes y sus soluciones:

### 1. ¿Por qué no hay libros en mi lista de Calibre?

*   **R**: Asegúrate de haber iniciado el Servidor de Contenido de Calibre en tu cliente o contenedor de Calibre. Generalmente se ejecuta en el puerto `8080`. Recuerda que esta aplicación se conecta a `calibre-server`, no a `calibre-web` (que normalmente se ejecuta en el puerto `8083`).
*   **R**: Verifica que la URL de tu servidor Calibre, el nombre de usuario y la contraseña sean correctos en la configuración. Puedes probar esto abriendo la URL configurada en tu navegador e intentando iniciar sesión.

### 2. ¿Por qué recibo un error `401 Unauthorized` al subir/editar libros?

*   **R**: Asegúrate de que la cuenta de usuario de Calibre que configuraste tenga permisos de escritura para la biblioteca. Para verificarlo, ve a `Preferencias` -> `Compartir por la red` -> `Cuentas de usuario` en la aplicación de escritorio de Calibre y asegúrate de que la opción "Permitir acceso de escritura" esté marcada para el usuario.

### 3. ¿Por qué recibo un error `403 Forbidden` al subir/editar libros?

*   **R**: Esto generalmente significa que has configurado un ID de Biblioteca de Calibre incorrecto.

### 4. ¿Cómo encuentro mi `library_id`?

*   **Método 1 (Visual)**: Abre tu Servidor de Contenido de Calibre en un navegador e inicia sesión. Mira el nombre de tu biblioteca que se muestra en la página. El `library_id` suele ser este nombre con los espacios y caracteres especiales reemplazados por guiones bajos. Por ejemplo, si tu biblioteca se llama "Calibre Library", el ID probablemente sea `Calibre_Library`.
*   **Método 2 (Desde la URL)**: En la interfaz del Servidor de Contenido, haz clic en el nombre de tu biblioteca. Mira la URL en la barra de direcciones de tu navegador. Deberías ver un parámetro como `library_id=...`. El valor de este parámetro es tu ID de biblioteca (podría estar codificado para URL, por lo que es posible que necesites decodificarlo).
*   **IDs Predeterminados Comunes**: El ID de la biblioteca predeterminada a menudo depende del idioma de tu sistema cuando ejecutaste Calibre por primera vez. Aquí hay algunos valores predeterminados comunes:
    *   Inglés: `Calibre_Library`
    *   Francés: `Bibliothèque_calibre`
    *   Alemán: `Calibre-Bibliothek`
    *   Español: `Biblioteca_de_calibre`
    *   Chino Simplificado (简体中文): `Calibre_书库`
    *   Chino Tradicional (繁體中文): `calibre_書庫`

### 5. ¿Por qué recibo un error `400 Bad Request` al editar la fecha de lectura o los campos de la biblioteca?

*   **R**: Este error ocurre porque a tu biblioteca de Calibre le faltan las columnas personalizadas necesarias para almacenar esta información. Para habilitar funciones como el seguimiento de quién subió/es dueño de un libro y establecer una fecha de lectura específica, necesitas añadir dos columnas personalizadas en tu aplicación de escritorio de Calibre:
    1.  Ve a `Preferencias` -> `Añadir columnas personalizadas`.
    2.  Haz clic en `Añadir columna personalizada`.
    3.  Crea la primera columna con los siguientes detalles:
        *   **Nombre de búsqueda**: `#library`
        *   **Encabezado de columna**: `Library` (o como prefieras)
        *   **Tipo de columna**: `Texto, con comas tratadas como etiquetas separadas`
    4.  Crea la segunda columna con estos detalles:
        *   **Nombre de búsqueda**: `#readdate`
        *   **Encabezado de columna**: `Read Date` (o como prefieras)
        *   **Tipo de columna**: `Fecha`
    5.  Haz clic en `Aplicar` y reinicia tu servidor de Calibre si está en funcionamiento. Después de añadir estas columnas, las funciones de edición funcionarán correctamente.

## 📖 Sincronización con KOReader

Puedes sincronizar tu progreso de lectura y tiempo de lectura entre tu biblioteca Anx y los dispositivos KOReader. La configuración implica dos pasos principales: configurar WebDAV para acceder a tus libros y configurar el complemento de sincronización para manejar la sincronización del progreso.

### Paso 1: Configurar Almacenamiento en la Nube WebDAV

Este paso te permite navegar y leer los libros de tu biblioteca Anx directamente en KOReader.

1.  En KOReader, ve a `Almacenamiento en la nube` -> `Añadir nuevo almacenamiento en la nube`.
2.  Selecciona `WebDAV`.
3.  Completa los detalles:
    -   **Dirección del servidor**: Ingresa la URL de WebDAV que se muestra en la página de configuración de Anx Calibre Manager (`Configuración` -> `Configuración de Sincronización de Koreader`). **Asegúrate de que la ruta termine con un `/`**.
    -   **Nombre de usuario**: Tu nombre de usuario de Anx Calibre Manager.
    -   **Contraseña**: Tu contraseña de inicio de sesión de Anx Calibre Manager.
    -   **Carpeta**: `/anx/data/file`
4.  Toca `Conectar` y guarda. Ahora deberías poder ver tu biblioteca Anx en el explorador de archivos de KOReader.

### Paso 2: Instalar y Configurar el Complemento de Sincronización

Este complemento envía tu progreso de lectura de vuelta al servidor de Anx Calibre Manager.

1.  **Descargar el Complemento**:
    -   Inicia sesión en Anx Calibre Manager.
    -   Ve a `Configuración` -> `Configuración de Sincronización de Koreader`.
    -   Haz clic en el botón `Descargar Complemento de KOReader (.zip)` para obtener el paquete del complemento.
2.  **Instalar el Complemento**:
    -   Descomprime el archivo descargado para obtener una carpeta llamada `anx-calibre-manager-koreader-plugin.koplugin`.
    -   Copia esta carpeta completa al directorio `koreader/plugins/` en tu dispositivo KOReader.
3.  **Reiniciar KOReader**: Cierra y vuelve a abrir completamente la aplicación KOReader para cargar el nuevo complemento.
4.  **Configurar el Servidor de Sincronización**:
    -   **Importante**: Primero, abre un libro desde el almacenamiento WebDAV que configuraste en el Paso 1. El menú del complemento **solo es visible en la vista de lectura**.
    -   En la vista de lectura, ve a `Herramientas (icono de llave inglesa)` -> `Página siguiente` -> `Más herramientas` -> `ANX Calibre Manager`.
    -   Selecciona `Servidor de sincronización personalizado`.
    -   **Dirección del servidor de sincronización personalizado**: Ingresa la URL del servidor de sincronización que se muestra en la página de configuración de Anx Calibre Manager (ej., `http://<tu_direccion_de_servidor>/koreader`).
    -   Vuelve al menú anterior, selecciona `Iniciar sesión` e ingresa tu nombre de usuario y contraseña de Anx Calibre Manager.

Una vez configurado, el complemento sincronizará automática o manualmente tu progreso de lectura. Puedes ajustar configuraciones como la frecuencia de sincronización en el menú del complemento. **Nota: Solo se admite el progreso de libros en formato EPUB.**

## 🤖 Servidor MCP

Esta aplicación incluye un servidor MCP (Protocolo de Contexto de Modelo) compatible con JSON-RPC 2.0, que permite a herramientas externas y agentes de IA interactuar con tu biblioteca.

### Cómo Usar

1.  **Generar un Token**: Después de iniciar sesión, ve a la página **Configuración -> Configuración de MCP**. Haz clic en "Generar Nuevo Token" para crear un nuevo token de API.
2.  **URL del Endpoint**: El endpoint del servidor MCP es `http://<tu_direccion_de_servidor>/mcp`.
3.  **Autenticación**: Autentícate añadiendo tu token como un parámetro de consulta a la URL, ej., `http://.../mcp?token=TU_TOKEN`.
4.  **Enviar Solicitudes**: Envía solicitudes `POST` a este endpoint con un cuerpo que cumpla con el formato JSON-RPC 2.0.

### Ejemplos de Prompts

Aquí tienes algunos ejemplos de prompts en lenguaje natural que podrías usar con un agente de IA que tenga acceso a estas herramientas. El agente llamaría de forma inteligente a una o más herramientas para satisfacer tu solicitud.

- **Búsqueda Simple y Avanzada**:
  - > "Encuentra libros sobre programación en Python."
  - > "Busca libros de ciencia ficción de Isaac Asimov publicados después de 1950."

- **Gestión de Libros**:
  - > "¿Cuáles son los 5 libros añadidos más recientemente? Envía el primero a mi Kindle."
  - > "Empuja el libro 'Dune' a mi lector Anx."
  - > "Genera un audiolibro para el libro 'El problema de los tres cuerpos'."
  - > "¿Cuál es el estado de la generación del audiolibro para 'El problema de los tres cuerpos'?"

- **Interacción y Resumen de Contenido**:
  - > "Muéstrame la tabla de contenidos del libro 'Fundación'."
  - > "Obtén el primer capítulo de 'Fundación' y dame un resumen."
  - > "Basado en el capítulo 'Los Psicohistoriadores' del libro 'Fundación', ¿cuáles son las ideas principales de la psicohistoria?"
  - > "Lee el libro completo 'El Principito' y dime cuál es el secreto del zorro."

- **Estadísticas y Progreso de Lectura**:
  - > "¿Cuántas palabras tiene el libro 'Dune' en total y enumera el recuento de palabras de cada capítulo?"
  - > "¿Cuántos libros he leído este año?"
  - > "¿Cuál es mi progreso de lectura en 'Dune'?"
  - > "¿Quién es el autor de 'Proyecto Hail Mary' y cuánto tiempo llevo leyéndolo?"

### Herramientas Disponibles

Puedes obtener una lista de todas las herramientas disponibles llamando al método `tools/list`. Las herramientas actualmente soportadas son:

-   **`search_calibre_books`**: Busca libros en Calibre utilizando la potente sintaxis de búsqueda de Calibre.
    -   **Parámetros**: `search_expression` (cadena), `limit` (entero, opcional).
    -   **Ejemplo (Búsqueda Avanzada)**: Encuentra libros de "O'Reilly Media" con una calificación de 4 estrellas o más.
        ```json
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_calibre_books",
                "arguments": {
                    "search_expression": "publisher:\"O'Reilly Media\" AND rating:>=4",
                    "limit": 10
                }
            },
            "id": "search-request-1"
        }
        ```
-   **`get_recent_books`**: Obtiene libros recientes de una biblioteca específica.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `limit` (entero, opcional).
-   **`get_book_details`**: Obtiene detalles de un libro específico en una biblioteca.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).
-   **`push_calibre_book_to_anx`**: Envía un libro de la biblioteca de Calibre a la biblioteca Anx del usuario.
    -   **Parámetros**: `book_id` (entero).
-   **`send_calibre_book_to_kindle`**: Envía un libro de la biblioteca de Calibre al correo electrónico de Kindle configurado por el usuario.
    -   **Parámetros**: `book_id` (entero).
-   **`get_table_of_contents`**: Obtiene la tabla de contenidos de un libro de una biblioteca específica.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).
-   **`get_chapter_content`**: Obtiene el contenido de un capítulo específico de un libro.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero), `chapter_number` (entero).
-   **`get_entire_book_content`**: Obtiene el contenido de texto completo de un libro de una biblioteca específica.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).
-   **`get_word_count_statistics`**: Obtiene estadísticas de recuento de palabras para un libro (total y por capítulo).
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).
-   **`generate_audiobook`**: Genera un audiolibro para un libro de la biblioteca Anx o Calibre.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).
-   **`get_audiobook_generation_status`**: Obtiene el estado de una tarea de generación de audiolibros por su ID de tarea.
    -   **Parámetros**: `task_id` (cadena).
-   **`get_audiobook_status_by_book`**: Obtiene el estado de la última tarea de audiolibro para un libro específico por su ID y tipo de biblioteca.
    -   **Parámetros**: `library_type` (cadena, 'anx' o 'calibre'), `book_id` (entero).

## 💻 Desarrollo

1.  **Clona el repositorio:**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **Crea un entorno virtual:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Instala las dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Ejecuta el servidor de desarrollo:**
    ```bash
    python app.py
    ```
    La aplicación estará disponible en `http://localhost:5000`.

## 🤝 Contribuciones

¡Las contribuciones, problemas y solicitudes de características son bienvenidos! Siéntete libre de revisar la [página de problemas](https://github.com/ptbsare/anx-calibre-manager/issues).

## 🙏 Agradecimientos

Este proyecto utiliza los siguientes proyectos de código abierto:

-   [foliate-js](https://github.com/johnfactotum/foliate-js) por proporcionar la funcionalidad de vista previa de libros electrónicos.
-   [ebook-converter](https://github.com/gryf/ebook-converter) por proporcionar la funcionalidad de conversión de libros electrónicos.

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia GPLv3.