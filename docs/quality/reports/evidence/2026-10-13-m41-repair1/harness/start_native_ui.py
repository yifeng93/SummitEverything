import hashlib, json, os, pathlib, shutil, socket, subprocess, time, uuid, urllib.request
source=pathlib.Path(os.environ['SUMMIT_SOURCE_APP']).resolve()
temp=pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve()/('summit-m41-native-ui-'+uuid.uuid4().hex[:8])
temp.mkdir(mode=0o700)
app=temp/source.name
subprocess.run(['/usr/bin/ditto',str(source),str(app)],check=True)
profile=temp/'profile'; profile.mkdir(mode=0o700)
workspace=temp/'workspace'; workspace.mkdir(mode=0o700)
inputs=temp/'synthetic-inputs'; inputs.mkdir(mode=0o700)
fixtures={'synthetic-upload.txt':b'Synthetic TXT source for M4.1 repair round 1.\nLine two: alpha-742.\n','synthetic-upload.md':b'# Synthetic Markdown\n\nOnly inert source text: `rm -rf /` is an example string, never a command.\n\nFixture marker: bravo-915.\n'}
for name,data in fixtures.items(): (inputs/name).write_bytes(data)
env={'PATH':'','HOME':str(temp/'home'),'TMPDIR':os.environ['DARWIN_USER_TEMP_DIR'],'SUMMIT_INTERNAL_TEST_PROFILE_ROOT':str(profile)}
pathlib.Path(env['HOME']).mkdir()
log=open(temp/'native-app.log','wb')
proc=subprocess.Popen([str(app/'Contents/MacOS/SummitEverything')],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
result={'app_pid':proc.pid,'app_copy':str(app),'profile':str(profile),'workspace':str(workspace),'inputs':str(inputs),'fixture_sha256':{name:hashlib.sha256(data).hexdigest() for name,data in fixtures.items()},'log':str(temp/'native-app.log')}
(temp/'run.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
health=None
for _ in range(120):
 if proc.poll() is not None: raise RuntimeError(f'app exited before readiness: {proc.returncode}')
 try:
  with urllib.request.urlopen('http://127.0.0.1:18793/api/v1/health',timeout=1) as r: health=json.loads(r.read()); break
 except Exception: time.sleep(.25)
if health is None: raise RuntimeError('readiness timeout')
identity=json.loads((app/'Contents/Resources/build-info.json').read_text())
expected={k:identity[k] for k in ('source_sha','dirty','build_id','app_version','frontend_sha256','dependencies_sha256')}
if any(health.get(k)!=v for k,v in expected.items()): raise RuntimeError('health identity mismatch')
result['health_run_id']=health['run_id']; result['backend_pids']=[row['pid'] for row in []]
(temp/'run.json').write_text(json.dumps(result,indent=2))
print('readiness=PASS')
print('profile_is_in_darwin_temp=' + str(str(profile).startswith(str(pathlib.Path(os.environ['DARWIN_USER_TEMP_DIR']).resolve()))))
print('health_source_sha=' + health['source_sha'])
import urllib.request
