FROM ubuntu:24.04
RUN apt-get update && apt-get install -y bash python3 python3-pip tmux && rm -rf /var/lib/apt/lists/*
WORKDIR /app

# Config files
RUN mkdir -p /app/config /app/services/auth /app/services/worker /app/env

RUN printf 'database:\n  host: db.internal\n  port: 5432\n  password: oldpass123\n  name: production\n' > /app/config/database.yml

RUN printf 'API_ENDPOINT=https://api.example.com\nAPI_KEY=sk-old-key-abc123\nAPI_TIMEOUT=30\n' > /app/config/api.conf

RUN printf '{\n  "jwt_secret": "jwt-secret-old-value",\n  "token_expiry": 3600,\n  "issuer": "myapp"\n}\n' > /app/services/auth/config.json

RUN printf 'WORKER_THREADS=4\nDB_PASSWORD=oldpass123\nQUEUE_URL=redis://cache.internal:6379\n' > /app/services/worker/env

RUN printf 'APP_ENV=production\nDB_PASSWORD=oldpass123\nAPI_KEY=sk-old-key-abc123\nJWT_SECRET=jwt-secret-old-value\nLOG_LEVEL=warn\n' > /app/env/.env.production
