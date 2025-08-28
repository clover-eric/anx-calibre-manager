# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

一個現代化的、行動端優先的 Web 應用程式，用於管理您的電子書庫，可與 Calibre 整合，並為您的 Anx-reader 相容裝置提供個人 WebDAV 伺服器。

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README_zh-Hans.md">简体中文</a></strong> |
  <strong><a href="README_zh-Hant.md">繁體中文</a></strong> |
  <strong><a href="README_es.md">Español</a></strong> |
  <strong><a href="README_fr.md">Français</a></strong> |
  <strong><a href="README_de.md">Deutsch</a></strong>
</p>

## ✨ 功能特性

- **多語言支援**: 完整的國際化支援，介面提供英語、簡體中文 (简体中文)、繁體中文 (繁體中文)、西班牙語、法語和德語。
- **行動端優先介面**: 簡潔、響應式的用戶介面，專為在手機上輕鬆使用而設計。
- **PWA 支援**: 可作為漸進式 Web 應用 (PWA) 安裝，提供類似原生應用的體驗。
- **Calibre 整合**: 連接到您現有的 Calibre 伺服器，以瀏覽和搜尋您的書庫。
- **KOReader 同步**: 與您的 KOReader 裝置同步閱讀進度和閱讀時間。
- **智慧推送到 Kindle**: 傳送書籍到您的 Kindle 時，應用程式會自動處理格式。如果書籍已有 EPUB 格式，則直接傳送；如果沒有，它將根據您的格式偏好設定，自動將最優先的可用格式**轉換為 EPUB**後再傳送，以確保最佳相容性。
- **推送到 Anx**: 將書籍從您的 Calibre 書庫直接傳送到您的個人 Anx-reader 裝置資料夾。
- **整合的 WebDAV 伺服器**: 每個使用者都會獲得自己獨立、安全的 WebDAV 資料夾，與 Anx-reader 和其他 WebDAV 用戶端相容。
- **MCP 伺服器**: 內建一個符合規範的 Model Context Protocol (MCP) 伺服器，允許 AI 代理和外部工具安全地與您的書庫互動。
- **使用者管理**: 簡單、內建的使用者管理系統，具有不同的角色：
    - **管理員 (Admin)**: 對使用者、全域設定和所有書籍擁有完全控制權。
    - **維護者 (Maintainer)**: 可以編輯所有書籍元資料。
    - **普通使用者 (User)**: 可以上傳書籍、管理自己的 WebDAV 書庫、MCP token、傳送書籍到 Kindle，以及**編輯自己上傳的書籍**。
- **使用者可編輯自己上傳的書籍**: 普通使用者現在可以編輯自己上傳的書籍的元資料。此功能依賴於 Calibre 中的一個名為 `#library` 的自訂欄位（類型：`文字，逗號分隔`）。當使用者上傳書籍時，他們的使用者名稱會自動儲存到該欄位。使用者可以編輯 `#library` 欄位中記錄的、由自己上傳的任何書籍。
    - **Docker 使用者建議**: 為啟用此功能，請確保您的 Calibre 書庫中有一個名為 `#library` 的自訂欄位（區分大小寫），類型為 `文字，逗號分隔`。
- **輕鬆部署**: 可作為單一 Docker 容器進行部署，內建了多語言環境支援。
- **閱讀統計**: 自動產生個人閱讀統計頁面，包含年度閱讀熱力圖、在讀書籍和已讀書籍清單。頁面支援公開或私人分享。

## 📸 截圖

![主介面](Screen%20Shot%20-%20Main.png)![設定頁面](Screen%20Shot%20-%20Setting.png)![MCP 設定](Screen%20Shot%20-%20MCP.png)![Koreader頁面](Screen%20Shot%20-%20Koreader.png)![統計頁面](Screen%20Shot%20-%20Stats.png)

## 🚀 部署

本應用程式設計為使用 Docker 進行部署。

### 先決條件

- 您的伺服器上已安裝 [Docker](https://www.docker.com/get-started)。
- 一個正在運行的 Calibre 伺服器 (可選，但大部分功能需要)。

### 使用 Docker 運行

1.  **取得您的使用者和群組 ID (PUID/PGID):**
    在您的主機上運行 `id $USER` 來取得您目前使用者的 UID 和 GID。這對於避免掛載磁碟區的權限問題至關重要。

    ```bash
    id $USER
    # 範例輸出: uid=1000(myuser) gid=1000(myuser) ...
    ```

2.  **建立持久化資料目錄:**
    您需要為設定/資料庫和 WebDAV 資料分別建立目錄。

    ```bash
    mkdir -p /path/to/your/config
    mkdir -p /path/to/your/webdav
    mkdir -p /path/to/your/fonts # 可選：用於自訂字型
    ```

3.  **運行 Docker 容器:**
    您可以使用 `docker run` 或 `docker-compose.yml` 檔案。

    **使用 `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="Asia/Taipei" \
      -v /path/to/your/config:/config \
      -v /path/to/your/webdav:/webdav \
      -v /path/to/your/fonts:/opt/share/fonts \ # 可選：掛載自訂字型
      -e "GUNICORN_WORKERS=2" \ 
      -e "SECRET_KEY=your_super_secret_key" \
      -e "CALIBRE_URL=http://your-calibre-server-ip:8080" \
      -e "CALIBRE_USERNAME=your_calibre_username" \
      -e "CALIBRE_PASSWORD=your_calibre_password" \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **使用 `docker-compose.yml`:**

    建立一個 `docker-compose.yml` 檔案:
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
          - /path/to/your/fonts:/opt/share/fonts # 可選：掛載自訂字型
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Asia/Taipei
          - GUNICORN_WORKERS=2 # 可選：自訂 Gunicorn worker 程序的數量
          - SECRET_KEY=your_super_secret_key
          - CALIBRE_URL=http://your-calibre-server-ip:8080
          - CALIBRE_USERNAME=your_calibre_username
          - CALIBRE_PASSWORD=your_calibre_password
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    然後運行:
    ```bash
    docker-compose up -d
    ```

### 自訂字型

書籍格式轉換工具 `ebook-converter` 會掃描 `/opt/share/fonts` 目錄以尋找字型。如果您在轉換某些包含特殊字元（如中文）的書籍時遇到字型問題，可以透過掛載一個包含您所需字型檔案（例如 `.ttf`, `.otf`）的本地目錄到容器的 `/opt/share/fonts` 路徑來提供自訂字型。

### 設定

應用程式透過環境變數進行設定。

| 變數 | 描述 | 預設值 |
| --- | --- | --- |
| `PUID` | 指定運行應用的使用者 ID。 | `1001` |
| `PGID` | 指定運行應用的群組 ID。 | `1001` |
| `TZ` | 您的時區, 例如 `Asia/Taipei`。 | `UTC` |
| `PORT` | 應用程式在容器內監聽的埠號。 | `5000` |
| `GUNICORN_WORKERS` | 可選：Gunicorn worker 程序的數量。 | `2` |
| `CONFIG_DIR` | 用於存放資料庫和 `settings.json` 的目錄。 | `/config` |
| `WEBDAV_DIR` | 用於存放 WebDAV 使用者檔案的基礎目錄。 | `/webdav` |
| `SECRET_KEY` | **必需。** 用於會話安全的、長的、隨機的字串。 | `""` |
| `CALIBRE_URL` | 您的 Calibre 內容伺服器的 URL。 | `""` |
| `CALIBRE_USERNAME` | 您的 Calibre 伺服器的使用者名稱。 | `""` |
| `CALIBRE_PASSWORD` | 您的 Calibre 伺服器的密碼。 | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | 用於瀏覽、搜尋和上傳書籍的預設 Calibre 庫 ID。 | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | 是否允許上傳重複的書籍。 | `false` |
| `SMTP_SERVER` | 用於傳送郵件 (例如，推送到 Kindle) 的 SMTP 伺服器。 | `""` |
| `SMTP_PORT` | SMTP 埠號。 | `587` |
| `SMTP_USERNAME` | SMTP 使用者名稱。 | `""` |
| `SMTP_PASSWORD` | SMTP 密碼。 | `""` |
| `SMTP_ENCRYPTION` | SMTP 加密類型 (`ssl`, `starttls`, `none`)。 | `ssl` |

## 📖 KOReader 同步

您可以同步您的閱讀進度和閱讀時間到 Anx 書庫。整個設定過程分為兩步：首先設定 WebDAV 以便存取您的書籍，然後設定同步外掛程式來處理進度同步。

### 第一步：設定 WebDAV 雲端儲存

此步驟讓您可以直接在 KOReader 中瀏覽和閱讀您的 Anx 書庫中的書籍。

1.  在 KOReader 中，進入 `雲端儲存` -> `新增雲端儲存`。
2.  選擇 `WebDAV`。
3.  填寫以下詳細資訊：
    -   **伺服器位址**: 填寫 Anx Calibre Manager 設定頁面（`設定` -> `Koreader 同步設定`）中顯示的 WebDAV 位址。**請確保路徑以 `/` 結尾**。
    -   **使用者名稱**: 您的 Anx Calibre Manager 使用者名稱。
    -   **密碼**: 您的 Anx Calibre Manager 登入密碼。
    -   **資料夾**: `/anx/data/file`
4.  點擊 `連線` 並儲存。現在您應該可以在 KOReader 的檔案瀏覽器中看到您的 Anx 書庫了。

### 第二步：安裝並設定同步外掛程式

此外掛程式負責將您的閱讀進度傳送回 Anx Calibre Manager 伺服器。

1.  **下載外掛程式**:
    -   登入 Anx Calibre Manager。
    -   進入 `設定` -> `Koreader 同步設定`。
    -   點擊 `下載 KOReader 外掛程式 (.zip)` 按鈕來取得外掛程式包。
2.  **安裝外掛程式**:
    -   解壓縮下載的 `.zip` 檔案，您會得到一個名為 `anx-calibre-manager-koreader-plugin.koplugin` 的資料夾。
    -   將這**整個資料夾**複製到您 KOReader 裝置的 `koreader/plugins/` 目錄下。
3.  **重新啟動 KOReader**: 完全關閉並重新開啟 KOReader 應用程式以載入新外掛程式。
4.  **設定同步伺服器**:
    -   **重要提示**: 首先，請透過上一步設定的 WebDAV 開啟並開始閱讀一本書籍。外掛程式選單**僅在閱讀介面中可見**。
    -   在閱讀介面，進入 `工具(扳手圖示)` -> `下一頁` -> `更多工具` -> `ANX Calibre Manager`。
    -   選擇 `自訂同步伺服器`。
    -   **自訂同步伺服器位址**: 輸入 Anx Calibre Manager 設定頁面中顯示的同步伺服器位址 (例如: `http://<your_server_address>/koreader`)。
    -   返回上一層選單，選擇 `登入`，並輸入您的 Anx Calibre Manager 使用者名稱和密碼。

設定完成後，外掛程式將自動或手動同步您的閱讀進度。您可以在外掛程式選單中調整同步頻率等設定。**注意：目前僅支援同步 EPUB 格式書籍的進度。**

## 🤖 MCP 伺服器

本應用程式包含一個符合 JSON-RPC 2.0 規範的 MCP (Model Context Protocol) 伺服器，允許外部工具和 AI 代理與您的書庫進行互動。

### 使用方法

1.  **產生權杖**: 登入後，進入 **設定 -> MCP 設定** 頁面。點擊「產生新權杖」來建立一個新的 API 權杖。
2.  **端點 URL**: MCP 伺服器的端點是 `http://<your_server_address>/mcp`。
3.  **認證**: 在您的請求 URL 中，透過查詢參數附加您的權杖，例如：`http://.../mcp?token=YOUR_TOKEN`。
4.  **傳送請求**: 向該端點傳送 `POST` 請求，請求體需遵循 JSON-RPC 2.0 格式。

### 可用工具

您可以透過 `tools/list` 方法取得所有可用工具的清單。目前支援的工具包括：

-   **`search_calibre_books`**: 使用 Calibre 強大的搜尋語法搜尋書籍。
    -   **參數**: `search_expression` (字串), `limit` (整數, 可選)。
    -   **功能**: 您可以提供簡單的關鍵詞進行模糊搜尋，也可以建構複雜的查詢。
    -   **範例 (進階搜尋)**: 搜尋由「O'Reilly Media」出版且評分高於4星的圖書。
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
-   `get_recent_calibre_books`: 取得最近的 Calibre 書籍。
-   `get_calibre_book_details`: 取得 Calibre 書籍詳情。
-   `get_recent_anx_books`: 取得最近的 Anx 書籍。
-   `get_anx_book_details`: 取得 Anx 書籍詳情。
-   `push_calibre_book_to_anx`: 推送 Calibre 書籍到 Anx。
-   `send_calibre_book_to_kindle`: 傳送 Calibre 書籍到 Kindle。

## 💻 開發

1.  **克隆儲存庫:**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **建立虛擬環境:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **安裝依賴:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **運行開發伺服器:**
    ```bash
    python app.py
    ```
    應用程式將在 `http://localhost:5000` 上可用。

## 🤝 貢獻

歡迎提交貢獻、問題和功能請求！請隨時查看 [問題頁面](https://github.com/ptbsare/anx-calibre-manager/issues)。

## 📄 授權

本專案採用 MIT 授權。