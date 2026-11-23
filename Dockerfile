# PocketAI — one service: Flask serves the API and the built frontend.
# Stage 1: build the Vite frontend.
FROM node:22-slim AS web
WORKDIR /web
COPY package.json package-lock.json .npmrc ./
RUN npm ci
COPY index.html vite.config.js ./
COPY src ./src
RUN npm run build

# Stage 2: the Python server.
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY server ./server
COPY tools ./tools
COPY config_manager.py agent.py ./
COPY --from=web /web/dist ./dist
# $PORT is set by Render; gunicorn serves the Flask app in server/.
CMD gunicorn --chdir server app:app --bind 0.0.0.0:$PORT --worker-class gthread --workers 1 --threads 4 --timeout 300
