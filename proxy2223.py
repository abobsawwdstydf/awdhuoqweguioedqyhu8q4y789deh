#!/usr/bin/env python3
"""
Cerebras Proxy Server for Render
Единственный файл, никаких зависимостей кроме встроенного Python
"""

import os
import json
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

# Конфигурация из переменных окружения Render
CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_URL = "https://api.cerebras.ai/v1"
PORT = int(os.environ.get("PORT", 8080))

class CerebrasProxyHandler(BaseHTTPRequestHandler):
    
    def do_OPTIONS(self):
        """CORS preflight request"""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.end_headers()
    
    def do_GET(self):
        """Обработка GET запросов"""
        if self.path == "/v1/models":
            self.proxy_to_cerebras("GET", "/models")
        elif self.path == "/health":
            self.send_health_check()
        elif self.path == "/" or self.path == "":
            self.send_service_info()
        else:
            self.send_error(404, f"Endpoint {self.path} not found")
    
    def do_POST(self):
        """Обработка POST запросов"""
        if self.path == "/v1/chat/completions":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            self.proxy_to_cerebras("POST", "/chat/completions", body)
        else:
            self.send_error(404, f"Endpoint {self.path} not found")
    
    def proxy_to_cerebras(self, method, path, body=None):
        """Проксирование запроса к Cerebras API"""
        try:
            url = f"{CEREBRAS_URL}{path}"
            req = urllib.request.Request(url, method=method)
            
            # Добавляем заголовки
            req.add_header("Authorization", f"Bearer {CEREBRAS_API_KEY}")
            req.add_header("Content-Type", "application/json")
            req.add_header("Accept", "application/json")
            
            if body:
                req.data = body
            
            # Логируем запрос
            print(f"[PROXY] {method} {url}")
            if body:
                print(f"[PROXY] Body: {body[:200]}...")
            
            # Отправляем запрос
            with urllib.request.urlopen(req, timeout=120) as response:
                response_data = response.read()
                
                # Отправляем ответ клиенту
                self.send_response(response.status)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(response_data)
                
                print(f"[PROXY] Response status: {response.status}")
                
        except urllib.error.HTTPError as e:
            # Ошибка от Cerebras API
            error_data = e.read() if e.fp else b'{}'
            print(f"[PROXY ERROR] HTTP {e.code}: {e.reason}")
            print(f"[PROXY ERROR] Response: {error_data}")
            
            self.send_response(e.code)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_data)
            
        except urllib.error.URLError as e:
            # Ошибка соединения
            print(f"[PROXY ERROR] URL Error: {e.reason}")
            error_response = json.dumps({
                "error": {
                    "message": f"Connection error: {str(e.reason)}",
                    "type": "connection_error"
                }
            }).encode()
            self.send_response(502)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_response)
            
        except Exception as e:
            # Другие ошибки
            print(f"[PROXY ERROR] Unexpected: {str(e)}")
            error_response = json.dumps({
                "error": {
                    "message": f"Internal proxy error: {str(e)}",
                    "type": "proxy_error"
                }
            }).encode()
            self.send_response(500)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(error_response)
    
    def send_health_check(self):
        """Health check endpoint"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        health_status = {
            "status": "ok",
            "service": "cerebras-proxy",
            "cerebras_configured": bool(CEREBRAS_API_KEY),
            "timestamp": str(__import__("time").time())
        }
        self.wfile.write(json.dumps(health_status).encode())
    
    def send_service_info(self):
        """Информация о сервисе"""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        info = {
            "service": "Cerebras API Proxy",
            "version": "2.0.0",
            "endpoints": [
                "GET  /v1/models",
                "POST /v1/chat/completions",
                "GET  /health"
            ],
            "config": {
                "cerebras_api_configured": bool(CEREBRAS_API_KEY),
                "cerebras_url": CEREBRAS_URL
            }
        }
        self.wfile.write(json.dumps(info, indent=2).encode())
    
    def log_message(self, format, *args):
        """Кастомное логирование"""
        print(f"[{self.address_string()}] {args[0]}")

def main():
    """Запуск сервера"""
    print("=" * 60)
    print("Cerebras Proxy Server for Render")
    print("=" * 60)
    
    if not CEREBRAS_API_KEY:
        print("⚠️  WARNING: CEREBRAS_API_KEY environment variable is not set!")
        print("   Please add it in Render dashboard:")
        print("   - Go to your Web Service → Environment")
        print("   - Add: CEREBRAS_API_KEY = your_api_key")
        print("=" * 60)
    else:
        print(f"✅ API Key configured: {CEREBRAS_API_KEY[:20]}...")
    
    print(f"🚀 Server starting on 0.0.0.0:{PORT}")
    print(f"📡 Health check: http://localhost:{PORT}/health")
    print(f"📡 API endpoint: http://localhost:{PORT}/v1")
    print(f"📡 Models: http://localhost:{PORT}/v1/models")
    print("=" * 60)
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    
    server = HTTPServer(("0.0.0.0", PORT), CerebrasProxyHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped by user")
        server.shutdown()

if __name__ == "__main__":
    main()
