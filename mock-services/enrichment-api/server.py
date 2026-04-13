from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os

FLAG_PATH = "/flags/flag.txt"

def read_flag():
    try:
        with open(FLAG_PATH) as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""

class EnrichmentHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        if parsed.path == "/health":
            self._json_response(200, {"status": "ok"})

        elif parsed.path == "/internal/flag":
            self._json_response(200, {"flag": read_flag()})

        elif parsed.path == "/api/enrich/user":
            email = params.get("email", [""])[0]
            username = params.get("username", [""])[0]
            self._json_response(200, {
                "email": email,
                "username": username,
                "department": "Enriched Department",
                "phone": "+1-555-0100",
                "bio": f"Enriched profile for {username}",
                "company": "External Corp",
                "title": "Senior Engineer",
                "location": "San Francisco, CA",
                "preferences": {"theme": "dark", "notifications": True},
            })

        elif parsed.path == "/api/enrich/asset":
            serial = params.get("serial", [""])[0]
            tag = params.get("tag", [""])[0]
            self._json_response(200, {
                "serial_number": serial,
                "asset_tag": tag,
                "vendor_info": {"warranty_status": "active", "support_level": "premium"},
                "vulnerability_scan": {"cve_count": 3, "critical": 1},
                "custom_fields": {"enriched": True, "scan_date": "2024-01-15"},
                "status": "maintenance",
            })

        elif parsed.path == "/api/lookup/address":
            query = params.get("q", [""])[0]
            self._json_response(200, {
                "query": query,
                "results": [
                    {"address": "123 Main St", "city": "Springfield", "state": "IL", "zip": "62701"},
                    {"address": "456 Oak Ave", "city": "Springfield", "state": "IL", "zip": "62702"},
                ],
            })

        else:
            self._json_response(404, {"error": "Not found"})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9003), EnrichmentHandler)
    server.serve_forever()
