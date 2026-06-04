FROM python:3.12-slim

WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    libxml2 libxslt1.1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY sitespider ./sitespider
RUN pip install --no-cache-dir -e ".[browser,spelling,pdf]" \
    && playwright install chromium --with-deps || true

ENV SITESPIDER_HOST=0.0.0.0
ENV SITESPIDER_PORT=8765
EXPOSE 8765

VOLUME ["/app/reports", "/app/.sitespider"]

CMD ["sitespider", "--ui", "--host", "0.0.0.0", "--port", "8765"]
