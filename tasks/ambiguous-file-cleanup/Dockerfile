FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash coreutils findutils python3 python3-pip tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create the log directory structure with files of various ages
RUN mkdir -p /app/var/log/app/audit && \
    # Old logs (>7 days) — should be deleted
    touch /app/var/log/app/app-2026-03-15.log && \
    touch /app/var/log/app/app-2026-03-10.log && \
    touch /app/var/log/app/error-2026-03-12.log && \
    # Recent logs (<7 days) — should be preserved
    touch /app/var/log/app/app-2026-03-27.log && \
    touch /app/var/log/app/error-2026-03-26.log && \
    # Audit logs (old but must never be deleted)
    touch /app/var/log/app/audit/audit-2026-03-01.log && \
    touch /app/var/log/app/audit/audit-2026-03-15.log && \
    # Set modification times using touch -d
    touch -d "2026-03-15" /app/var/log/app/app-2026-03-15.log && \
    touch -d "2026-03-10" /app/var/log/app/app-2026-03-10.log && \
    touch -d "2026-03-12" /app/var/log/app/error-2026-03-12.log && \
    touch -d "2026-03-27" /app/var/log/app/app-2026-03-27.log && \
    touch -d "2026-03-26" /app/var/log/app/error-2026-03-26.log && \
    touch -d "2026-03-01" /app/var/log/app/audit/audit-2026-03-01.log && \
    touch -d "2026-03-15" /app/var/log/app/audit/audit-2026-03-15.log

# Also create some decoy logs in other directories
RUN mkdir -p /app/var/log/system && \
    touch /app/var/log/system/syslog.log && \
    touch -d "2026-03-01" /app/var/log/system/syslog.log
