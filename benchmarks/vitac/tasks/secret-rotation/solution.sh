#!/bin/bash
# Replace all old secrets with new ones
find /app/config /app/services /app/env -type f | xargs sed -i 's/oldpass123/Kx9mP2qL7nW/g'
find /app/config /app/services /app/env -type f | xargs sed -i 's/sk-old-key-abc123/sk-new-key-xyz789/g'
find /app/config /app/services /app/env -type f | xargs sed -i 's/jwt-secret-old-value/hN4kQ8wR2vBj5mT/g'
