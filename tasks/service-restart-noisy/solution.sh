#!/bin/bash
python3 /app/svcctl.py restart payment-gateway
python3 /app/svcctl.py restart notification-service
