FROM n8nio/n8n:latest
USER root

# Temporarily disable SSL verification for apk
RUN sed -i 's/https/http/g' /etc/apk/repositories

# Install necessary tools
RUN apk update && \
    apk add --no-cache \
    ca-certificates \
    curl \
    openssl \
    wget

# Copy your corporate certificate
COPY ZscalerRootCertificate.crt /usr/local/share/ca-certificates/ZscalerRootCertificate.crt

# Add the certificate and update the certificate store
RUN cp /usr/local/share/ca-certificates/ZscalerRootCertificate.crt /etc/ssl/certs/ && \
    # Revert to HTTPS repositories
    sed -i 's/http/https/g' /etc/apk/repositories && \
    update-ca-certificates

# Create a script to verify certificate
RUN echo '#!/bin/sh' > /verify-ssl.sh && \
    echo 'echo "Verifying SSL connection..."' >> /verify-ssl.sh && \
    echo 'curl -v https://deno.land' >> /verify-ssl.sh && \
    chmod +x /verify-ssl.sh

# Add Node.js SSL environment variables
ENV NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt
ENV NODE_OPTIONS=--use-openssl-ca
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_DIR=/etc/ssl/certs

USER node