#!/bin/bash
set -e

# Function to wait for a service to be healthy
wait_for_health() {
    local service=$1
    local max_attempts=30
    local attempt=1

    echo "Waiting for $service to be healthy..."
    while [ $attempt -le $max_attempts ]; do
        if docker-compose ps $service | grep -q "healthy"; then
            echo "$service is healthy"
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service not healthy yet..."
        sleep 10
        attempt=$((attempt + 1))
    done
    echo "$service failed to become healthy after $max_attempts attempts"
    return 1
}

# Start Docker service if not running
if ! systemctl is-active --quiet docker; then
    echo "Starting Docker service..."
    systemctl start docker
fi

# Wait for Docker to be ready
while ! docker info >/dev/null 2>&1; do
    echo "Waiting for Docker to start..."
    sleep 1
done

# Create required directories if they don't exist
mkdir -p /app/nginx/certs
mkdir -p /app/letsencrypt
mkdir -p /app/vw-data

# Set correct permissions
chown -R 1000:1000 /app/nginx
chown -R 1000:1000 /app/letsencrypt
chown -R 1000:1000 /app/vw-data

# Start core services
echo "Starting core services..."
docker-compose up -d traefik
wait_for_health traefik

# Start application services
echo "Starting application services..."
docker-compose up -d dagster searxng vaultwarden whoami
wait_for_health dagster
wait_for_health searxng
wait_for_health vaultwarden
wait_for_health whoami

# Start Cloudflare tunnel
echo "Starting Cloudflare tunnel..."
docker-compose up -d cloudflared
wait_for_health cloudflared

# Start backup and monitoring services
echo "Starting backup and monitoring services..."
docker-compose up -d s3_client backup
wait_for_health s3_client
wait_for_health backup

# Start fail2ban
echo "Starting fail2ban..."
docker-compose -f docker-compose.fail2ban.yml up -d

echo "All services started successfully!"

# Keep container running and monitor service health
while true; do
    # Check if all services are running
    if ! docker-compose ps | grep -q "Exit"; then
        echo "All services running: $(date)"
    else
        echo "Service failure detected: $(date)"
        # List failed services
        docker-compose ps | grep "Exit"
        # Attempt to restart failed services
        docker-compose up -d
    fi
    sleep 60
done 