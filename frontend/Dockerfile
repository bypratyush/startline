# StartLine web app: React (Vite) built with Node, served by unprivileged nginx.
#   docker build -t startline-frontend:local ./frontend

# ---- stage 1: build the static bundle ---------------------------------------
FROM node:22-alpine AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npm run build

# ---- stage 2: only the built files + nginx (no node, no node_modules) --------
FROM nginxinc/nginx-unprivileged:1.29-alpine
# Pick up Alpine security fixes that landed after the base image was built.
USER root
RUN apk upgrade --no-cache
# The nginx entrypoint runs envsubst on /etc/nginx/templates/*.template at start,
# so the backend address is a runtime setting (BACKEND_URL).
ENV BACKEND_URL=http://backend:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 8080
USER 101
