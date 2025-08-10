# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml)
[![Docker Hub](https://img.shields.io/docker/pulls/ptbsare/anx-calibre-manager.svg)](https://hub.docker.com/r/ptbsare/anx-calibre-manager)

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

## 🚀 Deployment

This application is designed to be deployed using Docker.

### Prerequisites

- [Docker](https://www.docker.com/get-started) installed on your server.
- An existing Calibre server (optional, but required for most features).

### Running with Docker

1.  **Create a data directory:**
    This directory will store the application's database, configuration, and WebDAV files.

    ```bash
    mkdir -p /path/to/your/appdata
    ```

2.  **Run the Docker container:**
    You can use `docker run` or a `docker-compose.yml` file.

    **Using `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -v /path/to/your/appdata:/data \
      -e "SECRET_KEY=your_super_secret_key" \
      -e "CALIBRE_URL=http://your-calibre-server-ip:8080" \
      -e "CALIBRE_USERNAME=your_calibre_username" \
      -e "CALIBRE_PASSWORD=your_calibre_password" \
      --restart unless-stopped \
      ptbsare/anx-calibre-manager:latest
    ```

    **Using `docker-compose.yml`:**

    Create a `docker-compose.yml` file:
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /path/to/your/appdata:/data
        environment:
          - SECRET_KEY=your_super_secret_key
          - CALIBRE_URL=http://your-calibre-server-ip:8080
          - CALIBRE_USERNAME=your_calibre_username
          - CALIBRE_PASSWORD=your_calibre_password
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
| `PORT` | The port the application listens on inside the container. | `5000` |
| `DATA_DIR` | The base directory for all persistent data (database, config, WebDAV). | `/data` |
| `SECRET_KEY` | **Required.** A long, random string for session security. | `""` |
| `CALIBRE_URL` | The URL of your Calibre content server. | `""` |
| `CALIBRE_USERNAME` | Username for your Calibre server. | `""` |
| `CALIBRE_PASSWORD` | Password for your Calibre server. | `""` |
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
