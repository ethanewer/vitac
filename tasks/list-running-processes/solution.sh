#!/bin/bash
tail -n +2 /app/data/users.csv | cut -d, -f2 | sort -u > /app/output/usernames.txt
