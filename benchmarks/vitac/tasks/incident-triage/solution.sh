#!/bin/bash
sed -i 's/port=5432/port=5433/' /app/config/db.conf
find /app/cache/ -name "*.tmp" -mtime +0 -delete
cp /app/certs/renewed/server.pem /app/certs/active/server.pem
