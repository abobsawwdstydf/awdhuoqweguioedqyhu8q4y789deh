#!/usr/bin/env python3
"""
Groq API Proxy Server for Render
Простой прокси для Groq API, работает из любой облачной среды
"""

import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# Конфигурация
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1"
PORT = int(os.environ.get("PORT", 8080))

class GroqProxyHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
    
    def do_GET(self):
        if self.path == "/v1/models":
            self.proxy_to_groq("GET", "/models")
        elif self.path == "/health":
            self.send_health_check()
        else:
            self.send_error(404)
    
    def do_POST(self):
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self.proxy_to_groq("POST", "/chat/completions", body)
        else:
            self.send_error(404)
    
    def proxy_to_groq(self, method, path, body=None):
        try:
            url = f"{GROQ_URL}{path}"
            req = urllib.request.Request(url, method=method)
            req.add_header("Authorization", f"Bearer {GROQ_API_KEY}")
            req.add_header("Content-Type", "application/json")
            
            if body:
                req.data = body
            
            print(f"[PROXY] {method} {url}")
            
            with urllib.request.urlopen(req, timeout=60) as response:
                self.send_response(response.status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response.read())
                
        except urllib.error.HTTPError as e:
            error_data = e.read() if e.fp else b'{}'
            self.send_response(e.code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_data)
        except Exception as e:
            error_response = json.dumps({"error": str(e)}).encode()
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(error_response)
    
    def send_health_check(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "service": "groq-proxy"}).encode())

if __name__ == "__main__":
    if not GROQ_API_KEY:
        print("⚠️  GROQ_API_KEY not set!")
        exit(1)
    
    print(f"🚀 Groq Proxy on 0.0.0.0:{PORT}")
    server = HTTPServer(("0.0.0.0", PORT), GroqProxyHandler)
    server.serve_forever()
