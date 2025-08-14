FROM ghcr.io/open-webui/open-webui:main

# Install necessary tools
RUN apt-get update && \
    apt-get install -y \
    ca-certificates \
    curl \
    openssl \
    wget

# Copy your corporate certificate
COPY ZscalerRootCertificate.crt /usr/local/share/ca-certificates/

# Add the certificate and update the certificate store
RUN cp /usr/local/share/ca-certificates/ZscalerRootCertificate.crt /etc/ssl/certs/ && \
    # Revert to HTTPS repositories
    sed -i 's/http:/https:/g' /etc/apt/sources.list.d/* /etc/apt/sources.list || true && \
    update-ca-certificates

# Create a script to verify certificate
RUN echo '#!/bin/bash' > /verify-ssl.sh && \
    echo 'echo "Verifying SSL connection..."' >> /verify-ssl.sh && \
    echo 'curl -v https://deno.land' >> /verify-ssl.sh && \
    chmod +x /verify-ssl.sh

# IMPORTANT: Python SSL fix
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# For Python requests library specifically
RUN python -m pip install --upgrade pip certifi