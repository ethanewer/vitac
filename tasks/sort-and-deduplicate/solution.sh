#!/bin/bash
head -1 /app/data/records.csv > /app/output/clean.csv
tail -n +2 /app/data/records.csv | sort -u | sort -t, -k3,3 -n -r >> /app/output/clean.csv
