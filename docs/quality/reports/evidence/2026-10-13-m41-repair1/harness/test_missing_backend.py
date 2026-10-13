import os, pathlib, shutil, signal, socket, subprocess, time, uuid, urllib.error, urllib.request
source=pathlib.Path(os.environ['SUMMIT_SOURCE_APP']).resolve()
root=pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve()/('summit-m41-missing-backend-'+uuid.uuid4().hex[:8]); root.mkdir(mode=0o700)
app=root/source.name; subprocess.run(['/usr/bin/ditto',str(source),str(app)],check=True)
backend=app/'Contents/Resources/backend/summit-backend/summit-backend'; backend.rename(backend.with_name('summit-backend.removed-for-test'))
profile=root/'profile'; profile.mkdir(mode=0o700); home=root/'home'; home.mkdir(mode=0o700)
with socket.socket() as probe: probe.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); probe.bind(('127.0.0.1',18793))
log=open(root/'native-app.log','wb'); env={'PATH':'','HOME':str(home),'TMPDIR':os.environ['DARWIN_USER_TEMP_DIR'],'SUMMIT_INTERNAL_TEST_PROFILE_ROOT':str(profile)}
proc=subprocess.Popen([str(app/'Contents/MacOS/SummitEverything')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(f'app_pid={proc.pid}'); print(f'app_copy={app}'); print(f'profile={profile}')
time.sleep(2)
try:
 if proc.poll() is not None: raise RuntimeError(f'app exited before modal handling: {proc.returncode}')
 try:
  urllib.request.urlopen('http://127.0.0.1:18793/api/v1/health',timeout=.5)
  raise RuntimeError('unexpected service became ready with missing backend')
 except urllib.error.URLError: pass
 print('service_not_ready=PASS')
 print('modal_ui_observed=NOT_RUN_locked_screen')
finally:
 if proc.poll() is None: os.kill(proc.pid,signal.SIGTERM); proc.wait(timeout=10)
 log.close(); print(f'app_exit={proc.returncode}')
