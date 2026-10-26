# Stage 1: Build Frontend Static Bundle
FROM node:20-slim AS frontend-builder
WORKDIR /app/frontend
RUN npm install -g pnpm
COPY frontend/package.json frontend/pnpm-lock.yaml* ./
RUN pnpm install
COPY frontend/ ./
RUN pnpm run build

# Stage 2: Production Python Backend with Headless Chromium
FROM python:3.11-slim-bookworm
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PORT=7001

# Install system curl and certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Install Playwright Chromium and needed OS libraries
RUN playwright install --with-deps chromium

# Copy backend source code
COPY backend/ ./backend/

# Copy built frontend assets from stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

WORKDIR /app/backend

EXPOSE 7001

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-7001}"]
