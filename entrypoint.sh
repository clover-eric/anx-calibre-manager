#!/bin/sh
set -e

# Get the UID and GID from environment variables, with a default of 1001
PUID=${PUID:-1001}
PGID=${PGID:-1001}

# Check if the group exists, if not create it
if ! getent group "$PGID" >/dev/null; then
    addgroup -g "$PGID" appuser
fi

# Check if the user exists, if not create it
if ! getent passwd "$PUID" >/dev/null; then
    adduser -D -u "$PUID" -G appuser appuser
fi

# Update the user's UID and GID
usermod -o -u "$PUID" appuser
groupmod -o -g "$PGID" appuser

echo "
User UID : $(id -u appuser)
User GID : $(id -g appuser)
"

# Take ownership of the config and data directories
chown -R appuser:appuser /config /webdav

# Execute the command passed to this script (the Dockerfile's CMD)
exec gosu appuser "$@"