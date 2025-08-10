# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

一个现代化的、移动端优先的 Web 应用，用于管理您的电子书库，可与 Calibre 集成，并为您的 Anx-reader 兼容设备提供个人 WebDAV 服务器。

[Read in English](README.md)

## ✨ 功能特性

- **移动端优先界面**: 简洁、响应式的用户界面，专为在手机上轻松使用而设计。
- **PWA 支持**: 可作为渐进式 Web 应用 (PWA) 安装，提供类似原生应用的体验。
- **Calibre 集成**: 连接到您现有的 Calibre 服务器，以浏览和搜索您的书库。
- **推送到 Anx**: 将书籍从您的 Calibre 书库直接发送到您的个人 Anx-reader 设备文件夹。
- **集成的 WebDAV 服务器**: 每个用户都会获得自己独立、安全的 WebDAV 文件夹，与 Anx-reader 和其他 WebDAV 客户端兼容。
- **用户管理**: 简单、内置的用户管理系统。
- **轻松部署**: 可作为单个 Docker 容器进行部署。

## 🚀 部署

本应用设计为使用 Docker 进行部署。

### 先决条件

- 您的服务器上已安装 [Docker](https://www.docker.com/get-started)。
- 一个正在运行的 Calibre 服务器 (可选，但大部分功能需要)。

### 使用 Docker 运行

1.  **创建数据目录:**
    此目录将用于存储应用的数据库、配置文件和 WebDAV 文件。

    ```bash
    mkdir -p /path/to/your/appdata
    ```

2.  **运行 Docker 容器:**
    您可以使用 `docker run` 或 `docker-compose.yml` 文件。

    **使用 `docker run`:**

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
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **使用 `docker-compose.yml`:**

    创建一个 `docker-compose.yml` 文件:
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
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
    然后运行:
    ```bash
    docker-compose up -d
    ```

### 配置

应用通过环境变量进行配置。

| 变量 | 描述 | 默认值 |
| --- | --- | --- |
| `PORT` | 应用在容器内监听的端口。 | `5000` |
| `DATA_DIR` | 所有持久化数据 (数据库, 配置, WebDAV) 的基础目录。 | `/data` |
| `SECRET_KEY` | **必需。** 用于会话安全的、长的、随机的字符串。 | `""` |
| `CALIBRE_URL` | 您的 Calibre 内容服务器的 URL。 | `""` |
| `CALIBRE_USERNAME` | 您的 Calibre 服务器的用户名。 | `""` |
| `CALIBRE_PASSWORD` | 您的 Calibre 服务器的密码。 | `""` |
| `SMTP_SERVER` | 用于发送邮件 (例如，推送到 Kindle) 的 SMTP 服务器。 | `""` |
| `SMTP_PORT` | SMTP 端口。 | `587` |
| `SMTP_USERNAME` | SMTP 用户名。 | `""` |
| `SMTP_PASSWORD` | SMTP 密码。 | `""` |
| `SMTP_ENCRYPTION` | SMTP 加密类型 (`ssl`, `starttls`, `none`)。 | `ssl` |

## 💻 开发

1.  **克隆仓库:**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **创建虚拟环境:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **安装依赖:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **运行开发服务器:**
    ```bash
    python app.py
    ```
    应用将在 `http://localhost:5000` 上可用。

## 🤝 贡献

欢迎提交贡献、问题和功能请求！请随时查看 [问题页面](https://github.com/ptbsare/anx-calibre-manager/issues)。

## 📄 许可证

本项目采用 MIT 许可证。