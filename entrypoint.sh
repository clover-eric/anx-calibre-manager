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

# Execute the command passed to this script (the Dockerfile's CMD)
exec gosu appuser "$@"