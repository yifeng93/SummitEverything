import datetime, time
from urllib.request import urlopen
from urllib.error import URLError
for i in range(100):
    ts=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds')
    for name,url in [('api','http://127.0.0.1:18905/api/v1/health'),('web','http://127.0.0.1:15185/')]:
        try:
            with urlopen(url,timeout=.15) as r:
                body=r.read().decode() if name=='api' else ''
                print(f'{ts} {name} {r.status} response_url={r.url} {body}',flush=True)
        except Exception as e:
            print(f'{ts} {name} pending {type(e).__name__}',flush=True)
    time.sleep(.25)
