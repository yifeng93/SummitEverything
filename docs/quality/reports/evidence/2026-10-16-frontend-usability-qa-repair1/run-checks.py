import json, subprocess
from pathlib import Path
root = Path(__file__).parent
repo = Path(__file__).resolve().parents[3]
commands = [
    ('web-test', ['npm','test']),
    ('web-typecheck', ['npm','run','typecheck']),
    ('web-lint', ['npm','run','lint']),
    ('web-build', ['npm','run','build']),
    ('web-api-types', ['npm','run','api:types']),
    ('web-e2e', ['npm','run','test:e2e']),
    ('web-e2e-integration', ['npm','run','test:e2e:integration']),
]
results=[]
for name, cmd in commands:
    proc = subprocess.run(cmd, cwd=repo/'web', text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    log = root/'logs'/f'{name}.log'
    log.write_text(proc.stdout)
    results.append({'name':name,'command':'cd web && '+' '.join(cmd),'exit_code':proc.returncode,'log':str(log)})
    print(f'===== {name} EXIT_CODE={proc.returncode} =====')
    print(proc.stdout[-7000:])
(root/'check-status.json').write_text(json.dumps(results, indent=2)+'\n')
