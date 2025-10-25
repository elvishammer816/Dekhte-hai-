# Use a slim Python 3.12 base image (Debian-based for better compatibility)
FROM python:3.12-slim-bookworm

# Set the working directory
WORKDIR /app

# Install system dependencies first (optimized for download/upload performance)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    make \
    libffi-dev \
    ffmpeg \
    aria2 \
    wget \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Bento4 (manually install just mp4decrypt)
RUN wget -q https://github.com/axiomatic-systems/Bento4/archive/refs/tags/v1.6.0-639.zip \
    && unzip v1.6.0-639.zip \
    && cd Bento4-1.6.0-639 \
    && mkdir cmakebuild \
    && cd cmakebuild \
    && cmake -DCMAKE_BUILD_TYPE=Release .. \
    && make -j$(nproc --all) mp4decrypt \
    && cp mp4decrypt /usr/local/bin/ \
    && cd ../.. \
    && rm -rf Bento4-1.6.0-639 v1.6.0-639.zip

# Copy requirements file first to leverage Docker cache
COPY thanosbots.txt .

# Install Python dependencies with optimized flags
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --upgrade -r thanosbots.txt \
    && pip install --no-cache-dir --upgrade "yt-dlp[default]"

# Copy the rest of the application
COPY . .

# Optimize aria2 configuration for Render's network
RUN mkdir -p /etc/aria2 \
    && echo "disable-ipv6=true\n" \
         "file-allocation=falloc\n" \
         "optimize-concurrent-downloads=true\n" \
         "max-concurrent-downloads=10\n" \
         "max-connection-per-server=16\n" \
         "split=16\n" \
         "min-split-size=1M\n" \
         "continue=true\n" \
         "check-integrity=true" > /etc/aria2/aria2.conf

# Use gunicorn with reduced workers to save memory
CMD gunicorn --bind 0.0.0.0:${PORT:-8000} \
    --workers 1 \
    --threads 2 \
    --timeout 120 \
    app:app & \
    aria2c --enable-rpc --rpc-listen-all --daemon=true && \
    python3 main.py

