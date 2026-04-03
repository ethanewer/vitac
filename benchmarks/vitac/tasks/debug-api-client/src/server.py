#!/usr/bin/env python3
"""Mock REST API server."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json

VALID_TOKEN = "secret-api-key-12345"

DATA = {
    "results": [
        {"id": 1, "name": "Alpha", "value": 100},
        {"id": 2, "name": "Beta", "value": 200},
        {"id": 3, "name": "Gamma", "value": 300},
    ],
    "total": 3
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        auth = self.headers.get("Authorization", "")
        if auth != f"Bearer {VALID_TOKEN}":
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized. Expected 'Bearer <token>' in Authorization header."}).encode())
            return

        if self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(DATA).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logs

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 5000), Handler)
    print("Mock API server running on port 5000")
    server.serve_forever()
