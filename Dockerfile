# Use the repository's source instead of cloning a different upstream revision.
FROM python:3.10-slim

ENV PIP_NO_CACHE_DIR 1

# Installing Required Packages
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    bash \
    curl \
    libffi-dev \
    libjpeg-dev \
    libwebp-dev \
    libpq-dev \
    libxml2-dev \
    libxslt1-dev \
    gcc \
    libsqlite3-dev \
    ffmpeg \
    libssl-dev \
    libopus0 \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# Pypi package Repo upgrade
RUN pip3 install --upgrade pip setuptools

WORKDIR /app
COPY requirements.txt ./

ENV PATH="/home/bot/bin:$PATH"

# Install requirements
RUN pip3 install -U -r requirements.txt

COPY . .

# Starting Worker
CMD ["python3","-m","FallenRobot"]
