FROM searxng/searxng:latest

# Copy custom settings.yml
COPY searxng/settings.yml /etc/searxng/settings.yml

# Ensure correct permissions
USER root
RUN chmod 644 /etc/searxng/settings.yml
USER searxng
