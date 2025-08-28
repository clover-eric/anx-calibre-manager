# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

一个现代化的、移动端优先的 Web 应用，用于管理您的电子书库，可与 Calibre 集成，并为您的 Anx-reader 兼容设备提供个人 WebDAV 服务器。

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README_zh-Hans.md">简体中文</a></strong> |
  <strong><a href="README_zh-Hant.md">繁體中文</a></strong> |
  <strong><a href="README_es.md">Español</a></strong> |
  <strong><a href="README_fr.md">Français</a></strong> |
  <strong><a href="README_de.md">Deutsch</a></strong>
</p>

## ✨ 功能特性

- **多语言支持**: 完整的国际化支持，界面提供英语、简体中文 (简体中文)、繁体中文 (繁體中文)、西班牙语、法语和德语。
- **移动端优先界面**: 简洁、响应式的用户界面，专为在手机上轻松使用而设计。
- **PWA 支持**: 可作为渐进式 Web 应用 (PWA) 安装，提供类似原生应用的体验。
- **Calibre 集成**: 连接到您现有的 Calibre 服务器，以浏览和搜索您的书库。
- **KOReader 同步**: 与您的 KOReader 设备同步阅读进度和阅读时间。
- **智能推送到 Kindle**: 发送书籍到您的 Kindle 时，应用会自动处理格式。如果书籍已有 EPUB 格式，则直接发送；如果没有，它将根据您的格式偏好设置，自动将最优先的可用格式**转换为 EPUB**后再发送，以确保最佳兼容性。
- **推送到 Anx**: 将书籍从您的 Calibre 书库直接发送到您的个人 Anx-reader 设备文件夹。
- **集成的 WebDAV 服务器**: 每个用户都会获得自己独立、安全的 WebDAV 文件夹，与 Anx-reader 和其他 WebDAV 客户端兼容。
- **MCP 服务器**: 内置一个符合规范的 Model Context Protocol (MCP) 服务器，允许 AI 代理和外部工具安全地与您的书库交互。
- **用户管理**: 简单、内置的用户管理系统，具有不同的角色：
    - **管理员 (Admin)**: 对用户、全局设置和所有书籍拥有完全控制权。
    - **维护者 (Maintainer)**: 可以编辑所有书籍元数据。
    - **普通用户 (User)**: 可以上传书籍、管理自己的 WebDAV 书库、MCP token、发送书籍到 Kindle，以及**编辑自己上传的书籍**。
- **用户可编辑自己上传的书籍**: 普通用户现在可以编辑自己上传的书籍的元数据。此功能依赖于 Calibre 中的一个名为 `#library` 的自定义列（类型：`文本，逗号分隔`）。当用户上传书籍时，他们的用户名会自动保存到该字段。用户可以编辑 `#library` 字段中记录的、由自己上传的任何书籍。
    - **Docker 用户建议**: 为启用此功能，请确保您的 Calibre 书库中有一个名为 `#library` 的自定义列（区分大小写），类型为 `文本，逗号分隔`。
- **轻松部署**: 可作为单个 Docker 容器进行部署，内置了多语言环境支持。
- **阅读统计**: 自动生成个人阅读统计页面，包含年度阅读热力图、在读书籍和已读书籍列表。页面支持公开或私有分享。
## 📸 截图

![主界面](Screen%20Shot%20-%20Main.png)![设置页面](Screen%20Shot%20-%20Setting.png)![MCP 设置](Screen%20Shot%20-%20MCP.png)![Koreader页面](Screen%20Shot%20-%20Koreader.png)![统计页面](Screen%20Shot%20-%20Stats.png)

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

您可以同步您的阅读进度和阅读时间到 Anx 书库。整个设置过程分为两步：首先配置 WebDAV 以便访问您的书籍，然后配置同步插件来处理进度同步。

### 第一步：配置 WebDAV 云存储

此步骤让您可以直接在 KOReader 中浏览和阅读您的 Anx 书库中的书籍。

1.  在 KOReader 中，进入 `云存储` -> `添加新的云存储`。
2.  选择 `WebDAV`。
3.  填写以下详细信息：
    -   **服务器地址**: 填写 Anx Calibre Manager 设置页面（`设置` -> `Koreader 同步设置`）中显示的 WebDAV 地址。**请确保路径以 `/` 结尾**。
    -   **用户名**: 您的 Anx Calibre Manager 用户名。
    -   **密码**: 您的 Anx Calibre Manager 登录密码。
    -   **文件夹**: `/anx/data/file`
4.  点击 `连接` 并保存。现在您应该可以在 KOReader 的文件浏览器中看到您的 Anx 书库了。

### 第二步：安装并配置同步插件

此插件负责将您的阅读进度发送回 Anx Calibre Manager 服务器。

1.  **下载插件**:
    -   登录 Anx Calibre Manager。
    -   进入 `设置` -> `Koreader 同步设置`。
    -   点击 `下载 KOReader 插件 (.zip)` 按钮来获取插件包。
2.  **安装插件**:
    -   解压下载的 `.zip` 文件，您会得到一个名为 `anx-calibre-manager-koreader-plugin.koplugin` 的文件夹。
    -   将这**整个文件夹**复制到您 KOReader 设备的 `koreader/plugins/` 目录下。
3.  **重启 KOReader**: 完全关闭并重新打开 KOReader 应用以加载新插件。
4.  **配置同步服务器**:
    -   **重要提示**: 首先，请通过上一步设置的 WebDAV 打开并开始阅读一本书籍。插件菜单**仅在阅读界面中可见**。
    -   在阅读界面，进入 `工具(扳手图标)` -> `下一页` -> `更多工具` -> `ANX Calibre Manager`。
    -   选择 `自定义同步服务器`。
    -   **自定义同步服务器地址**: 输入 Anx Calibre Manager 设置页面中显示的同步服务器地址 (例如: `http://<your_server_address>/koreader`)。
    -   返回上一级菜单，选择 `登录`，并输入您的 Anx Calibre Manager 用户名和密码。

配置完成后，插件将自动或手动同步您的阅读进度。您可以在插件菜单中调整同步频率等设置。**注意：目前仅支持同步 EPUB 格式书籍的进度。**

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
