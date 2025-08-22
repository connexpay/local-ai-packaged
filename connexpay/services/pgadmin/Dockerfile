FROM dpage/pgadmin4:latest

# pgAdmin uses Alpine Linux, so we need to use apk instead of apt-get
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

# Switch back to pgadmin user
USER pgadmin