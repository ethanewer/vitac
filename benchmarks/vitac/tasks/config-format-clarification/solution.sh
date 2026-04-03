#!/bin/bash
cat > /app/config/app_config.yaml << 'EOF'
app_name: widget-service
port: 8080
database:
  host: db.internal.example.com
  port: 5432
  name: widgets_prod
log_level: info
EOF
