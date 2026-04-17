#!/usr/bin/env python3
import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_URL = "https://api.cerebras.ai/v1"
PORT = int(os.environ.get("PORT", 8080))

class ProxyHandler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
    
    def do_GET(self):
        if self.path == "/v1/models":
            self.proxy_request("GET", "/models")
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"ok"}')
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self.proxy_request("POST", "/chat/completions", body)
        else:
            self.send_error(404)
    
    def proxy_request(self, method, path, body=None):
        try:
            url = f"{CEREBRAS_URL}{path}"
            req = urllib.request.Request(url, method=method)
            req.add_header("Authorization", f"Bearer {CEREBRAS_API_KEY}")
            req.add_header("Content-Type", "application/json")
            
            if body:
                req.data = body
            
            with urllib.request.urlopen(req, timeout=60) as response:
                self.send_response(response.status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            self.send_response(e.code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            self.send_error(500, str(e))
    
    def log_message(self, format, *args):
        print(f"[{self.address_string()}] {args[0]}")
    
    def send_error(self, code, message=None):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        error_body = json.dumps({"error": message or "Server error"}).encode()
        self.wfile.write(error_body)

if __name__ == "__main__":
    if not CEREBRAS_API_KEY:
        print("⚠️  CEREBRAS_API_KEY не установлен!")
        print("   Windows: set CEREBRAS_API_KEY=твой_ключ")
        print("   А затем: python proxy.py")
        exit(1)
    
    print(f"✅ Cerebras Proxy запущен на http://0.0.0.0:{PORT}")
    print(f"📡 API endpoint: http://localhost:{PORT}/v1")
    print(f"🔑 API Key: {CEREBRAS_API_KEY[:20]}...")
    
    server = HTTPServer(("0.0.0.0", PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Сервер остановлен")