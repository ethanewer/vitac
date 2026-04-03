FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash python3 python3-pip tmux sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy buggy source code
COPY src/ /app/src/

# Make source files readable only by root
RUN chown -R root:root /app/src && chmod 600 /app/src/*.py

# Create log data file
RUN mkdir -p /app/data && cat > /app/data/app.log << 'LOGEOF'
[2026-03-28 10:00:01] INFO: Server started on port 8080
[2026-03-28 10:00:02] INFO: Request /api/users completed in 45ms
[2026-03-28 10:00:03] ERROR: Database connection timeout
[2026-03-28 10:00:04] INFO: Request /api/products completed in 120ms
[2026-03-28 10:00:05] WARN: High memory usage detected
[2026-03-28 10:00:06] ERROR: Failed to write to cache
[2026-03-28 10:00:07] INFO: Request /api/orders completed in 89ms
[2026-03-28 10:00:08] INFO: Health check passed
[2026-03-28 10:00:09] ERROR: Authentication service unreachable
[2026-03-28 10:00:10] INFO: Request /api/stats completed in 200ms
[2026-03-28 10:00:11] INFO: Cleanup job completed
[2026-03-28 10:00:12] ERROR: Rate limit exceeded for client 192.168.1.50
LOGEOF

# run-code wrapper: execute Python files via sudo
RUN printf '#!/bin/bash\nsudo python3 /app/src/"$@" 2>&1\n' > /usr/local/bin/run-code && chmod 755 /usr/local/bin/run-code

# apply-fix wrapper: overwrite a source file from stdin
RUN printf '#!/bin/bash\nsudo tee /app/src/"$1" > /dev/null\n' > /usr/local/bin/apply-fix && chmod 755 /usr/local/bin/apply-fix

# Sudoers: allow python3 and tee on /app/src/ without password
RUN echo 'ALL ALL=(root) NOPASSWD: /usr/bin/python3 /app/src/*, /usr/bin/tee /app/src/*' > /etc/sudoers.d/vitac && chmod 440 /etc/sudoers.d/vitac

# Output directory
RUN mkdir -p /app/output && chmod 777 /app/output
