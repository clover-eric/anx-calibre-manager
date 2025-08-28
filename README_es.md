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
- **Libros Subidos Editables por el Usuario**: Los usuarios regulares ahora pueden editar los metadatos de los libros que han subido. Esta funcionalidad se basa en una columna personalizada de Calibre llamada `#library` (tipo: `Texto, con comas tratadas como etiquetas separadas`). Cuando un usuario sube un libro, este campo se rellena automáticamente con `<nombredeusuario>上传`. Los usuarios pueden editar cualquier libro donde `#library` contenga su nombre de usuario seguido de "上传".
    - **Recomendación para Usuarios de Docker**: Para habilitar esta función, asegúrate de tener una columna personalizada en tu biblioteca de Calibre llamada `#library` (sensible a mayúsculas y minúsculas) con el tipo `Texto, con comas tratadas como etiquetas separadas`.
- **Despliegue Fácil**: Desplegable como un único contenedor de Docker con soporte de localización multilingüe incorporado.
- **Estadísticas de Lectura**: Genera automáticamente una página personal de estadísticas de lectura, con un mapa de calor de lectura anual, una lista de libros que se están leyendo actualmente y una lista de libros terminados. La página se puede compartir públicamente o mantener privada.

## 📸 Capturas de Pantalla

![Interfaz Principal](Screen%20Shot%20-%20Main.png)![Página de Configuración](Screen%20Shot%20-%20Setting.png)![Configuración de MCP](Screen%20Shot%20-%20MCP.png)![Página de Koreader](Screen%20Shot%20-%20Koreader.png)![Página de Estadísticas](Screen%20Shot%20-%20Stats.png)

## 🚀 Despliegue

Esta aplicación está diseñada para ser desplegada usando Docker.

### Prerrequisitos

- [Docker](https://www.docker.com/get-started) instalado en tu servidor.
- Un servidor Calibre existente (opcional, pero necesario para la mayoría de las funciones).

### Ejecutar con Docker

1.  **Encuentra tu ID de Usuario y Grupo (PUID/PGID):**
    Ejecuta `id $USER` en tu máquina anfitriona para obtener el UID y GID de tu usuario. Esto es crucial para evitar problemas de permisos con los volúmenes montados.

    ```bash
    id $USER
    # Salida de ejemplo: uid=1000(miusuario) gid=1000(miusuario) ...
    ```

2.  **Crea directorios para datos persistentes:**
    Necesitas directorios separados para la configuración/base de datos y para los datos de WebDAV.

    ```bash
    mkdir -p /ruta/a/tu/config
    mkdir -p /ruta/a/tu/webdav
    mkdir -p /ruta/a/tus/fuentes # Opcional: para fuentes personalizadas
    ```

3.  **Ejecuta el contenedor de Docker:**
    Puedes usar `docker run` o un archivo `docker-compose.yml`.

    **Usando `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="America/New_York" \
      -v /ruta/a/tu/config:/config \
      -v /ruta/a/tu/webdav:/webdav \
      -v /ruta/a/tus/fuentes:/opt/share/fonts \ # Opcional: Montar fuentes personalizadas
      -e "GUNICORN_WORKERS=2" \ 
      -e "SECRET_KEY=tu_clave_super_secreta" \
      -e "CALIBRE_URL=http://ip-de-tu-servidor-calibre:8080" \
      -e "CALIBRE_USERNAME=tu_usuario_calibre" \
      -e "CALIBRE_PASSWORD=tu_contraseña_calibre" \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **Usando `docker-compose.yml`:**

    Crea un archivo `docker-compose.yml`:
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /ruta/a/tu/config:/config
          - /ruta/a/tu/webdav:/webdav
          - /ruta/a/tus/fuentes:/opt/share/fonts # Opcional: Montar fuentes personalizadas
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=America/New_York
          - GUNICORN_WORKERS=2 # Opcional: Personaliza el número de procesos de trabajo de Gunicorn
          - SECRET_KEY=tu_clave_super_secreta
          - CALIBRE_URL=http://ip-de-tu-servidor-calibre:8080
          - CALIBRE_USERNAME=tu_usuario_calibre
          - CALIBRE_PASSWORD=tu_contraseña_calibre
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    Luego ejecuta:
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
| `CALIBRE_URL` | La URL de tu servidor de contenido de Calibre. | `""` |
| `CALIBRE_USERNAME` | Nombre de usuario para tu servidor Calibre. | `""` |
| `CALIBRE_PASSWORD` | Contraseña para tu servidor Calibre. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | El ID de la biblioteca de Calibre predeterminada para navegar, buscar y subir libros. | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Si se permite subir libros duplicados. | `false` |
| `SMTP_SERVER` | Servidor SMTP para enviar correos electrónicos (ej., para Kindle). | `""` |
| `SMTP_PORT` | Puerto SMTP. | `587` |
| `SMTP_USERNAME` | Nombre de usuario SMTP. | `""` |
| `SMTP_PASSWORD` | Contraseña SMTP. | `""` |
| `SMTP_ENCRYPTION` | Tipo de cifrado SMTP (`ssl`, `starttls`, `none`). | `ssl` |

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

### Herramientas Disponibles

Puedes obtener una lista de todas las herramientas disponibles llamando al método `tools/list`. Las herramientas actualmente soportadas son:

-   **`search_calibre_books`**: Busca libros usando la potente sintaxis de búsqueda de Calibre.
    -   **Parámetros**: `search_expression` (cadena), `limit` (entero, opcional).
    -   **Funcionalidad**: Puedes proporcionar palabras clave simples para una búsqueda amplia o construir consultas complejas.
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
-   `get_recent_calibre_books`: Obtiene libros recientes de la biblioteca de Calibre.
-   `get_calibre_book_details`: Obtiene detalles de un libro específico de Calibre.
-   `get_recent_anx_books`: Obtiene libros recientes de la biblioteca Anx.
-   `get_anx_book_details`: Obtiene detalles de un libro específico de Anx.
-   `push_calibre_book_to_anx`: Envía un libro de Calibre a la biblioteca Anx.
-   `send_calibre_book_to_kindle`: Envía un libro de Calibre a Kindle.

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

## 📄 Licencia

Este proyecto está licenciado bajo la Licencia MIT.