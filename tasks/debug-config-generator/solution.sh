#!/bin/bash
# Fix all three bugs in gen_config.py:
# 1. Use upstream_port instead of port
# 2. Add semicolon after proxy_pass directive
# 3. Use domain parameter instead of hardcoded localhost
cat > /tmp/fixed_gen_config.py << 'PYEOF'
#!/usr/bin/env python3
"""Generate nginx configuration from parameters."""

def generate_config(domain, listen_port, upstream_host, upstream_port):
    config = f"""server {{
    listen {listen_port};
    server_name {domain};

    location / {{
        proxy_pass http://{upstream_host}:{upstream_port};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }}
}}
"""
    return config

if __name__ == "__main__":
    config = generate_config(
        domain="app.example.com",
        listen_port=80,
        upstream_host="backend",
        upstream_port=3000
    )

    with open("/app/output/nginx.conf", "w") as f:
        f.write(config)

    print("Generated nginx config:")
    print(config)
PYEOF
sudo tee /app/src/gen_config.py < /tmp/fixed_gen_config.py > /dev/null
sudo python3 /app/src/gen_config.py
