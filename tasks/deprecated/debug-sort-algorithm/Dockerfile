FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash python3 python3-pip tmux sudo \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy buggy source code
COPY src/ /app/src/

# Make source files readable only by root
RUN chown -R root:root /app/src && chmod 600 /app/src/*.py

# Create input data
RUN mkdir -p /app/data && cat > /app/data/input.txt << 'EOF'
42
17
93
8
55
31
76
23
64
12
EOF

# run-code wrapper: execute Python files via sudo
RUN printf '#!/bin/bash\nsudo python3 /app/src/"$@" 2>&1\n' > /usr/local/bin/run-code && chmod 755 /usr/local/bin/run-code

# apply-fix wrapper: overwrite a source file from stdin
RUN printf '#!/bin/bash\nsudo tee /app/src/"$1" > /dev/null\n' > /usr/local/bin/apply-fix && chmod 755 /usr/local/bin/apply-fix

# Sudoers: allow python3 and tee on /app/src/ without password
RUN echo 'ALL ALL=(root) NOPASSWD: /usr/bin/python3 /app/src/*, /usr/bin/tee /app/src/*' > /etc/sudoers.d/vitac && chmod 440 /etc/sudoers.d/vitac

# Output directory
RUN mkdir -p /app/output && chmod 777 /app/output
