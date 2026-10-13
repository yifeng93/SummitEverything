import json, os, pathlib, shutil, signal, socket, subprocess, tempfile, time, urllib.request, uuid

source = pathlib.Path(os.environ['SUMMIT_SOURCE_APP']).resolve()
temp_root = pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve() / ('summit-m41-upload-fix1-' + uuid.uuid4().hex[:8])
temp_root.mkdir(mode=0o700)
app = temp_root / source.name
subprocess.run(['/usr/bin/ditto', str(source), str(app)], check=True)
profile = temp_root / 'profile'
profile.mkdir(mode=0o700)
with socket.socket() as probe:
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    probe.bind(('127.0.0.1', 18793))
    probe.listen(1)
env = {'PATH':'', 'HOME':str(temp_root/'home'), 'TMPDIR':os.environ['DARWIN_USER_TEMP_DIR'], 'SUMMIT_INTERNAL_TEST_PROFILE_ROOT':str(profile)}
(pathlib.Path(env['HOME'])).mkdir()
log = open(temp_root/'native-app.log', 'wb')
proc = subprocess.Popen([str(app/'Contents/MacOS/SummitEverything')], env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
print(f'app_pid={proc.pid}')
print(f'app_copy={app}')
print(f'profile={profile}')
try:
    health = None
    for _ in range(120):
        if proc.poll() is not None:
            raise RuntimeError(f'native app exited before readiness: {proc.returncode}')
        try:
            with urllib.request.urlopen('http://127.0.0.1:18793/api/v1/health', timeout=1) as response:
                health = json.loads(response.read())
                break
        except Exception:
            time.sleep(.25)
    if health is None:
        raise RuntimeError('native app backend readiness timeout')
    identity = json.loads((app/'Contents/Resources/build-info.json').read_text())
    expected = {k: identity[k] for k in ('source_sha','dirty','build_id','app_version','frontend_sha256','dependencies_sha256')}
    observed = {k: health.get(k) for k in expected}
    if observed != expected:
        raise RuntimeError('native app readiness identity mismatch')
    print('readiness=PASS')
    print(f'health_run_id={health.get("run_id")}')
    children = [parts[0] for row in subprocess.check_output(['/bin/ps','-A','-o','pid,ppid,command'], text=True).splitlines()[1:] if len(parts := row.strip().split(None, 2)) == 3 and parts[1] == str(proc.pid)]
    print('backend_child_pids=' + ','.join(children))
finally:
    if proc.poll() is None:
        os.kill(proc.pid, signal.SIGTERM)
        proc.wait(timeout=10)
    for _ in range(80):
        listener_alive = True
        try:
            urllib.request.urlopen('http://127.0.0.1:18793/api/v1/health', timeout=.25).close()
        except Exception:
            listener_alive = False
        child_alive = False
        for child in children if 'children' in locals() else []:
            try:
                os.kill(int(child), 0)
                child_alive = True
            except ProcessLookupError:
                pass
        if not listener_alive and not child_alive:
            break
        time.sleep(.1)
    else:
        raise RuntimeError(f'backend cleanup incomplete: listener={listener_alive}, child={child_alive}')
    log.close()
    print(f'app_exit={proc.returncode}')
    print('parent_cleanup=PASS')
