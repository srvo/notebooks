# Secure Infrastructure Setup

This repository contains a secure Docker-based infrastructure setup with Nginx reverse proxy, Cloudflare Tunnel integration, and various security measures.

## Services

- **Jupyter Notebook**: Data science environment
- **Dagster**: Data pipeline orchestration
- **SearXNG**: Privacy-focused search engine
- **Nginx**: Reverse proxy with SSL termination
- **Cloudflared**: Secure tunnel for external access
- **Fail2ban**: Intrusion prevention system

## Security Features

### Network Security
- SSL/TLS termination with strong cipher configuration
- Cloudflare Tunnel for secure external access
- Rate limiting on all endpoints
- Fail2ban for intrusion prevention
- HTTP to HTTPS redirection

### Access Control
- Basic authentication for sensitive endpoints
- Resource limits on all containers
- Automatic container health checks
- Secure headers configuration

### Monitoring & Logging
- AWS CloudWatch logging integration
- Health check endpoints
- Container resource monitoring

## Configuration Files

### Docker Compose
- `docker-compose.yml`: Main service configuration
- `docker-compose.fail2ban.yml`: Fail2ban service configuration

### Nginx
- `nginx/conf.d/reverse-proxy.conf`: Reverse proxy configuration
- `nginx/.htpasswd`: Basic authentication credentials
- `nginx/certs/`: SSL certificates directory

### Cloudflare
- `cloudflared/config.yml`: Tunnel configuration
- `cloudflared/credentials.json`: Tunnel credentials

### Fail2ban
- `fail2ban/jail.d/custom.conf`: Ban rules and configuration

## Setup Instructions

1. **Prerequisites**
   ```bash
   # Install required packages
   apt update
   apt install -y docker.io docker-compose nginx apache2-utils
   ```

2. **SSL Certificates**
   - Place your SSL certificates in `nginx/certs/`:
     - `fullchain.pem`
     - `privkey.pem`

3. **Basic Authentication**
   ```bash
   # Generate .htpasswd file
   htpasswd -c ./nginx/.htpasswd your-username
   ```

4. **Environment Variables**
   ```bash
   # Copy example .env file
   cp .env.example .env
   # Edit with your configurations
   nano .env
   ```

5. **Cloudflare Setup**
   - Create a Cloudflare Tunnel
   - Update `cloudflared/config.yml` with your tunnel ID
   - Place tunnel credentials in `cloudflared/credentials.json`

6. **Start Services**
   ```bash
   # Start all services
   docker-compose up -d
   # Start fail2ban
   docker-compose -f docker-compose.fail2ban.yml up -d
   ```

## Security Best Practices

1. **Access Control**
   - Use strong passwords for basic authentication
   - Regularly rotate credentials
   - Limit access to sensitive endpoints

2. **Monitoring**
   - Regularly check fail2ban logs
   - Monitor container resource usage
   - Review access logs

3. **Maintenance**
   - Keep containers updated
   - Regularly rotate SSL certificates
   - Update security configurations

4. **Resource Management**
   - Monitor container resource limits
   - Adjust limits based on usage
   - Enable automatic container restarts

## Rate Limiting

The Nginx configuration includes rate limiting:
- 10 requests per second per IP
- Burst of 5 requests allowed
- Applies to all protected endpoints

## Fail2ban Configuration

Current settings:
- 3 retry attempts within 30 minutes
- 3-day ban time
- Exponential increase for repeat offenders
- Monitors SSH and web traffic

## Environment Variables

Required environment variables:
```env
# Jupyter
JUPYTER_TOKEN=your-secure-token

# Dagster
DAGSTER_HOME=/opt/dagster/dagster_home

# SearXNG
SEARXNG_BASE_URL=https://searxng.yourdomain.com

# Cloudflare
TUNNEL_TOKEN=your-cloudflare-tunnel-token

# AWS (for logging)
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
AWS_DEFAULT_REGION=your-region
```

## Resource Limits

Container resource limits:
- Jupyter: 1 CPU, 512MB RAM
- Dagster: 1 CPU, 512MB RAM
- Nginx: 1 CPU, 512MB RAM

## Troubleshooting

1. **Check Service Status**
   ```bash
   docker-compose ps
   ```

2. **View Logs**
   ```bash
   docker-compose logs [service_name]
   ```

3. **Check Fail2ban Status**
   ```bash
   docker exec fail2ban fail2ban-client status
   ```

4. **Test Nginx Configuration**
   ```bash
   docker exec reverse_proxy nginx -t
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## License

MIT License 