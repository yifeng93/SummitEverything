import json, os, pathlib, shutil, subprocess, tempfile, uuid
app = pathlib.Path(os.environ['SUMMIT_SOURCE_APP']).resolve()
root = pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve() / ('summit-m41-tamper-' + uuid.uuid4().hex[:8])
(root/'web').mkdir(parents=True)
shutil.copytree(app/'Contents/Resources/web', root/'web', dirs_exist_ok=True)
shutil.copy2(app/'Contents/Resources/build-info.json', root/'build-info.json')
shutil.copy2(app/'Contents/Resources/dependencies.json', root/'dependencies.json')
entry = root/'web'/'index.html'
entry.write_bytes(entry.read_bytes() + b'<!-- synthetic tamper -->')
env = {
 'PATH':'', 'HOME':str(root/'home'), 'TMPDIR':os.environ['DARWIN_USER_TEMP_DIR'],
 'SUMMIT_PROFILE_ROOT':str(root/'profile'), 'SUMMIT_API_PORT':'18795', 'SUMMIT_WEB_PORT':'18795',
 'SUMMIT_RUN_ID':'synthetic-tamper-run', 'SUMMIT_SESSION_TOKEN':'synthetic-tamper-token',
 'SUMMIT_BUILD_INFO':str(root/'build-info.json'), 'SUMMIT_WEB_DIST':str(root/'web')
}
pathlib.Path(env['HOME']).mkdir()
pathlib.Path(env['SUMMIT_PROFILE_ROOT']).mkdir()
result = subprocess.run([str(app/'Contents/Resources/backend/summit-backend/summit-backend')], env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=10)
text = result.stdout.decode('utf-8', errors='replace')
print(f'backend_exit={result.returncode}')
print(f'tamper_rejected={result.returncode != 0}')
print(f'diagnostic_mentions_frontend_mismatch={"frontend identity does not match" in text}')
print('diagnostic=' + text.strip().splitlines()[-1][:300] if text.strip() else 'diagnostic=<empty>')
if result.returncode == 0 or 'synthetic-tamper-token' in text:
    raise SystemExit(1)
