# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

A modern, mobile-first web application to manage your ebook library, integrating with Calibre and providing a personal WebDAV server for your Anx-reader compatible devices.

[阅读中文版说明](README.zh-CN.md)

## ✨ Features

- **Mobile-First Interface**: A clean, responsive UI designed for easy use on your phone.
- **PWA Support**: Installable as a Progressive Web App for a native-like experience.
- **Calibre Integration**: Connects to your existing Calibre server to browse and search your library.
- **Push to Anx**: Send books from your Calibre library directly to your personal Anx-reader device folder.
- **Integrated WebDAV Server**: Each user gets their own secure WebDAV folder, compatible with Anx-reader and other WebDAV clients.
- **User Management**: Simple, built-in user management system.
- **Easy Deployment**: Deployable as a single Docker container.
## 📸 Screenshots

| Main Interface | Settings Page |
| :---: | :---: |
| ![Main Interface](Screen%20Shot%20-%20Main.png) | ![Settings Page](Screen%20Shot%20-%20Setting.png) |


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
      -e TZ="Asia/Shanghai" \
      -v /path/to/your/config:/config \
      -v /path/to/your/webdav:/webdav \
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
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Asia/Shanghai
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

### Configuration

The application is configured via environment variables.

| Variable | Description | Default |
| --- | --- | --- |
| `PUID` | The User ID to run the application as. | `1001` |
| `PGID` | The Group ID to run the application as. | `1001` |
| `TZ` | Your timezone, e.g., `America/New_York`. | `UTC` |
| `PORT` | The port the application listens on inside the container. | `5000` |
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
