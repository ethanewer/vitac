FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash coreutils findutils python3 python3-pip tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Service A logs
RUN mkdir -p /app/logs
RUN printf '[2026-03-28 09:00:01] ERROR: Connection refused on port 5432\n[2026-03-28 09:00:02] ERROR: Failed to connect to database\n[2026-03-28 09:00:03] WARN: Retrying connection...\n[2026-03-28 09:00:04] ERROR: Connection refused on port 5432\n' > /app/logs/service-a.log

# Service B logs
RUN printf '[2026-03-28 09:00:01] WARN: Disk space critically low: /app/cache/ using 95%%\n[2026-03-28 09:00:02] ERROR: Cannot write to cache\n[2026-03-28 09:00:03] INFO: Cache write failed, falling back to memory\n' > /app/logs/service-b.log

# Service C logs
RUN printf '[2026-03-28 09:00:01] ERROR: SSL certificate expired: /app/certs/active/server.pem\n[2026-03-28 09:00:02] ERROR: TLS handshake failed\n[2026-03-28 09:00:03] WARN: Connections being rejected\n' > /app/logs/service-c.log

# DB config
RUN mkdir -p /app/config
RUN printf 'host=db.internal\nport=5432\nname=mydb\n' > /app/config/db.conf

# Cache files (old ones have marker file to indicate age)
RUN mkdir -p /app/cache
RUN echo "temp data 1" > /app/cache/old1.tmp && \
    echo "temp data 2" > /app/cache/old2.tmp && \
    echo "temp data 3" > /app/cache/old3.tmp && \
    echo "recent data" > /app/cache/recent.tmp && \
    echo "important" > /app/cache/important.dat && \
    touch -d "2026-03-20" /app/cache/old1.tmp && \
    touch -d "2026-03-21" /app/cache/old2.tmp && \
    touch -d "2026-03-22" /app/cache/old3.tmp

# Certificates
RUN mkdir -p /app/certs/active /app/certs/renewed
RUN echo "-----EXPIRED CERT-----" > /app/certs/active/server.pem
RUN echo "-----RENEWED CERT 2026-----" > /app/certs/renewed/server.pem
