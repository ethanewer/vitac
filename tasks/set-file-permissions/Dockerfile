FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/data && echo "id,name,value" > /app/data/report.csv && chmod 000 /app/data/report.csv
