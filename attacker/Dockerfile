FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tcpdump \
    dnsutils \
    net-tools \
    iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install Python packages
RUN pip install --no-cache-dir \
    scapy \
    dnspython \
    requests

# Create app directory
WORKDIR /app

# Copy attack scripts (these will be mounted, but copy for backup)
# COPY poison.py /app/
# COPY detector.py /app/

# Keep container running
CMD ["tail", "-f", "/dev/null"]
