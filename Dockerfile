# Stage 1: Builder - To build dependencies
FROM python:3.12-slim-bookworm AS builder

# Set the working directory
WORKDIR /app

# Install build tools and dependencies for ebook-converter
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    git \
    pkg-config \
    libxml2-dev \
    libxslt-dev \
    poppler-utils \
    fonts-liberation \
    zip

# Create a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Create a virtual environment for building ebook-converter
RUN python -m venv /home/appuser/build_venv

# Install pyinstaller and build ebook-converter
RUN /home/appuser/build_venv/bin/pip install pyinstaller git+https://github.com/gryf/ebook-converter.git && \
    /home/appuser/build_venv/bin/pyinstaller --onefile --name ebook-converter --add-data /home/appuser/build_venv/lib/python3.12/site-packages/ebook_converter/data:ebook_converter/data /home/appuser/build_venv/bin/ebook-converter

# Create and activate a virtual environment for the app
RUN python -m venv /home/appuser/venv
ENV PATH="/home/appuser/venv/bin:$PATH"

# Copy only the requirements file to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .

# Upgrade pip and setuptools, then install dependencies
RUN /home/appuser/venv/bin/pip install --upgrade pip setuptools && \
    /home/appuser/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    /home/appuser/venv/bin/pip install gunicorn

# Stage 2: Final image - For running the application
FROM python:3.12-slim-bookworm

# Install gosu for user switching, tini for signal handling, and runtime deps for ebook-converter
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gosu \
    tini \
    poppler-utils \
    fonts-liberation \
    zip \
    locales \
    libxml2 && \
    rm -rf /var/lib/apt/lists/*

# Configure locales
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# zh_CN.UTF-8 UTF-8/zh_CN.UTF-8 UTF-8/' /etc/locale.gen && \
    sed -i -e 's/# zh_TW.UTF-8 UTF-8/zh_TW.UTF-8 UTF-8/' /etc/locale.gen && \
    dpkg-reconfigure --frontend=noninteractive locales

# Set environment variables for the application.
ENV LANG zh_CN.UTF-8
ENV LC_ALL zh_CN.UTF-8
ENV PORT=5000
ENV GUNICORN_WORKERS=2
# The following are placeholders and should be set securely at runtime
ENV SECRET_KEY=""
ENV CALIBRE_URL=""
ENV CALIBRE_USERNAME=""
ENV CALIBRE_PASSWORD=""
ENV SMTP_SERVER=""
ENV SMTP_PORT=587
ENV SMTP_USERNAME=""
ENV SMTP_PASSWORD=""
ENV SMTP_ENCRYPTION="ssl"
ENV CALIBRE_DEFAULT_LIBRARY_ID="Calibre_Library"
ENV CALIBRE_ADD_DUPLICATES="false"

# Create app user and standard directories as root
RUN useradd --uid 1001 --create-home appuser && \
    mkdir -p /config /webdav /tmp && \
    chown -R appuser:appuser /config /webdav /tmp

# Set working directory
WORKDIR /home/appuser

# Copy the application virtual environment and the compiled ebook-converter binary
COPY --from=builder --chown=appuser:appuser /home/appuser/venv ./venv
COPY --from=builder --chown=appuser:appuser /home/appuser/dist/ebook-converter /usr/local/bin/ebook-converter
COPY --chown=appuser:appuser . .

# Extract, initialize all language files, populate English, auto-translate others, and compile.
RUN . venv/bin/activate && \
    #mkdir -p translations/en/LC_MESSAGES translations/zh_Hans/LC_MESSAGES translations/zh_Hant/LC_MESSAGES translations/es/LC_MESSAGES translations/fr/LC_MESSAGES translations/de/LC_MESSAGES && \
    #pybabel extract -F babel.cfg -o messages.pot . && \
    #pybabel init -i messages.pot -d translations -l en && \
    #pybabel init -i messages.pot -d translations -l zh_Hans && \
    #pybabel init -i messages.pot -d translations -l zh_Hant && \
    #pybabel init -i messages.pot -d translations -l es && \
    #pybabel init -i messages.pot -d translations -l fr && \
    #pybabel init -i messages.pot -d translations -l de && \
    python populate_en_po.py && \
    #python auto_translate.py zh_Hans zh_Hant es fr de && \
    pybabel compile -d translations

# Package the KOReader plugin into a zip file, preserving the top-level directory
RUN zip -r /home/appuser/static/anx-calibre-manager-koreader-plugin.zip anx-calibre-manager-koreader-plugin.koplugin

# Copy the entrypoint script
COPY --chown=appuser:appuser entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Activate the virtual environment
ENV PATH="/home/appuser/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE $PORT

# Define volumes for persistent data
VOLUME ["/config", "/webdav"]

# Set the entrypoint to use tini for proper signal handling
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]

# Define the default command
# The --pid flag tells Gunicorn to write its master process ID to a file.
# This allows us to send signals (like SIGHUP for reloading) to it.
CMD gunicorn --bind 0.0.0.0:$PORT --workers ${GUNICORN_WORKERS} --timeout 180 --pid /tmp/gunicorn.pid "app:create_app()"