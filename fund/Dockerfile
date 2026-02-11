# ---- Stage 1: Build frontend ----
FROM node:22-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package*.json ./
RUN npm ci
COPY web/frontend/ ./
RUN npm run build

# ---- Stage 2: Python runtime ----
FROM python:3.12-slim
WORKDIR /app

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY boc_scraper/ boc_scraper/
COPY web/ web/
COPY portfolio.json .

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist web/frontend/dist/

# Data volume
VOLUME ["/app/data"]

EXPOSE 8000

ENV BOC_DB_PATH=/app/data/boc_nav.sqlite3
ENV BOC_PORTFOLIO_PATH=/app/portfolio.json
ENV BOC_FRONTEND_DIST=/app/web/frontend/dist

CMD ["uvicorn", "web.backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
