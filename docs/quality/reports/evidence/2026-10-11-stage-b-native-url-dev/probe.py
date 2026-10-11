import subprocess, threading, re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"synthetic Vite readiness")
    def log_message(self,*args): pass
server=HTTPServer(("127.0.0.1",0),Handler)
thread=threading.Thread(target=server.serve_forever);thread.start()
try:
    root=Path.cwd(); line=next(s for s in (root/'native/Sources/SummitEverythingApp/App.swift').read_text().splitlines() if s.startswith('private let webURL'))
    template=re.search(r'URL\(string: "(.*?)"\)',line).group(1)
    url=template.replace(chr(92)+'(webPort)',str(server.server_port))
    run=subprocess.run(['swift',str(Path(__file__).with_name('url-probe.swift')),url],capture_output=True,text=True)
    print(run.stdout,end=''); print(run.stderr,end='')
    assert run.returncode==0 and 'status=200' in run.stdout and 'equal=true' in run.stdout, 'production URL must match actual URLSession response'
finally:
    server.shutdown();server.server_close();thread.join()
