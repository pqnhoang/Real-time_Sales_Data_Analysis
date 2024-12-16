FROM python:3.11-slim-buster

WORKDIR /opt/spark/app

RUN apt-get update && \
apt-get install -y --no-install-recommends \
gcc && \
apt-get clean && \
rm -rf /var/lib/apt/lists/*

# Project initialization
RUN pip install uv
COPY requirements.txt /opt/spark/app/requirements.txt
RUN uv pip install --no-cache-dir --system -r /opt/spark/app/requirements.txt

# Copy code and workspace to /opt/dagster/app
COPY src /opt/spark/app/src
COPY pyproject.toml /opt/spark/app//app/pyproject.toml
RUN pip install --no-cache-dir -e .