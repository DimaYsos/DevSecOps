from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime

received_webhooks = []

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"raw": body}

        entry = {
            "path": self.path,
            "timestamp": datetime.utcnow().isoformat(),
            "headers": dict(self.headers),
            "body": data,
        }
        received_webhooks.append(entry)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "received",
            "id": len(received_webhooks),
            "path": self.path,
        }).encode())

    def do_GET(self):
        if self.path == "/health":
            self._json_response(200, {"status": "ok", "service": "mock-webhook-receiver"})
        elif self.path == "/webhooks":
            self._json_response(200, {"webhooks": received_webhooks[-100:]})
        elif self.path == "/webhooks/clear":
            received_webhooks.clear()
            self._json_response(200, {"status": "cleared"})
        else:
            self._json_response(200, {"status": "ok", "path": self.path})

    def _json_response(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9002), WebhookHandler)
    server.serve_forever()
