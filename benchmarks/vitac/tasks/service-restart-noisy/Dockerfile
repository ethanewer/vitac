FROM ubuntu:24.04

RUN apt-get update && apt-get install -y \
    bash python3 python3-pip tmux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY svcctl.py /app/svcctl.py
RUN chmod +x /app/svcctl.py
