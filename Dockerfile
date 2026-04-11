# Multi-stage build: Build frontend first
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm install

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build

# Final stage: Python backend
FROM python:3.11-slim

WORKDIR /app

# Accept version as build argument (optional)
ARG APP_VERSION
ENV APP_VERSION=${APP_VERSION}
ENV PORT=8192

# Install curl for HEALTHCHECK
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from builder stage (React Scripts creates 'build', not 'dist')
COPY --from=frontend-builder /app/frontend/build/ ./frontend/dist/

# Expose port (keep in sync with PORT)
EXPOSE 8192

# Liveness: lightweight /health only (see backend.app.health). If you change PORT at
# runtime, override the healthcheck in compose/orchestrator to match.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
  CMD sh -c 'curl -fsS "http://127.0.0.1:$${PORT}/health" >/dev/null || exit 1'

# Run the application
CMD ["python", "-m", "backend.app"]

