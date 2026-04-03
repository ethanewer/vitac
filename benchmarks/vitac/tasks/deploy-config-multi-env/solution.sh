#!/bin/bash
mkdir -p /app/deploy

cat > /app/deploy/dev.json << 'EOF'
{
  "app_name": "myservice",
  "environment": "development",
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "myservice_dev",
    "pool_size": 5
  },
  "cache": {
    "host": "localhost",
    "port": 6379
  },
  "features": {
    "dark_mode": true,
    "beta_features": true,
    "maintenance_mode": false
  },
  "replicas": 1,
  "log_level": "debug"
}
EOF

cat > /app/deploy/staging.json << 'EOF'
{
  "app_name": "myservice",
  "environment": "staging",
  "database": {
    "host": "staging-db.internal",
    "port": 5432,
    "name": "myservice_staging",
    "pool_size": 10
  },
  "cache": {
    "host": "staging-cache.internal",
    "port": 6379
  },
  "features": {
    "dark_mode": true,
    "beta_features": true,
    "maintenance_mode": false
  },
  "replicas": 2,
  "log_level": "info"
}
EOF

cat > /app/deploy/prod.json << 'EOF'
{
  "app_name": "myservice",
  "environment": "production",
  "database": {
    "host": "prod-db.internal",
    "port": 5432,
    "name": "myservice_prod",
    "pool_size": 50
  },
  "cache": {
    "host": "prod-cache.internal",
    "port": 6379
  },
  "features": {
    "dark_mode": true,
    "beta_features": false,
    "maintenance_mode": false
  },
  "replicas": 5,
  "log_level": "warn"
}
EOF
