#!/bin/bash
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

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

# Check for required commands
for cmd in docker docker-compose curl wget; do
    if ! command_exists $cmd; then
        echo "Error: $cmd is required but not installed."
        exit 1
    fi
done

# Create required directories
echo "Creating directories..."
mkdir -p letsencrypt
mkdir -p vw-data
mkdir -p fail2ban/data
mkdir -p fail2ban/jail.d

# Check for required files
echo "Checking required files..."
required_files=(".env" "docker-compose.yml" "docker-compose.fail2ban.yml")
for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        echo "Error: Required file $file not found"
        exit 1
    fi
done

# Pull latest images
echo "Pulling latest images..."
docker-compose pull
docker-compose -f docker-compose.fail2ban.yml pull

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
wait_for_health fail2ban

# Verify all services
echo "Verifying services..."
docker-compose ps
docker-compose -f docker-compose.fail2ban.yml ps

echo "Deployment complete! Checking logs..."
docker-compose logs --tail=20

# Print access URLs
echo "
Access URLs:
- Main site: https://ec1c.com
- WWW: https://www.ec1c.com
- Vaultwarden: https://vw.ec1c.com
- Traefik Dashboard: https://traefik.ec1c.com
" 