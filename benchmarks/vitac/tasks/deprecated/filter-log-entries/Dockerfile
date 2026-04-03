FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/logs /app/output && \
    printf '%s\n' \
    "2026-03-28 10:00:01 INFO  Application started" \
    "2026-03-28 10:00:02 DEBUG Connecting to database" \
    "2026-03-28 10:00:03 ERROR Failed to connect to database: timeout" \
    "2026-03-28 10:00:04 INFO  Retrying connection" \
    "2026-03-28 10:00:05 ERROR Connection refused by host db.local:5432" \
    "2026-03-28 10:00:06 WARN  Using fallback database" \
    "2026-03-28 10:00:07 INFO  Connected to fallback-db.local" \
    "2026-03-28 10:00:08 DEBUG Loading configuration" \
    "2026-03-28 10:00:09 ERROR Invalid configuration key: max_retries" \
    "2026-03-28 10:00:10 WARN  Deprecated API version detected" \
    "2026-03-28 10:00:11 INFO  Using default configuration" \
    "2026-03-28 10:00:12 INFO  Server listening on port 8080" \
    "2026-03-28 10:00:13 WARN  SSL certificate expires in 7 days" \
    "2026-03-28 10:00:14 DEBUG Health check passed" \
    > /app/logs/application.log
