from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(503)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"service":"not_ready","run_id":"occupied-port-dummy"}')

    def log_message(self, fmt, *args):
        pass


HTTPServer(("127.0.0.1", 18811), Handler).serve_forever()
