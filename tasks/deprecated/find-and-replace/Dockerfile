FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux sed && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/docs && \
    echo "Welcome to ACME Corp. ACME Corp is the best." > /app/docs/readme.txt && \
    echo "Contact ACME Corp at info@acme.com" > /app/docs/contact.txt && \
    echo "ACME Corp Employee Handbook v2.0" > /app/docs/handbook.txt && \
    echo "This file has no company name." > /app/docs/notes.txt
