FROM python:3.12-slim

ARG NETWEATHER_VCS_REF=unknown
LABEL org.opencontainers.image.title="NetWeather Web" \
      org.opencontainers.image.revision="$NETWEATHER_VCS_REF"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends traceroute ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 10001 netweather \
    && useradd --system --uid 10001 --gid 10001 --home-dir /nonexistent --shell /usr/sbin/nologin netweather

COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY backend/app /app/app
COPY frontend /app/frontend

RUN install -d -o 10001 -g 10001 -m 0750 /data \
    && chown -R 10001:10001 /app

ENV NETWEATHER_DB=/data/netweather.db \
    FRONTEND_DIR=/app/frontend

USER 10001:10001

EXPOSE 8000

CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1","--no-access-log"]
