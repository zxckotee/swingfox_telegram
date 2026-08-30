FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY api ./api
COPY config ./config
COPY handlers ./handlers
COPY state ./state
COPY telegram ./telegram
COPY main.py .

# Non-root user + writable session dir (named volume mounts at /app/data)
RUN useradd -m -u 10001 botuser \
    && mkdir -p /app/data /home/botuser/.local/share/swingfox \
    && chown -R botuser:botuser /app /home/botuser
USER botuser

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD pgrep -f "python main.py" || exit 1

CMD ["python", "main.py"]
