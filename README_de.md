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
- **In-Browser-Buchvorschau**: Vorschau von E-Books direkt in Ihrem Browser. Bietet Text-zu-Sprache (TTS).
- **Hörbuchgenerierung**: Konvertieren Sie EPUB-Bücher in M4B-Hörbücher mit Kapitelmarkierungen unter Verwendung konfigurierbarer Text-zu-Sprache (TTS)-Anbieter (z. B. Microsoft Edge TTS). Die generierten M4B-Dateien sind vollständig kompatibel mit Hörbuchservern wie [Audiobookshelf](https://www.audiobookshelf.org/).
- **Online-Hörbuch-Player**: Hören Sie Ihre generierten M4B-Hörbücher direkt im Browser. Ihr Hörfortschritt wird automatisch gespeichert und synchronisiert.
- **KI fragen**: Führen Sie Gespräche mit Ihren Büchern. Mit dieser Funktion können Sie mit jedem Buch in Ihrer Bibliothek chatten, Fragen zum Inhalt stellen, Zusammenfassungen erhalten oder Themen über eine KI-gestützte Oberfläche erkunden.
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
- **Registrierung nur mit Einladung**: Administratoren können Einladungscodes generieren, um die Benutzerregistrierung zu steuern. Diese Funktion ist standardmäßig aktiviert, um unbefugte Anmeldungen zu verhindern.
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

<p align="center">
  <em>MCP-Einstellungen</em><br>
  <img src="screenshots/Screen Shot - MCPSetting.png">
</p>

| MCP-Chat | MCP-Chat | MCP-Chat | MCP-Chat |
| :---: | :---: | :---: | :---: |
| <img src="screenshots/Screen Shot - MCPChat.jpg" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-1.png" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-2.png" width="250"/> | <img src="screenshots/Screen Shot - MCPChat2-3.png" width="250"/> |

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

| Hörbuchliste | Hörbuch-Player |
| :---: | :---: |
| <img src="screenshots/Screen Shot - AudiobookList.png" width="400"/> | <img src="screenshots/Screen Shot - AudiobookPlayer.png" width="400"/> |

| Chat mit Buch | Chat mit Buch |
| :---: | :---: |
| <img src="screenshots/Screen Shot - ChatWithBook1.png" width="400"/> | <img src="screenshots/Screen Shot - ChatWithBook2.png" width="400"/> |

## 🚀 Bereitstellung

Diese Anwendung ist für die Bereitstellung mit Docker konzipiert.

### Voraussetzungen

- [Docker](https://www.docker.com/get-started) auf Ihrem Server installiert.
- Ein vorhandener Calibre-Server (optional, aber für die meisten Funktionen erforderlich).

### Schnellstart (Docker Run)

Dies ist der einfachste Weg, um loszulegen.

1.  Erstellen Sie zwei Verzeichnisse für persistente Daten:
    ```bash
    mkdir -p ./config
    mkdir -p ./webdav
    ```

2.  Führen Sie den Docker-Container mit diesem einzigen Befehl aus:
    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -v $(pwd)/config:/config \
      -v $(pwd)/webdav:/webdav \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

3.  Greifen Sie auf die Anwendung unter `http://localhost:5000` zu. Der erste Benutzer, der sich registriert, wird zum Administrator. Sie können die Calibre-Serververbindung und andere Einstellungen später über die Weboberfläche konfigurieren.

### Erweiterte Konfiguration

Hier ist ein detaillierteres `docker-compose.yml`-Beispiel für Benutzer, die eine Verbindung zu einem Calibre-Server herstellen und weitere Optionen anpassen möchten.

1.  **Finden Sie Ihre Benutzer- und Gruppen-ID (PUID/PGID):**
    Führen Sie `id $USER` auf Ihrer Host-Maschine aus. Dies wird empfohlen, um Berechtigungsprobleme zu vermeiden.

2.  **Erstellen Sie eine `docker-compose.yml`-Datei:**
    ```yaml
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /pfad/zu/ihrer/config:/config
          - /pfad/zu/ihrem/webdav:/webdav
          - /pfad/zu/ihren/audiobooks:/audiobooks # Optional
          - /pfad/zu/ihren/schriftarten:/opt/share/fonts # Optional
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Europe/Berlin
          - GUNICORN_WORKERS=2 # Optional
          - SECRET_KEY=ihr_super_geheimer_schlüssel # Ändern Sie dies!
          - CALIBRE_URL=http://ip-ihres-calibre-servers:8080
          - CALIBRE_USERNAME=ihr_calibre_benutzername
          - CALIBRE_PASSWORD=ihr_calibre_passwort
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    *Hinweis: Ersetzen Sie `/pfad/zu/ihrer/...` durch die tatsächlichen Pfade auf Ihrer Host-Maschine.*

3.  Führen Sie den Container aus:
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
| `CALIBRE_URL` | Die URL Ihres Calibre-Content-Servers. Siehe [Fehlerbehebung](#1-warum-sind-keine-bücher-in-meiner-calibre-liste), wenn Sie Verbindungsprobleme haben. | `""` |
| `CALIBRE_USERNAME` | Benutzername für Ihren Calibre-Server. Siehe [Fehlerbehebung](#1-warum-sind-keine-bücher-in-meiner-calibre-liste), wenn Sie Verbindungsprobleme haben. | `""` |
| `CALIBRE_PASSWORD` | Passwort für Ihren Calibre-Server. Siehe [Fehlerbehebung](#1-warum-sind-keine-bücher-in-meiner-calibre-liste), wenn Sie Verbindungsprobleme haben. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | Die Standard-Calibre-Bibliotheks-ID. Details finden Sie unter [Wie finde ich meine `library_id`](#4-wie-finde-ich-meine-library_id). | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Ob das Hochladen doppelter Bücher erlaubt ist. | `false` |
| `REQUIRE_INVITE_CODE` | Ob für die Registrierung ein Einladungscode erforderlich ist. | `true` |
| `SMTP_SERVER` | SMTP-Server zum Senden von E-Mails (z.B. für Kindle). | `""` |
| `SMTP_PORT` | SMTP-Port. | `587` |
| `SMTP_USERNAME` | SMTP-Benutzername. | `""` |
| `SMTP_PASSWORD` | SMTP-Passwort. | `""` |
| `SMTP_ENCRYPTION` | SMTP-Verschlüsselungstyp (`ssl`, `starttls`, `none`). | `ssl` |
| `DEFAULT_TTS_PROVIDER` | Der Standard-TTS-Anbieter für die Hörbuchgenerierung (`edge_tts` oder `openai_tts`). | `edge_tts` |
| `DEFAULT_TTS_VOICE` | Die Standardstimme für den ausgewählten TTS-Anbieter. | `en-US-AriaNeural` |
| `DEFAULT_TTS_RATE` | Die Standard-Sprechgeschwindigkeit für den TTS-Anbieter (z. B. `+10%`). | `+0%` |
| `DEFAULT_OPENAI_API_KEY` | Ihr OpenAI-API-Schlüssel (erforderlich, wenn `openai_tts` verwendet wird). | `""` |
| `DEFAULT_OPENAI_API_BASE_URL` | Benutzerdefinierte Basis-URL für OpenAI-kompatible APIs. | `https://api.openai.com/v1` |
| `DEFAULT_OPENAI_API_MODEL` | Das OpenAI-Modell, das für TTS verwendet werden soll (z. B. `tts-1`). | `tts-1` |
| `DEFAULT_LLM_BASE_URL` | Die Basis-URL für die Large Language Model (LLM) API, kompatibel mit dem OpenAI-API-Format. | `""` |
| `DEFAULT_LLM_API_KEY` | Der API-Schlüssel für den LLM-Dienst. | `""` |
| `DEFAULT_LLM_MODEL` | Das Standardmodell, das für den LLM-Dienst verwendet werden soll (z. B. `gpt-4`). | `""` |

## 🔧 Fehlerbehebung

Hier sind einige häufige Probleme und deren Lösungen:

### 1. Warum sind keine Bücher in meiner Calibre-Liste?

*   **A**: Bitte stellen Sie sicher, dass Sie den Calibre Content Server in Ihrem Calibre-Client oder Container gestartet haben. Er läuft normalerweise auf Port `8080`. Denken Sie daran, diese Anwendung verbindet sich mit `calibre-server`, nicht mit `calibre-web` (das normalerweise auf Port `8083` läuft).
*   **B**: Überprüfen Sie, ob Ihre Calibre-Server-URL, Ihr Benutzername und Ihr Passwort in den Einstellungen korrekt sind. Sie können dies testen, indem Sie die konfigurierte URL in Ihrem Browser öffnen und versuchen, sich anzumelden.

### 2. Warum erhalte ich einen `401 Unauthorized`-Fehler beim Hochladen/Bearbeiten von Büchern?

*   **A**: Stellen Sie sicher, dass das von Ihnen konfigurierte Calibre-Benutzerkonto Schreibrechte für die Bibliothek hat. Um dies zu überprüfen, gehen Sie in der Calibre-Desktop-Anwendung zu `Einstellungen` -> `Über das Netzwerk teilen` -> `Benutzerkonten` und stellen Sie sicher, dass die Option "Schreibzugriff erlauben" für den Benutzer aktiviert ist.

### 3. Warum erhalte ich einen `403 Forbidden`-Fehler beim Hochladen/Bearbeiten von Büchern?

*   **A**: Dies bedeutet normalerweise, dass Sie eine falsche Calibre-Bibliotheks-ID konfiguriert haben.

### 4. Wie finde ich meine `library_id`?

*   **Methode 1 (Visuell)**: Öffnen Sie Ihren Calibre Content Server in einem Browser und melden Sie sich an. Schauen Sie sich den Namen Ihrer Bibliothek an, der auf der Seite angezeigt wird. Die `library_id` ist normalerweise dieser Name, bei dem Leerzeichen und Sonderzeichen durch Unterstriche ersetzt sind. Wenn Ihre Bibliothek beispielsweise "Calibre Library" heißt, lautet die ID wahrscheinlich `Calibre_Library`.
*   **Methode 2 (Aus der URL)**: Klicken Sie in der Content-Server-Oberfläche auf den Namen Ihrer Bibliothek. Schauen Sie sich die URL in der Adressleiste Ihres Browsers an. Sie sollten einen Parameter wie `library_id=...` sehen. Der Wert dieses Parameters ist Ihre Bibliotheks-ID (er könnte URL-kodiert sein, sodass Sie ihn möglicherweise dekodieren müssen).
*   **Häufige Standard-IDs**: Die Standard-Bibliotheks-ID hängt oft von der Sprache Ihres Systems ab, als Sie Calibre zum ersten Mal ausgeführt haben. Hier sind einige häufige Standardwerte:
    *   Englisch: `Calibre_Library`
    *   Französisch: `Bibliothèque_calibre`
    *   Deutsch: `Calibre-Bibliothek`
    *   Spanisch: `Biblioteca_de_calibre`
    *   Vereinfachtes Chinesisch (简体中文): `Calibre_书库`
    *   Traditionelles Chinesisch (繁體中文): `calibre_書庫`

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

### Beispiel-Prompts

Hier sind einige Beispiele für natürlichsprachige Prompts, die Sie mit einem KI-Agenten verwenden könnten, der Zugriff auf diese Werkzeuge hat. Der Agent würde intelligent ein oder mehrere Werkzeuge aufrufen, um Ihre Anfrage zu erfüllen.

- **Einfache & Erweiterte Suche**:
  - > "Finde Bücher über Python-Programmierung."
  - > "Suche nach Science-Fiction-Büchern von Isaac Asimov, die nach 1950 veröffentlicht wurden."

- **Buchverwaltung**:
  - > "Was sind die 5 zuletzt hinzugefügten Bücher? Sende das erste an meinen Kindle."
  - > "Schiebe das Buch 'Dune' auf meinen Anx-Reader."
  - > "Generiere ein Hörbuch für das Buch 'Die drei Sonnen'."
  - > "Wie ist der Status der Hörbuchgenerierung für 'Die drei Sonnen'?"

- **Inhaltsinteraktion & Zusammenfassung**:
  - > "Zeig mir das Inhaltsverzeichnis für das Buch 'Foundation'."
  - > "Hole das erste Kapitel von 'Foundation' und gib mir eine Zusammenfassung."
  - > "Was sind die Hauptideen der Psychohistorie, basierend auf dem Kapitel 'Die Psychohistoriker' aus dem Buch 'Foundation'?"
  - > "Lies das ganze Buch 'Der kleine Prinz' und verrate mir das Geheimnis des Fuchses."

- **Lesestatistiken & Fortschritt**:
  - > "Wie viele Wörter hat das Buch 'Dune' insgesamt und liste die Wortzahl für jedes Kapitel auf."
  - > "Wie viele Bücher habe ich dieses Jahr gelesen?"
  - > "Wie ist mein Lesefortschritt bei 'Dune'?"
  - > "Wer ist der Autor von 'Project Hail Mary' und wie lange lese ich es schon?"

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
-   `get_calibre_epub_entire_content`: Ruft den gesamten Inhalt eines Calibre-Buches ab.
-   `get_anx_epub_entire_content`: Ruft den gesamten Inhalt eines Buches aus der Anx-Bibliothek ab.
-   `get_calibre_book_word_count_stats`: Ruft die Wortzahlstatistiken für ein Calibre-Buch ab (Gesamtzahl und pro Kapitel).
-   `get_anx_book_word_count_stats`: Ruft die Wortzahlstatistiken für ein Buch aus der Anx-Bibliothek ab (Gesamtzahl und pro Kapitel).
-   `generate_audiobook`: Generiert ein Hörbuch für ein Buch aus der Anx- oder Calibre-Bibliothek.
-   `get_audiobook_generation_status`: Ruft den Status einer Hörbuch-Generierungsaufgabe anhand ihrer Aufgaben-ID ab.
-   `get_audiobook_status_by_book`: Ruft den Status der neuesten Hörbuch-Aufgabe für ein bestimmtes Buch anhand seiner ID und des Bibliothekstyps ab.

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

## 🙏 Danksagung

Dieses Projekt verwendet die folgenden Open-Source-Projekte:

-   [foliate-js](https://github.com/johnfactotum/foliate-js) für die Bereitstellung der E-Book-Vorschaufunktion.
-   [ebook-converter](https://github.com/gryf/ebook-converter) für die Bereitstellung der E-Book-Konvertierungsfunktion.

## 📄 Lizenz

Dieses Projekt ist unter der GPLv3-Lizenz lizenziert.