FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash python3 python3-pip tmux sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy buggy source code
COPY src/ /app/src/

# Make source files readable only by root
RUN chown -R root:root /app/src && chmod 600 /app/src/*.py

# run-code wrapper: execute Python files via sudo
RUN printf '#!/bin/bash\nsudo python3 /app/src/"$@" 2>&1\n' > /usr/local/bin/run-code && chmod 755 /usr/local/bin/run-code

# apply-fix wrapper: overwrite a source file from stdin
RUN printf '#!/bin/bash\nsudo tee /app/src/"$1" > /dev/null\n' > /usr/local/bin/apply-fix && chmod 755 /usr/local/bin/apply-fix

# Sudoers: allow python3 and tee on /app/src/ without password
RUN echo 'ALL ALL=(root) NOPASSWD: /usr/bin/python3 /app/src/*, /usr/bin/tee /app/src/*' > /etc/sudoers.d/vitac && chmod 440 /etc/sudoers.d/vitac

# Create test data files and a backup for restoration
RUN mkdir -p /app/data/files /app/data/.backup && \
    echo "Report content" > /app/data/files/report_20260315_final.txt && \
    echo "CSV data" > /app/data/files/data_20260320.csv && \
    echo "Log content" > /app/data/files/log_20260328_backup.log && \
    echo "Notes content" > /app/data/files/notes.txt && \
    cp /app/data/files/* /app/data/.backup/

# restore-data wrapper: reset /app/data/files/ to original state
RUN printf '#!/bin/bash\nrm -f /app/data/files/*\ncp /app/data/.backup/* /app/data/files/\necho "Data files restored."\n' > /usr/local/bin/restore-data && chmod 755 /usr/local/bin/restore-data

# Output directory
RUN mkdir -p /app/output && chmod 777 /app/output
