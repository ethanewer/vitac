#!/bin/bash
cat > /app/config/.env << 'EOF'
APP_PORT=3000
DB_HOST=postgres.local
DB_NAME=myapp
SECRET_KEY=supersecret123
EOF
