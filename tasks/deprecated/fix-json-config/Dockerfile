FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux jq && rm -rf /var/lib/apt/lists/*
WORKDIR /app
RUN mkdir -p /app/config && cat > /app/config/settings.json << 'EOF'
{
  "app_name": "myservice",
  "port": 3000,
  "debug": true,
  "log_level": "info",
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "mydb"
  }
}
EOF
