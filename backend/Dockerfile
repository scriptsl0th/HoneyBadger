# HoneyBadger backend: SSH honeypot + intake API/WebSocket in one asyncio process.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so source edits do not invalidate the install layer.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .

# Unprivileged runtime user; the honeypot only binds high ports (8022, 8090).
# The quarantine directory exists up front so payload capture can be enabled
# without a root-owned path (HB_CAPTURE_PAYLOADS=false by default).
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin hb \
    && mkdir -p /opt/hb-quarantine \
    && chown -R hb:hb /opt/hb-quarantine

USER hb

# SSH honeypot, HTTP honeypot (reserved), metrics (reserved), API + WebSocket.
EXPOSE 8022 8081 8000 8090

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8090/health', timeout=2).status == 200 else 1)"

CMD ["python", "main.py"]
