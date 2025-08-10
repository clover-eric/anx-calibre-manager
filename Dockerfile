# Stage 1: Builder - To build dependencies
FROM python:3.9-slim AS builder

# Set the working directory
WORKDIR /app

# Install build tools needed for some Python packages
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

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
FROM python:3.9-slim

# Set environment variables for the application
# These can be overridden at runtime (e.g., with `docker run -e ...`)
ENV PORT=5000
ENV DATA_DIR=/data
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

# Create the data directory and a non-root user
RUN mkdir -p ${DATA_DIR}/config && \
    mkdir -p ${DATA_DIR}/webdav && \
    useradd --create-home appuser && \
    chown -R appuser:appuser ${DATA_DIR}

# Copy the virtual environment from the builder stage
COPY --from=builder /home/appuser/venv /home/appuser/venv

# Copy the application source code
WORKDIR /home/appuser
COPY --chown=appuser:appuser . .

# Switch to the non-root user
USER appuser

# Activate the virtual environment
ENV PATH="/home/appuser/venv/bin:$PATH"

# Expose the port the app runs on
EXPOSE $PORT

# Define a volume for persistent data
VOLUME $DATA_DIR

# Define the command to run the application
CMD ["gunicorn", "--bind", "0.0.0.0:$PORT", "--workers", "4", "app:create_app()"]