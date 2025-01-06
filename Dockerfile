# Use Ubuntu 24.04 as base image
FROM ubuntu:24.04

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    DOCKER_COMPOSE_VERSION=v2.24.5

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    git \
    docker.io \
    apache2-utils \
    awscli \
    gnupg \
    lsb-release \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Docker Compose
RUN curl -L "https://github.com/docker/compose/releases/download/${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose && \
    chmod +x /usr/local/bin/docker-compose

# Create directory structure
RUN mkdir -p /app/nginx/{certs,conf.d} \
    /app/cloudflared \
    /app/fail2ban/{data,jail.d} \
    /app/vw-data \
    /app/letsencrypt

# Set working directory
WORKDIR /app

# Copy configuration files
COPY docker-compose.yml .
COPY docker-compose.fail2ban.yml .
COPY nginx/conf.d/reverse-proxy.conf nginx/conf.d/
COPY cloudflared/config.yml cloudflared/
COPY fail2ban/jail.d/custom.conf fail2ban/jail.d/
COPY .env .

# Create networks
RUN docker network create traefik_network || true

# Set up health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/health || exit 1

# Copy and set up entrypoint script
COPY scripts/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports
EXPOSE 80 443 8888 3000 8889

ENTRYPOINT ["/entrypoint.sh"] 