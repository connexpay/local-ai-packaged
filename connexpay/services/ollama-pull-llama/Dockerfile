FROM ollama/ollama:latest

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
    update-ca-certificates

# Create a script to verify certificate
RUN echo '#!/bin/bash' > /verify-ssl.sh && \
    echo 'echo "Verifying SSL connection..."' >> /verify-ssl.sh && \
    echo 'curl -v https://deno.land' >> /verify-ssl.sh && \
    chmod +x /verify-ssl.sh