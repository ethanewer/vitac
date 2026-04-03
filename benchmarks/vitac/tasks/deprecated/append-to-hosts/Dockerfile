FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/etc && printf "127.0.0.1 localhost\n::1 localhost\n" > /app/etc/hosts
