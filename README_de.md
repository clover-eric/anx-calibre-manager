# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

Eine moderne, mobil-orientierte Webanwendung zur Verwaltung Ihrer E-Book-Bibliothek, die sich in Calibre integrieren lässt und einen persönlichen WebDAV-Server für Ihre Anx-Reader-kompatiblen Geräte bereitstellt.

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README_zh-Hans.md">简体中文</a></strong> |
  <strong><a href="README_zh-Hant.md">繁體中文</a></strong> |
  <strong><a href="README_es.md">Español</a></strong> |
  <strong><a href="README_fr.md">Français</a></strong> |
  <strong><a href="README_de.md">Deutsch</a></strong>
</p>

## ✨ Funktionen

- **Mehrsprachige Unterstützung**: Vollständige Internationalisierungsunterstützung. Die Benutzeroberfläche ist auf Englisch, vereinfachtem Chinesisch (简体中文), traditionellem Chinesisch (繁體中文), Spanisch, Französisch und Deutsch verfügbar.
- **Mobil-orientierte Benutzeroberfläche**: Eine saubere, responsive Benutzeroberfläche, die für eine einfache Bedienung auf Ihrem Telefon konzipiert ist.
- **PWA-Unterstützung**: Als Progressive Web App installierbar für ein nativ-ähnliches Erlebnis.
- **Calibre-Integration**: Verbindet sich mit Ihrem vorhandenen Calibre-Server, um Ihre Bibliothek zu durchsuchen und zu durchsuchen.
- **KOReader-Synchronisierung**: Synchronisieren Sie Ihren Lesefortschritt und Ihre Lesezeit mit KOReader-Geräten.
- **Intelligentes Senden an Kindle**: Behandelt automatisch Formate beim Senden an Ihren Kindle. Wenn ein EPUB vorhanden ist, wird es direkt gesendet. Wenn nicht, konvertiert die App **das beste verfügbare Format in EPUB** basierend auf Ihren Vorlieben, bevor sie es sendet, um eine optimale Kompatibilität zu gewährleisten.
- **An Anx senden**: Senden Sie Bücher aus Ihrer Calibre-Bibliothek direkt in den Ordner Ihres persönlichen Anx-Reader-Geräts.
- **Integrierter WebDAV-Server**: Jeder Benutzer erhält seinen eigenen sicheren WebDAV-Ordner, der mit Anx-Reader und anderen WebDAV-Clients kompatibel ist.
- **MCP-Server**: Ein eingebauter, konformer Model Context Protocol (MCP)-Server, der es KI-Agenten und externen Tools ermöglicht, sicher mit Ihrer Bibliothek zu interagieren.
- **Benutzerverwaltung**: Einfaches, integriertes Benutzerverwaltungssystem mit unterschiedlichen Rollen:
    - **Admin**: Volle Kontrolle über Benutzer, globale Einstellungen und alle Bücher.
    - **Maintainer**: Kann alle Buchmetadaten bearbeiten.
    - **Benutzer**: Kann Bücher hochladen, seine eigene WebDAV-Bibliothek, MCP-Token verwalten, Bücher an Kindle senden und **von ihm hochgeladene Bücher bearbeiten**.
- **Vom Benutzer bearbeitbare hochgeladene Bücher**: Reguläre Benutzer können jetzt Metadaten für von ihnen hochgeladene Bücher bearbeiten. Diese Funktionalität basiert auf einer benutzerdefinierten Spalte in Calibre namens `#library` (Typ: `Text, wobei Kommas als separate Tags behandelt werden`). Wenn ein Benutzer ein Buch hochlädt, wird sein Benutzername automatisch in diesem Feld gespeichert. Benutzer können dann jedes Buch bearbeiten, bei dem sie im Feld `#library` als Eigentümer aufgeführt sind.
    - **Empfehlung für Docker-Benutzer**: Um diese Funktion zu aktivieren, stellen Sie bitte sicher, dass Sie in Ihrer Calibre-Bibliothek eine benutzerdefinierte Spalte namens `#library` (Groß-/Kleinschreibung beachten) vom Typ `Text, wobei Kommas als separate Tags behandelt werden` haben.
- **Einfache Bereitstellung**: Als einzelner Docker-Container mit integrierter mehrsprachiger Locale-Unterstützung bereitstellbar.
- **Lesestatistiken**: Generiert automatisch eine persönliche Lesestatistikseite mit einer jährlichen Lese-Heatmap, einer Liste der aktuell gelesenen Bücher und einer Liste der beendeten Bücher. Die Seite kann öffentlich geteilt oder privat gehalten werden.

## 📸 Screenshots

<p align="center">
  <em>Hauptoberfläche</em><br>
  <img src="screenshots/Screen Shot - MainPage.png">
</p>
<p align="center">
  <em>Einstellungsseite</em><br>
  <img src="screenshots/Screen Shot - SettingPage.png">
</p>

| MCP-Chat | MCP-Einstellungen |
| :---: | :---: |
| <img src="screenshots/Screen Shot - MCPChat.jpg" width="350"/> | <img src="screenshots/Screen Shot - MCPSetting.png" width="650"/> |

| Koreader-Buchstatus | Koreader-Synchronisierung |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderBookStatus.jpg" width="400"/> | <img src="screenshots/Screen Shot - KoreaderSync.jpg" width="400"/> |

| Koreader-Einstellungen | Koreader-WebDAV |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderSetting.png" width="750"/> | <img src="screenshots/Screen Shot - KoreaderWebdav.jpg" width="250"/> |

<p align="center">
  <em>Statistik-Seite</em><br>
  <img src="screenshots/Screen Shot - StatsPage.png">
</p>

## 🚀 Bereitstellung

Diese Anwendung ist für die Bereitstellung mit Docker konzipiert.

### Voraussetzungen

- [Docker](https://www.docker.com/get-started) auf Ihrem Server installiert.
- Ein vorhandener Calibre-Server (optional, aber für die meisten Funktionen erforderlich).

### Ausführen mit Docker

1.  **Finden Sie Ihre Benutzer- und Gruppen-ID (PUID/PGID):**
    Führen Sie `id $USER` auf Ihrer Host-Maschine aus, um die UID und GID Ihres Benutzers zu erhalten. Dies ist entscheidend, um Berechtigungsprobleme mit den gemounteten Volumes zu vermeiden.

    ```bash
    id $USER
    # Beispielausgabe: uid=1000(meinbenutzer) gid=1000(meinbenutzer) ...
    ```

2.  **Erstellen Sie Verzeichnisse für persistente Daten:**
    Sie benötigen separate Verzeichnisse für die Konfiguration/Datenbank und für WebDAV-Daten.

    ```bash
    mkdir -p /pfad/zu/ihrer/config
    mkdir -p /pfad/zu/ihrem/webdav
    mkdir -p /pfad/zu/ihren/schriftarten # Optional: für benutzerdefinierte Schriftarten
    ```

3.  **Führen Sie den Docker-Container aus:**
    Sie können `docker run` oder eine `docker-compose.yml`-Datei verwenden.

    **Mit `docker run`:**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="Europe/Berlin" \
      -v /pfad/zu/ihrer/config:/config \
      -v /pfad/zu/ihrem/webdav:/webdav \
      -v /pfad/zu/ihren/schriftarten:/opt/share/fonts \ # Optional: Benutzerdefinierte Schriftarten mounten
      -e "GUNICORN_WORKERS=2" \ 
      -e "SECRET_KEY=ihr_super_geheimer_schlüssel" \
      -e "CALIBRE_URL=http://ip-ihres-calibre-servers:8080" \
      -e "CALIBRE_USERNAME=ihr_calibre_benutzername" \
      -e "CALIBRE_PASSWORD=ihr_calibre_passwort" \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **Mit `docker-compose.yml`:**

    Erstellen Sie eine `docker-compose.yml`-Datei:
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /pfad/zu/ihrer/config:/config
          - /pfad/zu/ihrem/webdav:/webdav
          - /pfad/zu/ihren/schriftarten:/opt/share/fonts # Optional: Benutzerdefinierte Schriftarten mounten
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Europe/Berlin
          - GUNICORN_WORKERS=2 # Optional: Passen Sie die Anzahl der Gunicorn-Worker-Prozesse an
          - SECRET_KEY=ihr_super_geheimer_schlüssel
          - CALIBRE_URL=http://ip-ihres-calibre-servers:8080
          - CALIBRE_USERNAME=ihr_calibre_benutzername
          - CALIBRE_PASSWORD=ihr_calibre_passwort
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    Führen Sie dann aus:
    ```bash
    docker-compose up -d
    ```

### Benutzerdefinierte Schriftarten

Das Buchkonvertierungstool `ebook-converter` durchsucht das Verzeichnis `/opt/share/fonts` nach Schriftarten. Wenn Sie beim Konvertieren von Büchern mit Sonderzeichen (z. B. Chinesisch) auf schriftartenbezogene Probleme stoßen, können Sie benutzerdefinierte Schriftarten bereitstellen, indem Sie ein lokales Verzeichnis mit Ihren Schriftartdateien (z. B. `.ttf`, `.otf`) an den Pfad `/opt/share/fonts` des Containers mounten.

### Konfiguration

Die Anwendung wird über Umgebungsvariablen konfiguriert.

| Variable | Beschreibung | Standard |
| --- | --- | --- |
| `PUID` | Die Benutzer-ID, unter der die Anwendung ausgeführt wird. | `1001` |
| `PGID` | Die Gruppen-ID, unter der die Anwendung ausgeführt wird. | `1001` |
| `TZ` | Ihre Zeitzone, z.B. `Europe/Berlin`. | `UTC` |
| `PORT` | Der Port, auf dem die Anwendung im Container lauscht. | `5000` |
| `GUNICORN_WORKERS` | Optional: Die Anzahl der Gunicorn-Worker-Prozesse. | `2` |
| `CONFIG_DIR` | Das Verzeichnis für die Datenbank und `settings.json`. | `/config` |
| `WEBDAV_DIR` | Das Basisverzeichnis für WebDAV-Benutzerdateien. | `/webdav` |
| `SECRET_KEY` | **Erforderlich.** Eine lange, zufällige Zeichenfolge für die Sitzungssicherheit. | `""` |
| `CALIBRE_URL` | Die URL Ihres Calibre-Content-Servers. | `""` |
| `CALIBRE_USERNAME` | Benutzername für Ihren Calibre-Server. | `""` |
| `CALIBRE_PASSWORD` | Passwort für Ihren Calibre-Server. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | Die Standard-Calibre-Bibliotheks-ID zum Durchsuchen, Suchen und Hochladen von Büchern. | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Ob das Hochladen doppelter Bücher erlaubt ist. | `false` |
| `SMTP_SERVER` | SMTP-Server zum Senden von E-Mails (z.B. für Kindle). | `""` |
| `SMTP_PORT` | SMTP-Port. | `587` |
| `SMTP_USERNAME` | SMTP-Benutzername. | `""` |
| `SMTP_PASSWORD` | SMTP-Passwort. | `""` |
| `SMTP_ENCRYPTION` | SMTP-Verschlüsselungstyp (`ssl`, `starttls`, `none`). | `ssl` |

## 📖 KOReader-Synchronisierung

Sie können Ihren Lesefortschritt und Ihre Lesezeit zwischen Ihrer Anx-Bibliothek und KOReader-Geräten synchronisieren. Die Einrichtung umfasst zwei Hauptschritte: die Einrichtung von WebDAV für den Zugriff auf Ihre Bücher und die Konfiguration des Synchronisierungs-Plugins zur Handhabung der Fortschrittssynchronisierung.

### Schritt 1: WebDAV-Cloud-Speicher konfigurieren

Dieser Schritt ermöglicht es Ihnen, Ihre Anx-Bibliotheksbücher direkt in KOReader zu durchsuchen und zu lesen.

1.  Navigieren Sie in KOReader zu `Cloud-Speicher` -> `Neuen Cloud-Speicher hinzufügen`.
2.  Wählen Sie `WebDAV`.
3.  Füllen Sie die Details aus:
    -   **Serveradresse**: Geben Sie die WebDAV-URL ein, die auf der Einstellungsseite von Anx Calibre Manager angezeigt wird (`Einstellungen` -> `Koreader-Synchronisierungseinstellungen`). **Stellen Sie sicher, dass der Pfad mit einem `/` endet**.
    -   **Benutzername**: Ihr Anx Calibre Manager-Benutzername.
    -   **Passwort**: Ihr Anx Calibre Manager-Anmeldepasswort.
    -   **Ordner**: `/anx/data/file`
4.  Tippen Sie auf `Verbinden` und speichern Sie. Sie sollten nun Ihre Anx-Bibliothek im Dateibrowser von KOReader sehen können.

### Schritt 2: Synchronisierungs-Plugin installieren und konfigurieren

Dieses Plugin sendet Ihren Lesefortschritt an den Anx Calibre Manager-Server zurück.

1.  **Plugin herunterladen**:
    -   Melden Sie sich bei Anx Calibre Manager an.
    -   Gehen Sie zu `Einstellungen` -> `Koreader-Synchronisierungseinstellungen`.
    -   Klicken Sie auf die Schaltfläche `KOReader-Plugin herunterladen (.zip)`, um das Plugin-Paket zu erhalten.
2.  **Plugin installieren**:
    -   Entpacken Sie die heruntergeladene Datei, um einen Ordner namens `anx-calibre-manager-koreader-plugin.koplugin` zu erhalten.
    -   Kopieren Sie diesen gesamten Ordner in das Verzeichnis `koreader/plugins/` auf Ihrem KOReader-Gerät.
3.  **KOReader neu starten**: Schließen Sie die KOReader-App vollständig und öffnen Sie sie erneut, um das neue Plugin zu laden.
4.  **Synchronisierungsserver konfigurieren**:
    -   **Wichtig**: Öffnen Sie zuerst ein Buch aus dem in Schritt 1 konfigurierten WebDAV-Speicher. Das Plugin-Menü ist **nur in der Leseansicht sichtbar**.
    -   Gehen Sie in der Leseansicht zu `Werkzeuge (Schraubenschlüssel-Symbol)` -> `Nächste Seite` -> `Weitere Werkzeuge` -> `ANX Calibre Manager`.
    -   Wählen Sie `Benutzerdefinierter Synchronisierungsserver`.
    -   **Adresse des benutzerdefinierten Synchronisierungsservers**: Geben Sie die URL des Synchronisierungsservers ein, die auf der Einstellungsseite von Anx Calibre Manager angezeigt wird (z.B. `http://<ihre_server_adresse>/koreader`).
    -   Gehen Sie zum vorherigen Menü zurück, wählen Sie `Anmelden` und geben Sie Ihren Anx Calibre Manager-Benutzernamen und Ihr Passwort ein.

Nach der Konfiguration synchronisiert das Plugin Ihren Lesefortschritt automatisch oder manuell. Sie können Einstellungen wie die Synchronisierungshäufigkeit im Plugin-Menü anpassen. **Hinweis: Es wird nur der Fortschritt von EPUB-Büchern unterstützt.**

## 🤖 MCP-Server

Diese Anwendung enthält einen JSON-RPC 2.0-kompatiblen MCP (Model Context Protocol)-Server, der es externen Tools und KI-Agenten ermöglicht, mit Ihrer Bibliothek zu interagieren.

### Wie man es benutzt

1.  **Token generieren**: Gehen Sie nach dem Anmelden zur Seite **Einstellungen -> MCP-Einstellungen**. Klicken Sie auf "Neues Token generieren", um ein neues API-Token zu erstellen.
2.  **Endpunkt-URL**: Der MCP-Server-Endpunkt ist `http://<ihre_server_adresse>/mcp`.
3.  **Authentifizierung**: Authentifizieren Sie sich, indem Sie Ihr Token als Abfrageparameter an die URL anhängen, z.B. `http://.../mcp?token=IHR_TOKEN`.
4.  **Anfragen senden**: Senden Sie `POST`-Anfragen an diesen Endpunkt mit einem Body, der dem JSON-RPC 2.0-Format entspricht.

### Verfügbare Werkzeuge

Sie können eine Liste aller verfügbaren Werkzeuge erhalten, indem Sie die Methode `tools/list` aufrufen. Die derzeit unterstützten Werkzeuge sind:

-   **`search_calibre_books`**: Suchen Sie nach Büchern mit der leistungsstarken Suchsyntax von Calibre.
    -   **Parameter**: `search_expression` (Zeichenkette), `limit` (Ganzzahl, optional).
    -   **Funktionalität**: Sie können einfache Schlüsselwörter für eine breite Suche angeben oder komplexe Abfragen erstellen.
    -   **Beispiel (Erweiterte Suche)**: Finden Sie Bücher von "O'Reilly Media" mit einer Bewertung von 4 Sternen oder höher.
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
-   `get_recent_calibre_books`: Holen Sie sich die neuesten Bücher aus der Calibre-Bibliothek.
-   `get_calibre_book_details`: Holen Sie sich Details zu einem bestimmten Calibre-Buch.
-   `get_recent_anx_books`: Holen Sie sich die neuesten Bücher aus der Anx-Bibliothek.
-   `get_anx_book_details`: Holen Sie sich Details zu einem bestimmten Anx-Buch.
-   `push_calibre_book_to_anx`: Schieben Sie ein Calibre-Buch in die Anx-Bibliothek.
-   `send_calibre_book_to_kindle`: Senden Sie ein Calibre-Buch an Kindle.
-   `get_calibre_epub_table_of_contents`: Ruft das Inhaltsverzeichnis für ein Calibre-Buch ab.
-   `get_calibre_epub_chapter_content`: Ruft den Inhalt eines Kapitels aus einem Calibre-Buch ab.
-   `get_anx_epub_table_of_contents`: Ruft das Inhaltsverzeichnis für ein Buch aus der Anx-Bibliothek ab.
-   `get_anx_epub_chapter_content`: Ruft den Inhalt eines Kapitels aus einem Buch der Anx-Bibliothek ab.

## 💻 Entwicklung

1.  **Klonen Sie das Repository:**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **Erstellen Sie eine virtuelle Umgebung:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Installieren Sie die Abhängigkeiten:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Starten Sie den Entwicklungsserver:**
    ```bash
    python app.py
    ```
    Die Anwendung ist unter `http://localhost:5000` verfügbar.

## 🤝 Mitwirken

Beiträge, Probleme und Funktionswünsche sind willkommen! Schauen Sie sich gerne die [Problemseite](https://github.com/ptbsare/anx-calibre-manager/issues) an.

## 📄 Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert.