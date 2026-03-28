#!/usr/bin/env python3
"""Generate nginx configuration from parameters."""

def generate_config(domain, listen_port, upstream_host, upstream_port):
    config = f"""server {{
    listen {listen_port};
    server_name localhost;

    location / {{
        proxy_pass http://{upstream_host}:{port}
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
