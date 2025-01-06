I'll help edit the README.md to reflect our learnings about simplification and the current state of the infrastructure. I'll make it more concise and focused on the key aspects:

```yaml:.github/workflows/ci-cd.yml
    - name: Edit README
      uses: nick-fields/retry@v3.0.0
      with:
        timeout_minutes: 5
        max_attempts: 2
        command: |
          cat > README.md << 'EOL'
# Secure Infrastructure Setup

This repository contains a secure Docker-based infrastructure setup with Traefik reverse proxy and various security measures.

## Core Services

- **Jupyter Notebook**: Data science environment
- **Dagster**: Data pipeline orchestration
- **SearxNG**: Privacy-focused search engine
- **Traefik**: Reverse proxy with automatic SSL
- **Cloudflared**: Secure tunnel for external access
- **Vaultwarden**: Password manager
- **Fail2ban**: Intrusion prevention system

notebooks/
├── data/               # Data directory
│   └── research.db     # DuckDB database
├── jupyter/           
│   ├── __init__.py
│   ├── setup_db.py    # Database setup
│   ├── db.py          # Database operations
│   └── search.py      # Search utilities
├── dagster/
│   ├── workspace.yaml
│   └── dagster.yaml
├── docker-compose.yml
├── requirements.txt
├── .env
└── .env.example


## Environment Variables

### Required Secrets
```bash
# SSH Configuration
SSH_PRIVATE_KEY       # Private SSH key for deployment
SSH_KNOWN_HOSTS      # SSH known hosts
SSH_USER             # Deployment user
SSH_HOST             # Server hostname

# Service Configuration
CF_TUNNEL_TOKEN      # Cloudflare tunnel token
HETZNER_S3_ACCESS_KEY    # S3 access key
HETZNER_S3_SECRET_KEY    # S3 secret key
AWS_ENDPOINT_URL     # S3 endpoint URL
S3_BACKUP_BUCKET     # Bucket for backups
S3_DATA_BUCKET       # Bucket for data storage
```

### Service Configuration
```bash
# Jupyter Configuration
JUPYTER_TOKEN        # Secure token for Jupyter access
JUPYTER_ENABLE_LAB=yes
JUPYTER_ALLOW_ROOT=yes

# Dagster Configuration
DAGSTER_HOME=/opt/dagster/dagster_home
DAGSTER_PG_USERNAME=dagster
DAGSTER_PG_PASSWORD=dagster
DAGSTER_PG_HOST=postgres
DAGSTER_PG_DB=dagster

# SearxNG Configuration
SEARXNG_BASE_URL=https://app.ec1c.com/searxng
```

## Architecture

- Uses Docker Compose for service orchestration
- Default Docker networking for simplicity
- Traefik for automatic SSL and routing
- Cloudflare Tunnel for secure external access
- S3 for backups and data storage

## Deployment

1. Clone the repository:
```bash
git clone https://github.com/yourusername/infrastructure.git
cd infrastructure
```

2. Create environment files:
```bash
cp .env.example .env
# Edit .env with your configurations
```

3. Deploy using GitHub Actions:
- Push to main branch
- GitHub Actions will validate, test, and deploy

4. Verify deployment:
```bash
docker compose ps
docker compose logs
```

## Maintenance

### Service Management
```bash
# Pull latest images
docker compose pull

# Restart services
docker compose up -d

# View logs
docker compose logs [service]

# Check health
docker compose ps
```

### Backups
- Automatic backups to S3
- Daily backup schedule
- Configurable retention period

## Security Features

- SSL/TLS termination with Traefik
- Cloudflare Tunnel for secure access
- Fail2ban for intrusion prevention
- Regular security updates
- Health monitoring
- Automated backups

## License

MIT License
EOL
        shell: bash
        on_retry_command: |
          echo "Retry attempt - cleaning up..."
          sleep 5
```
Key changes made to the README:
1. Simplified service descriptions
2. Focused on essential environment variables
3. Removed redundant network configuration
4. Streamlined deployment steps
5. Added clear maintenance instructions
6. Organized security features
7. Removed unnecessary complexity
8. Added clear section structure

Let's commit these changes:

```bash
git add README.md
git commit -m "docs: simplify README and focus on essential information"
git push origin main
```


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

## Parallel Processing with Joblib

The research workflow (wants to) use [Joblib](https://joblib.readthedocs.io/) for efficient parallel processing and caching:

### Key Features
- **Transparent Parallelization**: Automatically parallelizes company research tasks
- **Memory Caching**: Caches API responses and research results to avoid recomputation
- **Robust Error Handling**: Fails fast without retries for better debugging
- **No Dependencies**: Uses only Python standard library

### Implementation
```python
from joblib import Memory, Parallel, delayed

# Configure caching
memory = Memory('cache_dir', verbose=0)

@memory.cache
def research_single_company(company):
    """Research a single company with automatic caching"""
    return {
        'context': generate_company_context(company),
        'analysis': analyze_company_data(company),
        'trends': analyze_positive_trends(company)
    }

def bulk_research_companies(companies, n_jobs=3):
    """Process multiple companies in parallel"""
    return Parallel(n_jobs=n_jobs)(
        delayed(research_single_company)(company) 
        for company in companies
    )
```

### Benefits
- Faster processing through parallel execution
- Automatic caching of expensive operations
- Simplified error handling and debugging
- Easy recovery from failures

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

# Infrastructure Management

This repository manages the infrastructure deployment for various services using Docker Compose and Traefik.

## Current State

The infrastructure is deployed on a Hetzner server (5.78.132.88) with the following components:

- **Reverse Proxy**: Traefik with automatic SSL certificate management
- **Storage**: Hetzner Object Storage (S3-compatible) for data and backups
- **Compute Services**:
  - Jupyter Lab for interactive development
  - Dagster for data orchestration
- **Security**:
  - Basic authentication for service access
  - Fail2ban for intrusion prevention
  - Cloudflare for DNS and DDoS protection

## Configuration

The infrastructure uses environment variables for configuration, stored in `.env` files. For security:

- Sensitive credentials are stored in GitHub Secrets
- Local development uses `.env` files (not committed)
- Production deployment uses environment variables

### Required Secrets

The following secrets need to be configured in GitHub:

- `SSH_PRIVATE_KEY`: For deployment access
- `SSH_KNOWN_HOSTS`: Server fingerprint
- `HETZNER_S3_ACCESS_KEY`: Object storage access
- `HETZNER_S3_SECRET_KEY`: Object storage secret
- `CF_API_TOKEN`: Cloudflare API access
- Various API keys for services

### Service Configuration

Key services are configured with:

- **Jupyter**: Full resource access, JupyterLab interface
- **Dagster**: Unlimited workers, debug logging
- **Traefik**: Automatic SSL via Let's Encrypt
- **Object Storage**: S3-compatible buckets for data and backups

## Development

For local development:

1. Copy `.env.example` to `.env`
2. Fill in required credentials
3. Run `docker compose up -d`

## Deployment

Deployment is handled via GitHub Actions:

1. Push to main triggers deployment
2. GitHub Actions uses SSH for deployment
3. Services are updated via Docker Compose
4. Logs are retained for 30 days

## Analysis Flows

### Ethical Analysis Flow
Performs comprehensive ethical analysis of companies using AI:

- **Input**: Company name/symbol
- **Process**:
  1. Context Generation: Creates initial company context
  2. Query Generation: Builds targeted search queries for:
     - Financial/Legal risks
     - Ethical/Social concerns
     - Environmental/Safety issues
  3. Multi-source Research: Executes parallel searches
  4. Data Extraction: Processes and structures findings
  5. Analysis Generation: Creates detailed risk assessments
- **Output**: Structured JSON with:
  - Company metadata
  - Risk categorizations
  - Evidence snippets
  - Source citations
- **Performance**:
  - ~13-15 seconds per company
  - ~2500-3000 tokens per analysis
  - Parallel processing capable
  - Auto-batching and rate limiting

### Search Flow
Handles distributed search operations:

- **Input**: Search queries and parameters
- **Process**:
  1. Query Preprocessing
  2. Parallel Search Execution
  3. Result Deduplication
  4. Content Extraction
  5. Structured Data Generation
- **Output**: 
  - Cleaned search results
  - Metadata and statistics
  - Source tracking


