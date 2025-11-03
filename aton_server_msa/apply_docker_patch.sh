#!/bin/bash

###########################################
# Apply Docker Compatibility Patch
# Modifies comm2center.py to use environment variables
###########################################

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

COMM2CENTER_FILE="comm2center/comm2center.py"
BACKUP_FILE="comm2center/comm2center.py.original"

# Check if file exists
if [ ! -f "$COMM2CENTER_FILE" ]; then
    log_error "File not found: $COMM2CENTER_FILE"
    log_info "Please run this script from aton_server_msa directory"
    exit 1
fi

# Check if already patched
if grep -q "os.getenv('MQTT_HOST'" "$COMM2CENTER_FILE"; then
    log_warn "File appears to be already patched"
    read -p "Do you want to revert and re-apply the patch? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        if [ -f "$BACKUP_FILE" ]; then
            log_info "Restoring from backup..."
            cp "$BACKUP_FILE" "$COMM2CENTER_FILE"
        else
            log_error "No backup file found"
            exit 1
        fi
    else
        log_info "Skipping patch"
        exit 0
    fi
fi

# Create backup
log_info "Creating backup: $BACKUP_FILE"
cp "$COMM2CENTER_FILE" "$BACKUP_FILE"

# Apply patch
log_info "Applying Docker compatibility patch..."

# Use sed to modify the file
sed -i '10a import os' "$COMM2CENTER_FILE"

# Replace MQTT and InfluxDB configuration lines
sed -i '/^if MIOT_TEST_MODE == 0 :/,/^INFLUX_PORT = / {
    /MQTT_HOST = "106.247.250.251"/c\    MQTT_HOST = os.getenv('\''MQTT_HOST'\'', "106.247.250.251")
    /MQTT_PORT = 31883/c\    MQTT_PORT = int(os.getenv('\''MQTT_PORT'\'', "31883"))
    /MQTT_HOST = "172.17.0.1"/c\    MQTT_HOST = os.getenv('\''MQTT_HOST'\'', "172.17.0.1")
    /MQTT_PORT = 1883$/c\    MQTT_PORT = int(os.getenv('\''MQTT_PORT'\'', "1883"))
}' "$COMM2CENTER_FILE"

# Replace InfluxDB configuration
sed -i 's/^INFLUX_HOST = "106.247.250.251"/INFLUX_HOST = os.getenv('\''INFLUX_HOST'\'', "106.247.250.251")/' "$COMM2CENTER_FILE"
sed -i 's/^INFLUX_PORT = 31886/INFLUX_PORT = int(os.getenv('\''INFLUX_PORT'\'', "31886"))/' "$COMM2CENTER_FILE"

# Add logging
sed -i '/^INFLUX_PORT = /a\\nprint(f"[INFO] MQTT Configuration: {MQTT_HOST}:{MQTT_PORT}")\nprint(f"[INFO] InfluxDB Configuration: {INFLUX_HOST}:{INFLUX_PORT}")' "$COMM2CENTER_FILE"

log_info "Patch applied successfully!"
echo ""
echo "Changes made:"
echo "  - Added 'import os'"
echo "  - Modified MQTT_HOST to use os.getenv('MQTT_HOST', default)"
echo "  - Modified MQTT_PORT to use os.getenv('MQTT_PORT', default)"
echo "  - Modified INFLUX_HOST to use os.getenv('INFLUX_HOST', default)"
echo "  - Modified INFLUX_PORT to use os.getenv('INFLUX_PORT', default)"
echo "  - Added configuration logging"
echo ""
echo "Backup saved to: $BACKUP_FILE"
echo ""
echo "To revert the changes:"
echo "  cp $BACKUP_FILE $COMM2CENTER_FILE"
echo ""
echo "Now rebuild the Docker images:"
echo "  docker-compose build comm2center"
echo "  docker-compose up -d"
