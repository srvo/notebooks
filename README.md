# Secure Infrastructure Setup

This repository contains a secure Docker-based infrastructure setup with Traefik reverse proxy, Cloudflare Tunnel integration, and various security measures.

## Environment Variables

### GitHub Actions Secrets
These variables need to be set in your GitHub repository secrets:
```bash
# SSH Configuration
SSH_PRIVATE_KEY       # Private SSH key for deployment
SSH_KNOWN_HOSTS       # Output from ssh-keyscan -H 5.78.132.88
SSH_USER=srvo        # Deployment user
SSH_HOST=5.78.132.88 # Server hostname
```

### Service Configuration
```bash
# Cloudflare Configuration
CF_TUNNEL_TOKEN      # Cloudflare tunnel token
CF_ZONE_ID          # Cloudflare zone ID for ec1c.com
CF_API_TOKEN        # Cloudflare API token with DNS edit permissions

# AWS Configuration
AWS_ACCESS_KEY_ID    # AWS access key for S3 and logging
AWS_SECRET_ACCESS_KEY# AWS secret key
AWS_DEFAULT_REGION   # AWS region (e.g., us-east-1)
S3_BACKUP_BUCKET     # Bucket for backups
S3_DATA_BUCKET       # Bucket for data storage
```

### Application Configuration
```bash
# Jupyter Configuration
JUPYTER_TOKEN        # Secure token for Jupyter access
JUPYTER_MEMORY_LIMIT=0  # No memory limit (use available server memory)
JUPYTER_CPU_LIMIT=0    # No CPU limit (use all available cores)
JUPYTER_ENABLE_LAB=yes # Use JupyterLab interface
JUPYTER_ALLOW_ROOT=yes # Allow root access for system operations

# Dagster Configuration
DAGSTER_HOME=/opt/dagster/dagster_home
DAGSTER_MEMORY_LIMIT=0  # No memory limit
DAGSTER_CPU_LIMIT=0     # No CPU limit
DAGSTER_MAX_WORKERS=-1  # Use all available cores for workers
DAGSTER_COMPUTE_LOG_LEVEL=DEBUG  # Detailed compute logs

# SearXNG Configuration
SEARXNG_BASE_URL=https://app.ec1c.com/searxng

# Vaultwarden Configuration
VW_ADMIN_TOKEN       # Admin token for Vaultwarden
VW_DOMAIN=https://vw.ec1c.com

# Traefik Configuration
TRAEFIK_ACME_EMAIL=sloane@srvo.org  # Email for Let's Encrypt notifications
```

### Security Configuration
```bash
# Basic Auth Credentials
BASIC_AUTH_USER      # Username for basic auth
BASIC_AUTH_PASS      # Password hash for basic auth
```

### Resource Configuration
```bash
# Compute Resources
COMPUTE_PRIORITY_SERVICES="jupyter,dagster"  # Services with resource priority
ENABLE_COMPUTE_LIMITS=false  # Disable container resource limits
ENABLE_SWAP=true  # Enable swap for memory-intensive operations

# Monitoring
LOG_LEVEL=info       # Log level for all services
RETENTION_DAYS=30    # Log retention period
```

## Services

- **Jupyter Notebook**: Data science environment with unlimited compute resources
- **Dagster**: Data pipeline orchestration with full server capability
- **SearXNG**: Privacy-focused search engine
- **Traefik**: Reverse proxy with automatic SSL
- **Cloudflared**: Secure tunnel for external access
- **Vaultwarden**: Password manager
- **Fail2ban**: Intrusion prevention system

## Resource Management

### Compute Priority Services
Jupyter and Dagster are configured for maximum performance:
- No memory limits
- Access to all CPU cores
- Unlimited locked memory
- High file descriptor limits
- Root access for system operations

### Other Services
- Standard resource limits
- Automatic health checks
- Graceful restart policies

## Security Features

### Network Security
- SSL/TLS termination with strong cipher configuration
- Cloudflare Tunnel for secure external access
- Rate limiting on all endpoints
- Fail2ban for intrusion prevention
- HTTP to HTTPS redirection

### Access Control
- Basic authentication for sensitive endpoints
- Resource limits on non-priority services
- Automatic container health checks
- Secure headers configuration

### Monitoring & Logging
- AWS CloudWatch logging integration
- Health check endpoints
- Container resource monitoring
- Configurable log retention

## Deployment

1. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configurations
```

2. Add GitHub secrets for CI/CD:
- Navigate to Settings > Secrets and variables > Actions
- Add all required secrets from the Environment Variables section

3. Deploy using GitHub Actions:
- Push to main branch
- GitHub Actions will validate, test, and deploy

4. Verify deployment:
```bash
docker-compose ps
docker-compose logs
```

## Maintenance

### Updating Services
```bash
# Pull latest images
docker-compose pull

# Restart services
docker-compose up -d
```

### Checking Resources
```bash
# View resource usage
docker stats

# Check service health
docker-compose ps
```

### Log Management
```bash
# View service logs
docker-compose logs [service_name]

# Check fail2ban status
docker-compose exec fail2ban fail2ban-client status
```

## License

MIT License 
