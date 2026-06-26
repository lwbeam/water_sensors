FROM debian:bookworm-slim

# Install Python 3, pip, and ping
RUN apt-get update && \
  apt-get install -y --no-install-recommends python3 python3-pip iputils-ping && \
  rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
RUN pip3 install --no-cache-dir --break-system-packages aiohttp xmltodict

# Copy application and config files
COPY water_sensors.py .
COPY config.json .
COPY smtp.json .
COPY push.json .
COPY ifttt.json .
COPY siren.json .

CMD ["python3", "-u", "water_sensors.py"]
