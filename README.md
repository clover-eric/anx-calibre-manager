# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

A modern, mobile-first web application to manage your ebook library, integrating with Calibre and providing a personal WebDAV server for your Anx-reader compatible devices.

[阅读中文版说明](README.zh-CN.md)

## ✨ Features

- **Mobile-First Interface**: A clean, responsive UI designed for easy use on your phone.
- **PWA Support**: Installable as a Progressive Web App for a native-like experience.
- **Calibre Integration**: Connects to your existing Calibre server to browse and search your library.
- **Smart Send to Kindle**: Automatically handles formats when sending to your Kindle. If an EPUB exists, it's sent directly. If not, the app **converts the best available format to EPUB** based on your preferences before sending, ensuring optimal compatibility.
- **Push to Anx**: Send books from your Calibre library directly to your personal Anx-reader device folder.
- **Integrated WebDAV Server**: Each user gets their own secure WebDAV folder, compatible with Anx-reader and other WebDAV clients.
- **MCP Server**: A built-in, compliant Model Context Protocol (MCP) server, allowing AI agents and external tools to interact with your library securely.
- **User Management**: Simple, built-in user management system.
- **Easy Deployment**: Deployable as a single Docker container.
## 📸 Screenshots

![Main Interface](Screen%20Shot%20-%20Main.png)![Settings Page](Screen%20Shot%20-%20Setting.png)![MCP Settings](Screen%20Shot%20-%20MCP.png)

## 🚀 Deployment

This application is designed to be deployed using Docker.

### Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your server.
- An existing Calibre server (optional, but required for most features).

### Running with Docker

1.  **Find your User and Group ID (PUID/PGID):**
    Run `id $USER` on your host machine to get your user's UID and GID. This is crucial for avoiding permission issues with the mounted volumes.

    ```bash
    id $USER
    # Example output: uid=1000(myuser) gid=1000(myuser) ...
    ```

2.  **Create directories for persistent data:**
    You need separate directories for configuration/database and for WebDAV data.

    ```bash
    mkdir -p /path/to/your/config
    mkdir -p /path/to/your/webdav
    mkdir -p /path/to/your/fonts # Optional: for custom fonts
    ```

3.  **Run the Docker container:**
    You can use `docker run` or a `docker-compose.yml` file.

    **Using `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="America/New_York" \
      -v /path/to/your/config:/config \
      -v /path/to/your/webdav:/webdav \
      -v /path/to/your/fonts:/opt/share/fonts \ # Optional: Mount custom fonts
      -e "GUNICORN_WORKERS=2" \ 
      -e "SECRET_KEY=your_super_secret_key" \
      -e "CALIBRE_URL=http://your-calibre-server-ip:8080" \
      -e "CALIBRE_USERNAME=your_calibre_username" \
      -e "CALIBRE_PASSWORD=your_calibre_password" \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **Using `docker-compose.yml`:**

    Create a `docker-compose.yml` file:
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /path/to/your/config:/config
          - /path/to/your/webdav:/webdav
          - /path/to/your/fonts:/opt/share/fonts # Optional: Mount custom fonts
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=America/New_York
          - GUNICORN_WORKERS=2 # Optional: Customize the number of Gunicorn worker processes
          - SECRET_KEY=your_super_secret_key
          - CALIBRE_URL=http://your-calibre-server-ip:8080
          - CALIBRE_USERNAME=your_calibre_username
          - CALIBRE_PASSWORD=your_calibre_password
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    Then run:
    ```bash
    docker-compose up -d
    ```

### Custom Fonts

The book conversion tool, `ebook-converter`, scans the `/opt/share/fonts` directory for fonts. If you encounter font-related issues when converting books with special characters (e.g., Chinese), you can provide custom fonts by mounting a local directory containing your font files (e.g., `.ttf`, `.otf`) to the container's `/opt/share/fonts` path.

### Configuration

The application is configured via environment variables.

| Variable | Description | Default |
| --- | --- | --- |
| `PUID` | The User ID to run the application as. | `1001` |
| `PGID` | The Group ID to run the application as. | `1001` |
| `TZ` | Your timezone, e.g., `America/New_York`. | `UTC` |
| `PORT` | The port the application listens on inside the container. | `5000` |
| `GUNICORN_WORKERS` | Optional: The number of Gunicorn worker processes. | `2` |
| `CONFIG_DIR` | The directory for the database and `settings.json`. | `/config` |
| `WEBDAV_DIR` | The base directory for WebDAV user files. | `/webdav` |
| `SECRET_KEY` | **Required.** A long, random string for session security. | `""` |
| `CALIBRE_URL` | The URL of your Calibre content server. | `""` |
| `CALIBRE_USERNAME` | Username for your Calibre server. | `""` |
| `CALIBRE_PASSWORD` | Password for your Calibre server. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | The default Calibre library ID for browsing, searching, and uploading books. | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Whether to allow uploading duplicate books. | `false` |
| `SMTP_SERVER` | SMTP server for sending emails (e.g., for Kindle). | `""` |
| `SMTP_PORT` | SMTP port. | `587` |
| `SMTP_USERNAME` | SMTP username. | `""` |
| `SMTP_PASSWORD` | SMTP password. | `""` |
| `SMTP_ENCRYPTION` | SMTP encryption type (`ssl`, `starttls`, `none`). | `ssl` |

## 🤖 MCP Server

This application includes a JSON-RPC 2.0 compliant MCP (Model Context Protocol) server, allowing external tools and AI agents to interact with your library.

### How to Use

1.  **Generate a Token**: After logging in, go to the **Settings -> MCP Settings** page. Click "Generate New Token" to create a new API token.
2.  **Endpoint URL**: The MCP server endpoint is `http://<your_server_address>/mcp`.
3.  **Authentication**: Authenticate by appending your token as a query parameter to the URL, e.g., `http://.../mcp?token=YOUR_TOKEN`.
4.  **Send Requests**: Send `POST` requests to this endpoint with a body compliant with the JSON-RPC 2.0 format.

### Available Tools

You can get a list of all available tools by calling the `tools/list` method. The currently supported tools are:

-   `search_calibre_books`: Search for books in the Calibre library.
-   `get_recent_calibre_books`: Get recent books from the Calibre library.
-   `get_calibre_book_details`: Get details for a specific Calibre book.
-   `get_recent_anx_books`: Get recent books from the Anx library.
-   `get_anx_book_details`: Get details for a specific Anx book.
-   `push_calibre_book_to_anx`: Push a Calibre book to the Anx library.
-   `send_calibre_book_to_kindle`: Send a Calibre book to Kindle.

## 💻 Development

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **Create a virtual environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run the development server:**
    ```bash
    python app.py
    ```
    The app will be available at `http://localhost:5000`.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the [issues page](https://github.com/ptbsare/anx-calibre-manager/issues).

## 📄 License

This project is licensed under the MIT License.
