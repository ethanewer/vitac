#!/bin/bash
# Reference solution: delete logs older than 7 days in /app/var/log/app/
# but preserve the audit/ subdirectory
find /app/var/log/app/ -maxdepth 1 -name "*.log" -mtime +7 -delete
