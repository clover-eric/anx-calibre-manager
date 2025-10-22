#!/bin/sh
set -e

# Get the UID and GID from environment variables, with a default of 1001
PUID=${PUID:-1001}
PGID=${PGID:-1001}

# Ensure group 'appuser' exists with the correct GID
if ! getent group appuser >/dev/null; then
    addgroup --gid "$PGID" appuser
else
    groupmod -o -g "$PGID" appuser
fi

# Ensure user 'appuser' exists with the correct UID
if ! getent passwd appuser >/dev/null; then
    adduser --system --disabled-password --uid "$PUID" --ingroup appuser appuser
else
    usermod -o -u "$PUID" appuser
fi

echo "
User UID : $(id -u appuser)
User GID : $(id -g appuser)
"

# Create logs directory if it doesn't exist
mkdir -p /config/logs

# Take ownership of the config and data directories
chown -R appuser:appuser /config /webdav

# Check if calibre-server is installed (AIO mode)
if command -v calibre-server >/dev/null 2>&1; then
    echo "AIO mode detected: Starting calibre-server..."
    
    # Parse port from CALIBRE_URL (default: http://localhost:8080)
    CALIBRE_URL=${CALIBRE_URL:-http://localhost:8080}
    CALIBRE_SERVER_PORT=$(echo "$CALIBRE_URL" | sed -n 's/.*:\([0-9]\+\).*/\1/p')
    CALIBRE_SERVER_PORT=${CALIBRE_SERVER_PORT:-8080}
    
    # Set default credentials
    CALIBRE_USERNAME=${CALIBRE_USERNAME:-admin}
    CALIBRE_PASSWORD=${CALIBRE_PASSWORD:-password}
    
    # Ensure /Calibre Library directory ownership
    if [ -d "/Calibre Library" ]; then
        chown -R appuser:appuser "/Calibre Library"
    fi
    
    # Initialize empty Calibre library if metadata.db doesn't exist
    if [ ! -f "/Calibre Library/metadata.db" ]; then
        echo "No existing Calibre library found. Initializing empty library..."
        CALIBRE_DEFAULT_LIBRARY_ID=${CALIBRE_DEFAULT_LIBRARY_ID:-Calibre_Library}
        
        # Create library directory if it doesn't exist
        mkdir -p "/Calibre Library"
        
        # Initialize empty library using calibredb (suppress error output)
        # The --with-library option specifies the library path
        gosu appuser calibredb restore_database --really-do-it --with-library "/Calibre Library" >/dev/null 2>&1 || {
            # Alternative: Create a minimal metadata.db by listing (which auto-creates if missing)
            gosu appuser calibredb list --with-library "/Calibre Library" >/dev/null 2>&1 || true
        }
        
        # Add custom columns for user library tracking and read date
        echo "Adding custom columns #library and #readdate..."
        
        # Add #library column (Text column, comma separated)
        gosu appuser calibredb add_custom_column \
            --with-library "/Calibre Library" \
            library "Library" text \
            --is-multiple \
            >/dev/null 2>&1 || echo "Note: #library column may already exist or failed to create"
        
        # Add #readdate column (Date column)
        gosu appuser calibredb add_custom_column \
            --with-library "/Calibre Library" \
            readdate "Read Date" datetime \
            >/dev/null 2>&1 || echo "Note: #readdate column may already exist or failed to create"
        
        echo "Empty Calibre library initialized at /Calibre Library with ID: $CALIBRE_DEFAULT_LIBRARY_ID"
        echo "Custom columns #library and #readdate have been added"
        chown -R appuser:appuser "/Calibre Library"
    else
        echo "Existing Calibre library found at /Calibre Library"
    fi
    
    # Create user database if it doesn't exist or is corrupted
    if [ ! -f /config/calibre-users.sqlite ]; then
        echo "Creating calibre-server user database..."
        # Remove any existing corrupted database file
        rm -f /config/calibre-users.sqlite /config/calibre-users.sqlite-journal
        
        # Create the user database with proper ownership
        gosu appuser calibre-server \
            --userdb /config/calibre-users.sqlite \
            --manage-users add "$CALIBRE_USERNAME" "$CALIBRE_PASSWORD" 2>&1 || {
            echo "Failed to create user database, retrying..."
            rm -f /config/calibre-users.sqlite /config/calibre-users.sqlite-journal
            sleep 1
            gosu appuser calibre-server \
                --userdb /config/calibre-users.sqlite \
                --manage-users add "$CALIBRE_USERNAME" "$CALIBRE_PASSWORD"
        }
        
        # Ensure proper ownership
        chown appuser:appuser /config/calibre-users.sqlite 2>/dev/null || true
    else
        # Verify existing database is accessible
        if ! gosu appuser calibre-server --userdb /config/calibre-users.sqlite --manage-users list >/dev/null 2>&1; then
            echo "Existing user database is corrupted, recreating..."
            rm -f /config/calibre-users.sqlite /config/calibre-users.sqlite-journal
            gosu appuser calibre-server \
                --userdb /config/calibre-users.sqlite \
                --manage-users add "$CALIBRE_USERNAME" "$CALIBRE_PASSWORD"
            chown appuser:appuser /config/calibre-users.sqlite 2>/dev/null || true
        fi
    fi
    
    # Start calibre-server in background
    echo "Starting calibre-server on port $CALIBRE_SERVER_PORT..."
    gosu appuser calibre-server \
        --enable-auth \
        --userdb /config/calibre-users.sqlite \
        --port="$CALIBRE_SERVER_PORT" \
        --enable-local-write \
        --log=/config/logs/calibre-server.log \
        --access-log=/config/logs/calibre-server-access.log \
        "/Calibre Library" &
    
    echo "calibre-server started with PID $!"
fi

# Execute the command passed to this script (the Dockerfile's CMD)
exec gosu appuser "$@"