# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-publish.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

一个现代化的、移动端优先的 Web 应用，用于管理您的电子书库，可与 Calibre 集成，并为您的 Anx-reader 兼容设备提供个人 WebDAV 服务器。

[Read in English](README.md)

## ✨ 功能特性

- **移动端优先界面**: 简洁、响应式的用户界面，专为在手机上轻松使用而设计。
- **PWA 支持**: 可作为渐进式 Web 应用 (PWA) 安装，提供类似原生应用的体验。
- **Calibre 集成**: 连接到您现有的 Calibre 服务器，以浏览和搜索您的书库。
- **KOReader 同步**: 与您的 KOReader 设备同步阅读进度。
- **智能推送到 Kindle**: 发送书籍到您的 Kindle 时，应用会自动处理格式。如果书籍已有 EPUB 格式，则直接发送；如果没有，它将根据您的格式偏好设置，自动将最优先的可用格式**转换为 EPUB**后再发送，以确保最佳兼容性。
- **推送到 Anx**: 将书籍从您的 Calibre 书库直接发送到您的个人 Anx-reader 设备文件夹。
- **集成的 WebDAV 服务器**: 每个用户都会获得自己独立、安全的 WebDAV 文件夹，与 Anx-reader 和其他 WebDAV 客户端兼容。
- **MCP 服务器**: 内置一个符合规范的 Model Context Protocol (MCP) 服务器，允许 AI 代理和外部工具安全地与您的书库交互。
- **用户管理**: 简单、内置的用户管理系统。
- **轻松部署**: 可作为单个 Docker 容器进行部署。
## 📸 截图

![主界面](Screen%20Shot%20-%20Main.png)![设置页面](Screen%20Shot%20-%20Setting.png)![MCP 设置](Screen%20Shot%20-%20MCP.png)

## 🚀 部署

本应用设计为使用 Docker 进行部署。

### 先决条件

- 您的服务器上已安装 [Docker](https://www.docker.com/get-started)。
- 一个正在运行的 Calibre 服务器 (可选，但大部分功能需要)。

### 使用 Docker 运行

1.  **获取您的用户和组 ID (PUID/PGID):**
    在您的宿主机上运行 `id $USER` 来获取您当前用户的 UID 和 GID。这对于避免挂载卷的权限问题至关重要。

    ```bash
    id $USER
    # 示例输出: uid=1000(myuser) gid=1000(myuser) ...
    ```

2.  **创建持久化数据目录:**
    您需要为配置/数据库和 WebDAV 数据分别创建目录。

    ```bash
    mkdir -p /path/to/your/config
    mkdir -p /path/to/your/webdav
    mkdir -p /path/to/your/fonts # 可选：用于自定义字体
    ```

3.  **运行 Docker 容器:**
    您可以使用 `docker run` 或 `docker-compose.yml` 文件。

    **使用 `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="Asia/Shanghai" \
      -v /path/to/your/config:/config \
      -v /path/to/your/webdav:/webdav \
      -v /path/to/your/fonts:/opt/share/fonts \ # 可选：挂载自定义字体
      -e "GUNICORN_WORKERS=2" \ 
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
          - /path/to/your/config:/config
          - /path/to/your/webdav:/webdav
          - /path/to/your/fonts:/opt/share/fonts # 可选：挂载自定义字体
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Asia/Shanghai
          - GUNICORN_WORKERS=2 # 可选：自定义 Gunicorn worker 进程的数量
          - SECRET_KEY=your_super_secret_key
          - CALIBRE_URL=http://your-calibre-server-ip:8080
          - CALIBRE_USERNAME=your_calibre_username
          - CALIBRE_PASSWORD=your_calibre_password
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    然后运行:
    ```bash
    docker-compose up -d
    ```

### 自定义字体

书籍格式转换工具 `ebook-converter` 会扫描 `/opt/share/fonts` 目录以查找字体。如果您在转换某些包含特殊字符（如中文）的书籍时遇到字体问题，可以通过挂载一个包含您所需字体文件（例如 `.ttf`, `.otf`）的本地目录到容器的 `/opt/share/fonts` 路径来提供自定义字体。

### 配置

应用通过环境变量进行配置。

| 变量 | 描述 | 默认值 |
| --- | --- | --- |
| `PUID` | 指定运行应用的用户 ID。 | `1001` |
| `PGID` | 指定运行应用的组 ID。 | `1001` |
| `TZ` | 您的时区, 例如 `America/New_York`。 | `UTC` |
| `PORT` | 应用在容器内监听的端口。 | `5000` |
| `GUNICORN_WORKERS` | 可选：Gunicorn worker 进程的数量。 | `2` |
| `CONFIG_DIR` | 用于存放数据库和 `settings.json` 的目录。 | `/config` |
| `WEBDAV_DIR` | 用于存放 WebDAV 用户文件的基础目录。 | `/webdav` |
| `SECRET_KEY` | **必需。** 用于会话安全的、长的、随机的字符串。 | `""` |
| `CALIBRE_URL` | 您的 Calibre 内容服务器的 URL。 | `""` |
| `CALIBRE_USERNAME` | 您的 Calibre 服务器的用户名。 | `""` |
| `CALIBRE_PASSWORD` | 您的 Calibre 服务器的密码。 | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | 用于浏览、搜索和上传书籍的默认 Calibre 库 ID。 | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | 是否允许上传重复的书籍。 | `false` |
| `SMTP_SERVER` | 用于发送邮件 (例如，推送到 Kindle) 的 SMTP 服务器。 | `""` |
| `SMTP_PORT` | SMTP 端口。 | `587` |
| `SMTP_USERNAME` | SMTP 用户名。 | `""` |
| `SMTP_PASSWORD` | SMTP 密码。 | `""` |
| `SMTP_ENCRYPTION` | SMTP 加密类型 (`ssl`, `starttls`, `none`)。 | `ssl` |

## 📖 KOReader 同步

您可以将您的 Anx 书库与 KOReader 设备的阅读进度进行同步。

### 使用方法
### 插件安装

1.  **下载插件**: 从本项目的 `anx-calibre-manager-koreader-plugin.koplugin` 目录中下载所有文件。
2.  **复制到设备**: 将整个 `anx-calibre-manager-koreader-plugin.koplugin` 文件夹复制到您的 KOReader 设备的 `koreader/plugins/` 目录下。
3.  **重启 KOReader**: 重启您的 KOReader 应用以加载新插件。


1.  **登录** Anx Calibre Manager。
2.  进入 **设置 -> Koreader 同步设置** 页面。
3.  在 KOReader 中，进入 `工具` -> `ANX Progress sync`，然后选择 `Set sync server`。
4.  输入以下信息：
    -   **自定义同步服务器地址**: `http://<your_server_address>/koreader` (使用设置页面中显示的 URL)。
    -   **用户名**: 您的 Anx Calibre Manager 用户名。
    -   **密码**: 您的 Anx Calibre Manager 密码。
5.  点击 **登录**。KOReader 现在即可与您的 Anx 书库同步进度。

## 🤖 MCP 服务器

本应用包含一个符合 JSON-RPC 2.0 规范的 MCP (Model Context Protocol) 服务器，允许外部工具和 AI 代理与您的书库进行交互。

### 使用方法

1.  **生成令牌**: 登录后，进入 **设置 -> MCP 设置** 页面。点击“生成新令牌”来创建一个新的 API 令牌。
2.  **端点 URL**: MCP 服务器的端点是 `http://<your_server_address>/mcp`。
3.  **认证**: 在您的请求 URL 中，通过查询参数附加您的令牌，例如：`http://.../mcp?token=YOUR_TOKEN`。
4.  **发送请求**: 向该端点发送 `POST` 请求，请求体需遵循 JSON-RPC 2.0 格式。

### 可用工具

您可以通过 `tools/list` 方法获取所有可用工具的列表。当前支持的工具包括：

-   **`search_calibre_books`**: 使用 Calibre 强大的搜索语法搜索书籍。
    -   **参数**: `search_expression` (字符串), `limit` (整数, 可选)。
    -   **功能**: 您可以提供简单的关键词进行模糊搜索，也可以构建复杂的查询。
    -   **示例 (高级搜索)**: 搜索由“人民邮电出版社”出版且评分高于4星的图书。
        ```json
        {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "search_calibre_books",
                "arguments": {
                    "search_expression": "publisher:\"人民邮电出版社\" AND rating:>=4",
                    "limit": 10
                }
            },
            "id": "search-request-1"
        }
        ```
-   `get_recent_calibre_books`: 获取最近的 Calibre 书籍。
-   `get_calibre_book_details`: 获取 Calibre 书籍详情。
-   `get_recent_anx_books`: 获取最近的 Anx 书籍。
-   `get_anx_book_details`: 获取 Anx 书籍详情。
-   `push_calibre_book_to_anx`: 推送 Calibre 书籍到 Anx。
-   `send_calibre_book_to_kindle`: 发送 Calibre 书籍到 Kindle。

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
