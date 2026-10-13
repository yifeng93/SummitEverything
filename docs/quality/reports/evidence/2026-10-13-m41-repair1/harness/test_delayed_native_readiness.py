import json, os, pathlib, shutil, signal, socket, subprocess, tempfile, time, uuid
app_source = pathlib.Path(os.environ['SUMMIT_SOURCE_APP']).resolve()
temp_root = pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve() / ('summit-m41-delayready-' + uuid.uuid4().hex[:8])
temp_root.mkdir(mode=0o700)
app = temp_root / app_source.name
subprocess.run(['/usr/bin/ditto', str(app_source), str(app)], check=True)
backend = app/'Contents/Resources/backend/summit-backend/summit-backend'
backend.write_text('''#!/usr/bin/python3\nimport json, os, pathlib, sys, threading, time\nfrom http.server import BaseHTTPRequestHandler, ThreadingHTTPServer\nfrom urllib.parse import urlsplit\nroot = pathlib.Path(__file__).resolve().parents[3]\nmanifest = json.loads(pathlib.Path(os.environ["SUMMIT_BUILD_INFO"]).read_text())\nrun_id = os.environ["SUMMIT_RUN_ID"]\nlog = pathlib.Path(__file__).with_name("fake-server.log")\ntime.sleep(4)\nclass Handler(BaseHTTPRequestHandler):\n def do_GET(self):\n  with log.open("a") as out: out.write(self.path + "\\n")\n  if self.path == "/api/v1/health":\n   body = json.dumps({"service":"ready", "run_id":run_id, **manifest}).encode()\n   self.send_response(200); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)\n  elif self.path == "/":\n   body=b"<html>synthetic delayed readiness</html>"\n   self.send_response(200); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)\n  else: self.send_error(404)\n def log_message(self, *args): pass\nclass Server(ThreadingHTTPServer): allow_reuse_address=True\nserver=Server(("127.0.0.1", int(os.environ["SUMMIT_API_PORT"])), Handler)\ndef parent_watch():\n sys.stdin.buffer.read(); server.shutdown()\nthreading.Thread(target=parent_watch, daemon=True).start()\nserver.serve_forever()\nserver.server_close()\n''')
backend.chmod(0o755)
profile = temp_root/'profile'; profile.mkdir(mode=0o700)
home = temp_root/'home'; home.mkdir(mode=0o700)
log = open(temp_root/'native-app.log','wb')
env={'PATH':'','HOME':str(home),'TMPDIR':os.environ['DARWIN_USER_TEMP_DIR'],'SUMMIT_INTERNAL_TEST_PROFILE_ROOT':str(profile)}
proc=subprocess.Popen([str(app/'Contents/MacOS/SummitEverything')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(f'app_pid={proc.pid}')
print(f'app_copy={app}')
print(f'profile={profile}')
requests=backend.with_name('fake-server.log')
try:
 deadline=time.time()+20
 while time.time()<deadline:
  if proc.poll() is not None: raise RuntimeError(f'native app exited early: {proc.returncode}')
  observed=requests.read_text().splitlines() if requests.exists() else []
  if '/' in observed: break
  time.sleep(.1)
 else: raise RuntimeError('native app did not complete readiness after delayed backend')
 print('synthetic_backend_delay_seconds=4')
 print('health_seen_before_root=' + str(observed.index('/api/v1/health') < observed.index('/')))
 print('readiness_after_delay=PASS')
 print('request_paths=' + ','.join(observed))
finally:
 if proc.poll() is None:
  os.kill(proc.pid, signal.SIGTERM); proc.wait(timeout=10)
 for _ in range(50):
  try:
   with socket.create_connection(('127.0.0.1',18793),timeout=.2): pass
   time.sleep(.1)
  except OSError: break
 else: raise RuntimeError('fake readiness backend survived native parent exit')
 log.close()
 print(f'app_exit={proc.returncode}')
