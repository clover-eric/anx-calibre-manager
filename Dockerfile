# Stage 1: Builder - To build dependencies
FROM python:3.9-slim-bullseye AS builder

# Set the working directory
WORKDIR /app

# Install build tools needed for some Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential

# Create a non-root user for security
RUN useradd --create-home appuser
WORKDIR /home/appuser

# Create and activate a virtual environment
RUN python -m venv /home/appuser/venv
ENV PATH="/home/appuser/venv/bin:$PATH"

# Copy only the requirements file to leverage Docker cache
COPY --chown=appuser:appuser requirements.txt .

# Install dependencies into the virtual environment
RUN pip install --no-cache-dir -r requirements.txt && pip install gunicorn

# Stage 2: Final image - For running the application
FROM python:3.9-slim-bullseye

# Install gosu for user switching
RUN apt-get update && \
    apt-get install -y --no-install-recommends gosu && \
    rm -rf /var/lib/apt/lists/*

# Set environment variables for the application.
ENV PORT=5000
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

# Create app user and standard directories as root
RUN useradd --uid 1001 --create-home appuser && \
    mkdir -p /config /webdav && \
    chown -R appuser:appuser /config /webdav

# Set working directory
WORKDIR /home/appuser

# Copy the virtual environment and application source code from builder stage
COPY --from=builder --chown=appuser:appuser /home/appuser/venv ./venv
COPY --chown=appuser:appuser . .

# Copy the entrypoint script
COPY --chown=appuser:appuser entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Activate the virtual environment
ENV PATH="/home/appuser/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE $PORT

# Define volumes for persistent data
VOLUME ["/config", "/webdav"]

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Define the default command
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "3", "app:create_app()"]