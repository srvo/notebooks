#!/bin/bash
set -e

# Create test log directory
mkdir -p /app/test-logs || { echo "Failed to create test log directory"; exit 1; }

# Add test function with retry logic
test_service() {
    local service=$1
    local endpoint=$2
    local log_file="/app/test-logs/${service}_test.log"
    local max_attempts=5
    local attempt=1
    local delay=5

    echo "Testing $service at $endpoint..."
    echo "Test started at $(date)" > $log_file
    while [ $attempt -le $max_attempts ]; do
        if curl -f $endpoint >> $log_file 2>&1; then
            echo "$service test passed" | tee -a $log_file
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: $service test failed, retrying in $delay seconds..." | tee -a $log_file
        sleep $delay
        attempt=$((attempt + 1))
        delay=$((delay * 2))
    done
    echo "$service test failed after $max_attempts attempts" | tee -a $log_file
    return 1
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

# Add service tests
test_service "traefik" "http://localhost:8080/ping"
test_service "jupyter" "http://localhost:8888/api/status"
test_service "dagster" "http://localhost:3000/health"
test_service "searxng" "http://localhost:8889/status"
test_service "vaultwarden" "http://localhost:80/alive"
test_service "whoami" "http://localhost:80"

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
mkdir -p /app/nginx/certs || { echo "Failed to create nginx certs directory"; exit 1; }
mkdir -p /app/letsencrypt || { echo "Failed to create letsencrypt directory"; exit 1; }
mkdir -p /app/vw-data || { echo "Failed to create vw-data directory"; exit 1; }

# Set correct permissions
chown -R 1000:1000 /app/nginx || { echo "Failed to set permissions for nginx"; exit 1; }
chown -R 1000:1000 /app/letsencrypt || { echo "Failed to set permissions for letsencrypt"; exit 1; }
chown -R 1000:1000 /app/vw-data || { echo "Failed to set permissions for vw-data"; exit 1; }

# Set correct permissions
chown -R 1000:1000 /app/nginx || { echo "Failed to set permissions for nginx"; exit 1; }
chown -R 1000:1000 /app/letsencrypt || { echo "Failed to set permissions for letsencrypt"; exit 1; }
chown -R 1000:1000 /app/vw-data || { echo "Failed to set permissions for vw-data"; exit 1; }

# Validate required environment variables
required_vars=(
  "JUPYTER_TOKEN"
  "CF_TUNNEL_TOKEN"
  "HETZNER_S3_ACCESS_KEY"
  "HETZNER_S3_SECRET_KEY"
  "S3_DATA_BUCKET"
  "S3_BACKUP_BUCKET"
)

# Validate S3 credentials
if [ -z "${HETZNER_S3_ACCESS_KEY}" ] || [ -z "${HETZNER_S3_SECRET_KEY}" ]; then
  echo "HETZNER_S3_ACCESS_KEY and HETZNER_S3_SECRET_KEY environment variables are required"
  exit 1
fi

for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Environment variable $var is required"
    exit 1
  fi
done

# Function to restart services with error handling
restart_service() {
    local service=$1
    local max_attempts=3
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        echo "Attempt $attempt: Restarting $service..."
        if docker-compose up -d $service; then
            echo "$service restarted successfully"
            return 0
        fi
        echo "Failed to restart $service, retrying in 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    echo "Failed to restart $service after $max_attempts attempts"
    return 1
}

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
