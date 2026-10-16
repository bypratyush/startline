# StartLine API: FastAPI + Alembic + seed catalogue.
#   docker build -t startline-backend:local ./backend

# Alpine, not Debian slim: python:3.13-slim carried 44 HIGH CVEs in util-linux
# with no Debian fix yet, which a strict Trivy gate (any HIGH/CRITICAL fails)
# would block. Every dependency ships a musllinux wheel, so nothing is compiled.

# ---- stage 1: install dependencies into a virtualenv -------------------------
FROM python:3.13-alpine AS deps
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
COPY requirements.txt .
# pip is only needed to build the venv; its vendored packages have carried HIGH
# CVEs before, so it is removed rather than shipped.
RUN pip install -r requirements.txt && pip uninstall -y pip

# ---- stage 2: runtime, no build tools, not root ------------------------------
FROM python:3.13-alpine
ARG APP_VERSION=dev
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_VERSION=${APP_VERSION}
RUN apk upgrade --no-cache \
 && /usr/local/bin/python3 -m pip uninstall -y --root-user-action=ignore pip \
 && addgroup -S -g 10001 app \
 && adduser -S -D -H -u 10001 -G app -s /sbin/nologin app
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app
COPY --chmod=755 entrypoint.sh ./
USER 10001
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1
ENTRYPOINT ["./entrypoint.sh"]
