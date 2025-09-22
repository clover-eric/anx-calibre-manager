# Anx Calibre Manager

[![Docker Image CI](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml/badge.svg)](https://github.com/ptbsare/anx-calibre-manager/actions/workflows/docker-ci.yml)
[![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ptbsare%2Fanx--calibre--manager-blue?logo=github)](https://github.com/ptbsare/anx-calibre-manager/pkgs/container/anx-calibre-manager)

Une application web moderne et axée sur le mobile pour gérer votre bibliothèque de livres électroniques, s'intégrant à Calibre et fournissant un serveur WebDAV personnel pour vos appareils compatibles avec Anx-reader.

<p align="center">
  <strong><a href="README.md">English</a></strong> |
  <strong><a href="README_zh-Hans.md">简体中文</a></strong> |
  <strong><a href="README_zh-Hant.md">繁體中文</a></strong> |
  <strong><a href="README_es.md">Español</a></strong> |
  <strong><a href="README_fr.md">Français</a></strong> |
  <strong><a href="README_de.md">Deutsch</a></strong>
</p>

## ✨ Fonctionnalités

- **Support Multilingue**: Prise en charge complète de l'internationalisation. L'interface est disponible en anglais, chinois simplifié (简体中文), chinois traditionnel (繁體中文), espagnol, français et allemand.
- **Interface Axée sur le Mobile**: Une interface utilisateur propre et réactive conçue pour une utilisation facile sur votre téléphone.
- **Support PWA**: Installable en tant qu'application web progressive pour une expérience similaire à une application native.
- **Visionneuse de livres dans le navigateur**: Prévisualisez les livres électroniques directement dans votre navigateur. Comprend une fonction de synthèse vocale (TTS).
- **Génération de Livres Audio**: Convertissez des livres EPUB en livres audio M4B avec des marqueurs de chapitre, en utilisant des fournisseurs de synthèse vocale (TTS) configurables (par ex., Microsoft Edge TTS). Les fichiers M4B générés sont entièrement compatibles avec des serveurs de livres audio comme [Audiobookshelf](https://www.audiobookshelf.org/).
- **Lecteur de Livres Audio en Ligne**: Écoutez vos livres audio M4B générés directement dans le navigateur. Votre progression d'écoute est automatiquement sauvegardée et synchronisée.
- **Intégration Calibre**: Se connecte à votre serveur Calibre existant pour parcourir et rechercher votre bibliothèque.
- **Synchronisation KOReader**: Synchronisez votre progression de lecture et votre temps de lecture avec les appareils KOReader.
- **Envoi Intelligent vers Kindle**: Gère automatiquement les formats lors de l'envoi vers votre Kindle. Si un EPUB existe, il est envoyé directement. Sinon, l'application **convertit le meilleur format disponible en EPUB** selon vos préférences avant de l'envoyer, garantissant une compatibilité optimale.
- **Pousser vers Anx**: Envoyez des livres de votre bibliothèque Calibre directement dans le dossier de votre appareil Anx-reader personnel.
- **Serveur WebDAV Intégré**: Chaque utilisateur dispose de son propre dossier WebDAV sécurisé, compatible avec Anx-reader et d'autres clients WebDAV.
- **Serveur MCP**: Un serveur intégré et conforme au Protocole de Contexte de Modèle (MCP), permettant aux agents IA et aux outils externes d'interagir en toute sécurité avec votre bibliothèque.
- **Gestion des Utilisateurs**: Système de gestion des utilisateurs simple et intégré avec des rôles distincts :
    - **Admin**: Contrôle total sur les utilisateurs, les paramètres globaux et tous les livres.
    - **Mainteneur**: Peut modifier les métadonnées de tous les livres.
    - **Utilisateur**: Peut téléverser des livres, gérer sa propre bibliothèque WebDAV, ses jetons MCP, envoyer des livres à Kindle et **modifier les livres qu'il a téléversés**.
- **Inscription sur Invitation Uniquement**: Les administrateurs peuvent générer des codes d'invitation pour contrôler l'inscription des utilisateurs. Cette fonctionnalité est activée par défaut pour empêcher les inscriptions non autorisées.
- **Livres Téléversés Modifiables par l'Utilisateur**: Les utilisateurs réguliers peuvent désormais modifier les métadonnées des livres qu'ils ont téléversés. Cette fonctionnalité repose sur une colonne personnalisée de Calibre nommée `#library` (type : `Texte, avec les virgules traitées comme des balises distinctes`). Lorsqu'un utilisateur téléverse un livre, son nom d'utilisateur est automatiquement enregistré dans ce champ. Les utilisateurs peuvent alors modifier tout livre où ils sont listés comme propriétaires dans le champ `#library`.
    - **Recommandation pour les Utilisateurs de Docker**: Pour activer cette fonctionnalité, veuillez vous assurer que vous avez une colonne personnalisée dans votre bibliothèque Calibre nommée `#library` (sensible à la casse) de type `Texte, avec les virgules traitées comme des balises distinctes`.
- **Déploiement Facile**: Déployable en tant que conteneur Docker unique avec prise en charge des locales multilingues intégrée.
- **Statistiques de Lecture**: Génère automatiquement une page de statistiques de lecture personnelle, avec une carte de chaleur de lecture annuelle, une liste des livres en cours de lecture et une liste des livres terminés. La page peut être partagée publiquement ou rester privée.

## 📸 Captures d'écran

<p align="center">
  <em>Interface Principale</em><br>
  <img src="screenshots/Screen Shot - MainPage.png">
</p>
<p align="center">
  <em>Page des Paramètres</em><br>
  <img src="screenshots/Screen Shot - SettingPage.png">
</p>

| Chat MCP | Paramètres MCP |
| :---: | :---: |
| <img src="screenshots/Screen Shot - MCPChat.jpg" width="350"/> | <img src="screenshots/Screen Shot - MCPSetting.png" width="650"/> |

| Statut du Livre Koreader | Synchronisation Koreader |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderBookStatus.jpg" width="400"/> | <img src="screenshots/Screen Shot - KoreaderSync.jpg" width="400"/> |

| Paramètres Koreader | WebDAV Koreader |
| :---: | :---: |
| <img src="screenshots/Screen Shot - KoreaderSetting.png" width="750"/> | <img src="screenshots/Screen Shot - KoreaderWebdav.jpg" width="250"/> |

<p align="center">
  <em>Page des Statistiques</em><br>
  <img src="screenshots/Screen Shot - StatsPage.png">
</p>

## 🚀 Déploiement

Cette application est conçue pour être déployée avec Docker.

### Prérequis

- [Docker](https://www.docker.com/get-started) installé sur votre serveur.
- [ffmpeg](https://ffmpeg.org/download.html) installé sur votre serveur et disponible dans le PATH du système. Ceci est requis pour la génération de livres audio.
- Un serveur Calibre existant (facultatif, mais requis pour la plupart des fonctionnalités).

### Exécuter avec Docker

1.  **Trouvez votre ID d'Utilisateur et de Groupe (PUID/PGID) :**
    Exécutez `id $USER` sur votre machine hôte pour obtenir l'UID et le GID de votre utilisateur. C'est crucial pour éviter les problèmes de permissions avec les volumes montés.

    ```bash
    id $USER
    # Exemple de sortie : uid=1000(monutilisateur) gid=1000(monutilisateur) ...
    ```

2.  **Créez des répertoires pour les données persistantes :**
    Vous avez besoin de répertoires distincts pour la configuration/base de données et pour les données WebDAV.

    ```bash
    mkdir -p /chemin/vers/votre/config
    mkdir -p /chemin/vers/votre/webdav
    mkdir -p /chemin/vers/vos/audiobooks # Facultatif : pour les livres audio générés
    mkdir -p /chemin/vers/vos/polices # Facultatif : pour les polices personnalisées
    ```

3.  **Exécutez le conteneur Docker :**
    Vous pouvez utiliser `docker run` ou un fichier `docker-compose.yml`.

    **Avec `docker run` :**

    ```bash
    docker run -d \
      --name anx-calibre-manager \
      -p 5000:5000 \
      -e PUID=1000 \
      -e PGID=1000 \
      -e TZ="Europe/Paris" \
      -v /chemin/vers/votre/config:/config \
      -v /chemin/vers/votre/webdav:/webdav \
      -v /chemin/vers/vos/audiobooks:/audiobooks \ # Facultatif : Monter le répertoire de sortie des livres audio
      -v /chemin/vers/vos/polices:/opt/share/fonts \ # Facultatif : Monter des polices personnalisées
      -e "GUNICORN_WORKERS=2" \
      -e "SECRET_KEY=votre_super_cle_secrete" \
      -e "CALIBRE_URL=http://ip-de-votre-serveur-calibre:8080" \
      -e "CALIBRE_USERNAME=votre_nom_utilisateur_calibre" \
      -e "CALIBRE_PASSWORD=votre_mot_de_passe_calibre" \
      --restart unless-stopped \
      ghcr.io/ptbsare/anx-calibre-manager:latest
    ```

    **Avec `docker-compose.yml` :**

    Créez un fichier `docker-compose.yml` :
    ```yaml
    version: '3.8'
    services:
      anx-calibre-manager:
        image: ghcr.io/ptbsare/anx-calibre-manager:latest
        container_name: anx-calibre-manager
        ports:
          - "5000:5000"
        volumes:
          - /chemin/vers/votre/config:/config
          - /chemin/vers/votre/webdav:/webdav
          - /chemin/vers/vos/audiobooks:/audiobooks # Facultatif : Monter le répertoire de sortie des livres audio
          - /chemin/vers/vos/polices:/opt/share/fonts # Facultatif : Monter des polices personnalisées
        environment:
          - PUID=1000
          - PGID=1000
          - TZ=Europe/Paris
          - GUNICORN_WORKERS=2 # Facultatif : Personnalisez le nombre de processus Gunicorn
          - SECRET_KEY=votre_super_cle_secrete
          - CALIBRE_URL=http://ip-de-votre-serveur-calibre:8080
          - CALIBRE_USERNAME=votre_nom_utilisateur_calibre
          - CALIBRE_PASSWORD=votre_mot_de_passe_calibre
          - CALIBRE_DEFAULT_LIBRARY_ID=Calibre_Library
          - CALIBRE_ADD_DUPLICATES=false
        restart: unless-stopped
    ```
    Puis exécutez :
    ```bash
    docker-compose up -d
    ```

### Polices Personnalisées

L'outil de conversion de livres, `ebook-converter`, scanne le répertoire `/opt/share/fonts` à la recherche de polices. Si vous rencontrez des problèmes liés aux polices lors de la conversion de livres avec des caractères spéciaux (par exemple, le chinois), vous pouvez fournir des polices personnalisées en montant un répertoire local contenant vos fichiers de polices (par exemple, `.ttf`, `.otf`) sur le chemin `/opt/share/fonts` du conteneur.

### Configuration

L'application est configurée via des variables d'environnement.

| Variable | Description | Défaut |
| --- | --- | --- |
| `PUID` | L'ID utilisateur pour exécuter l'application. | `1001` |
| `PGID` | L'ID de groupe pour exécuter l'application. | `1001` |
| `TZ` | Votre fuseau horaire, ex: `Europe/Paris`. | `UTC` |
| `PORT` | Le port sur lequel l'application écoute à l'intérieur du conteneur. | `5000` |
| `GUNICORN_WORKERS` | Facultatif : Le nombre de processus Gunicorn. | `2` |
| `CONFIG_DIR` | Le répertoire pour la base de données et `settings.json`. | `/config` |
| `WEBDAV_DIR` | Le répertoire de base pour les fichiers utilisateur WebDAV. | `/webdav` |
| `SECRET_KEY` | **Requis.** Une longue chaîne aléatoire pour la sécurité des sessions. | `""` |
| `CALIBRE_URL` | L'URL de votre serveur de contenu Calibre. | `""` |
| `CALIBRE_USERNAME` | Nom d'utilisateur pour votre serveur Calibre. | `""` |
| `CALIBRE_PASSWORD` | Mot de passe pour votre serveur Calibre. | `""` |
| `CALIBRE_DEFAULT_LIBRARY_ID` | L'ID de la bibliothèque Calibre par défaut pour la navigation, la recherche et le téléversement de livres. | `Calibre_Library` |
| `CALIBRE_ADD_DUPLICATES` | Autoriser le téléversement de livres en double. | `false` |
| `REQUIRE_INVITE_CODE` | Exiger un code d'invitation pour l'inscription. | `true` |
| `SMTP_SERVER` | Serveur SMTP pour l'envoi d'e-mails (ex: pour Kindle). | `""` |
| `SMTP_PORT` | Port SMTP. | `587` |
| `SMTP_USERNAME` | Nom d'utilisateur SMTP. | `""` |
| `SMTP_PASSWORD` | Mot de passe SMTP. | `""` |
| `SMTP_ENCRYPTION` | Type de chiffrement SMTP (`ssl`, `starttls`, `none`). | `ssl` |
| `DEFAULT_TTS_PROVIDER` | Le fournisseur TTS par défaut pour la génération de livres audio (`edge_tts` ou `openai_tts`). | `edge_tts` |
| `DEFAULT_TTS_VOICE` | La voix par défaut pour le fournisseur TTS sélectionné. | `en-US-AriaNeural` |
| `DEFAULT_TTS_RATE` | La vitesse de parole par défaut pour le fournisseur TTS (par ex., `+10%`). | `+0%` |
| `DEFAULT_OPENAI_API_KEY` | Votre clé API OpenAI (requise si vous utilisez `openai_tts`). | `""` |
| `DEFAULT_OPENAI_API_BASE_URL` | URL de base personnalisée pour les API compatibles avec OpenAI. | `https://api.openai.com/v1` |
| `DEFAULT_OPENAI_API_MODEL` | Le modèle OpenAI à utiliser pour le TTS (par ex., `tts-1`). | `tts-1` |

## 📖 Synchronisation KOReader

Vous pouvez synchroniser votre progression de lecture et votre temps de lecture entre votre bibliothèque Anx et vos appareils KOReader. La configuration se fait en deux étapes principales : la configuration de WebDAV pour accéder à vos livres et la configuration du plugin de synchronisation pour gérer la synchronisation de la progression.

### Étape 1 : Configurer le Stockage Cloud WebDAV

Cette étape vous permet de parcourir et de lire les livres de votre bibliothèque Anx directement dans KOReader.

1.  Dans KOReader, allez dans `Stockage cloud` -> `Ajouter un nouveau stockage cloud`.
2.  Sélectionnez `WebDAV`.
3.  Remplissez les détails :
    -   **Adresse du serveur**: Entrez l'URL WebDAV affichée dans la page des paramètres de Anx Calibre Manager (`Paramètres` -> `Paramètres de synchronisation Koreader`). **Assurez-vous que le chemin se termine par un `/`**.
    -   **Nom d'utilisateur**: Votre nom d'utilisateur Anx Calibre Manager.
    -   **Mot de passe**: Votre mot de passe de connexion Anx Calibre Manager.
    -   **Dossier**: `/anx/data/file`
4.  Appuyez sur `Connecter` et enregistrez. Vous devriez maintenant pouvoir voir votre bibliothèque Anx dans l'explorateur de fichiers de KOReader.

### Étape 2 : Installer et Configurer le Plugin de Synchronisation

Ce plugin renvoie votre progression de lecture au serveur Anx Calibre Manager.

1.  **Télécharger le Plugin**:
    -   Connectez-vous à Anx Calibre Manager.
    -   Allez dans `Paramètres` -> `Paramètres de synchronisation Koreader`.
    -   Cliquez sur le bouton `Télécharger le plugin KOReader (.zip)` pour obtenir le paquet du plugin.
2.  **Installer le Plugin**:
    -   Décompressez le fichier téléchargé pour obtenir un dossier nommé `anx-calibre-manager-koreader-plugin.koplugin`.
    -   Copiez ce dossier entier dans le répertoire `koreader/plugins/` de votre appareil KOReader.
3.  **Redémarrer KOReader**: Fermez complètement et rouvrez l'application KOReader pour charger le nouveau plugin.
4.  **Configurer le Serveur de Synchronisation**:
    -   **Important**: Ouvrez d'abord un livre depuis le stockage WebDAV que vous avez configuré à l'étape 1. Le menu du plugin n'est **visible que dans la vue de lecture**.
    -   Dans la vue de lecture, allez dans `Outils (icône de clé à molette)` -> `Page suivante` -> `Plus d'outils` -> `ANX Calibre Manager`.
    -   Sélectionnez `Serveur de synchronisation personnalisé`.
    -   **Adresse du serveur de synchronisation personnalisé**: Entrez l'URL du serveur de synchronisation affichée dans la page des paramètres de Anx Calibre Manager (ex: `http://<votre_adresse_serveur>/koreader`).
    -   Revenez au menu précédent, sélectionnez `Connexion`, et entrez votre nom d'utilisateur et votre mot de passe Anx Calibre Manager.

Une fois configuré, le plugin synchronisera automatiquement ou manuellement votre progression de lecture. Vous pouvez ajuster des paramètres comme la fréquence de synchronisation dans le menu du plugin. **Note : Seule la progression des livres au format EPUB est prise en charge.**

## 🤖 Serveur MCP

Cette application inclut un serveur MCP (Model Context Protocol) compatible JSON-RPC 2.0, permettant aux outils externes et aux agents IA d'interagir avec votre bibliothèque.

### Comment l'utiliser

1.  **Générer un Jeton**: Après vous être connecté, allez à la page **Paramètres -> Paramètres MCP**. Cliquez sur "Générer un nouveau jeton" pour créer un nouveau jeton d'API.
2.  **URL de l'Endpoint**: L'endpoint du serveur MCP est `http://<votre_adresse_serveur>/mcp`.
3.  **Authentification**: Authentifiez-vous en ajoutant votre jeton en tant que paramètre de requête à l'URL, ex: `http://.../mcp?token=VOTRE_JETON`.
4.  **Envoyer des Requêtes**: Envoyez des requêtes `POST` à cet endpoint avec un corps conforme au format JSON-RPC 2.0.

### Exemples de Prompts

Voici quelques exemples de prompts en langage naturel que vous pourriez utiliser avec un agent IA ayant accès à ces outils. L'agent appellerait intelligemment un ou plusieurs outils pour répondre à votre demande.

- **Recherche Simple et Avancée**:
  - > "Trouver des livres sur la programmation en Python."
  - > "Rechercher des livres de science-fiction d'Isaac Asimov publiés après 1950."

- **Gestion de Livres**:
  - > "Quels sont les 5 derniers livres ajoutés ? Envoyez le premier à mon Kindle."
  - > "Pousser le livre 'Dune' sur mon lecteur Anx."

- **Interaction et Résumé de Contenu**:
  - > "Montre-moi la table des matières du livre 'Fondation'."
  - > "Récupère le premier chapitre de 'Fondation' et fais-moi un résumé."
  - > "D'après le chapitre 'Les Psychohistoriens' du livre 'Fondation', quelles sont les idées principales de la psychohistoire ?"
  - > "Lis tout le livre 'Le Petit Prince' et dis-moi quel est le secret du renard."

- **Statistiques et Progression de Lecture**:
  - > "Combien de mots compte le livre 'Dune' au total, et dresse la liste du nombre de mots pour chaque chapitre."
  - > "Combien de livres ai-je lus cette année ?"
  - > "Quelle est ma progression de lecture sur 'Dune' ?"
  - > "Qui est l'auteur de 'Project Hail Mary' et depuis combien de temps le lis-je ?"

### Outils Disponibles

Vous pouvez obtenir une liste de tous les outils disponibles en appelant la méthode `tools/list`. Les outils actuellement pris en charge sont :

-   **`search_calibre_books`**: Recherchez des livres en utilisant la puissante syntaxe de recherche de Calibre.
    -   **Paramètres**: `search_expression` (chaîne de caractères), `limit` (entier, facultatif).
    -   **Fonctionnalité**: Vous pouvez fournir des mots-clés simples pour une recherche large ou construire des requêtes complexes.
    -   **Exemple (Recherche Avancée)**: Trouver les livres de "O'Reilly Media" avec une note de 4 étoiles ou plus.
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
-   `get_recent_calibre_books`: Obtenir les livres récents de la bibliothèque Calibre.
-   `get_calibre_book_details`: Obtenir les détails d'un livre spécifique de Calibre.
-   `get_recent_anx_books`: Obtenir les livres récents de la bibliothèque Anx.
-   `get_anx_book_details`: Obtenir les détails d'un livre spécifique d'Anx.
-   `push_calibre_book_to_anx`: Pousser un livre de Calibre vers la bibliothèque Anx.
-   `send_calibre_book_to_kindle`: Envoyer un livre de Calibre à Kindle.
-   `get_calibre_epub_table_of_contents`: Obtenir la table des matières d'un livre Calibre.
-   `get_calibre_epub_chapter_content`: Obtenir le contenu d'un chapitre d'un livre Calibre.
-   `get_anx_epub_table_of_contents`: Obtenir la table des matières d'un livre de la bibliothèque Anx.
-   `get_anx_epub_chapter_content`: Obtenir le contenu d'un chapitre d'un livre de la bibliothèque Anx.
-   `get_calibre_epub_entire_content`: Obtenir le contenu complet d'un livre Calibre.
-   `get_anx_epub_entire_content`: Obtenir le contenu complet d'un livre de la bibliothèque Anx.
-   `get_calibre_book_word_count_stats`: Obtenir les statistiques de nombre de mots pour un livre Calibre (total et par chapitre).
-   `get_anx_book_word_count_stats`: Obtenir les statistiques de nombre de mots pour un livre de la bibliothèque Anx (total et par chapitre).

## 💻 Développement

1.  **Clonez le dépôt :**
    ```bash
    git clone https://github.com/ptbsare/anx-calibre-manager.git
    cd anx-calibre-manager
    ```

2.  **Créez un environnement virtuel :**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Installez les dépendances :**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Lancez le serveur de développement :**
    ```bash
    python app.py
    ```
    L'application sera disponible à l'adresse `http://localhost:5000`.

## 🤝 Contribution

Les contributions, les problèmes et les demandes de fonctionnalités sont les bienvenus ! N'hésitez pas à consulter la [page des problèmes](https://github.com/ptbsare/anx-calibre-manager/issues).

## 📄 Licence

Ce projet est sous licence GPLv3.