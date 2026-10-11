import os, subprocess, json, time
from pathlib import Path
root=Path.cwd()
out=root/'docs/quality/reports/evidence/2026-10-11-stage-b-native-readiness-dev/checks'
env=os.environ.copy()
env['PYTHONPATH']=str(root/'scripts/offline_guard')+':'+str(root/'src')
checks=[('backend',['.venv/bin/python','-m','pytest','-q'],root),('ruff',['uv','run','ruff','check','src','tests','scripts/offline_guard'],root),('format',['uv','run','ruff','format','--check','src','tests','scripts/offline_guard'],root),('mypy',['uv','run','mypy','src'],root),('lock',['uv','lock','--check'],root),('package',['uv','build','--no-build-isolation'],root),('api-types',['npm','run','api:types'],root/'web'),('web-tests',['npm','test'],root/'web'),('web-types',['npm','run','typecheck'],root/'web'),('web-lint',['npm','run','lint'],root/'web'),('web-build',['npm','run','build'],root/'web'),('swift',['swift','build','--package-path','native'],root),('diff',['git','diff','--check'],root)]
results=[]
for name,args,cwd in checks:
 started=time.monotonic()
 with (out/(name+'.log')).open('w') as log:
  log.write('Command: '+repr(args)+'\nWorking directory: '+str(cwd)+'\nGuard: scripts/offline_guard (DNS/non-loopback/Keychain blocked)\n');log.flush()
  p=subprocess.run(args,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT)
 result={'check':name,'command':args,'exit':p.returncode,'seconds':round(time.monotonic()-started,3)}
 results.append(result)
 print(json.dumps(result),flush=True)
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 if p.returncode: raise SystemExit(p.returncode)
