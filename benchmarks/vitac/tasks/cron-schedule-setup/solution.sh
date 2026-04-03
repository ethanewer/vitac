#!/bin/bash
cat > /app/config/crontab << 'EOF'
30 2 * * * /usr/local/bin/backup-db.sh
0 */6 * * * /usr/local/bin/rotate-logs.sh
*/5 * * * * /usr/local/bin/health-check.sh
0 8 * * 0 /usr/local/bin/weekly-report.sh
0 0 1 * * /usr/local/bin/monthly-cleanup.sh
EOF
