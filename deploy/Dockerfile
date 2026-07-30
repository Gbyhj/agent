# Multi-stage build — Alpine (~50MB vs Slim ~150MB)
FROM python:3.12-alpine AS builder

WORKDIR /build
RUN apk add --no-cache gcc musl-dev curl

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ── Runtime ──
FROM python:3.12-alpine

WORKDIR /app

# Runtime deps (minimal)
RUN apk add --no-cache curl git ripgrep

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy app code
COPY . .

# Non-root user
RUN adduser -D -s /bin/sh agent && chown -R agent:agent /app
USER agent

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

EXPOSE 5000

CMD ["python", "server.py"]
