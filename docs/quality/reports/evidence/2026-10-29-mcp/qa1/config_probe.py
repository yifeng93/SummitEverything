import os, pathlib, subprocess, sys, tempfile
root=pathlib.Path.cwd()
base={**os.environ, 'PYTHONPATH':str(root/'src')}
cmd=[sys.executable,'-m','summit_everything.mcp_server']
with tempfile.TemporaryDirectory() as td:
    td=pathlib.Path(td)
    target=td/'token'; target.write_text('synthetic-token'); target.chmod(0o600)
    link=td/'link'; link.symlink_to(target)
    cases={
      'missing_token': ({k:v for k,v in base.items() if k not in ('SUMMIT_MCP_TOKEN','SUMMIT_MCP_TOKEN_FILE')}, '请设置'),
      'bad_token': ({**base,'SUMMIT_MCP_TOKEN':'SENTINEL secret'}, 'token 不能为空'),
      'symlink_token_file': ({**base,'SUMMIT_MCP_TOKEN_FILE':str(link)}, 'token 文件必须归当前用户所有'),
      'nonloopback_url': ({**base,'SUMMIT_API_URL':'http://example.com:8793','SUMMIT_MCP_TOKEN':'safe-token'}, '主机必须是 loopback'),
      'url_path': ({**base,'SUMMIT_API_URL':'http://127.0.0.1:8793/prefix','SUMMIT_MCP_TOKEN':'safe-token'}, '不得包含路径'),
    }
    failed=False
    for name,(env,expect) in cases.items():
      env={k:v for k,v in env.items() if k not in ('SUMMIT_MCP_TOKEN','SUMMIT_MCP_TOKEN_FILE','SUMMIT_API_URL')}
      env.update({k:v for k,v in cases[name][0].items() if k.startswith(('SUMMIT_','PYTHONPATH'))})
      p=subprocess.run(cmd,cwd=root,env=env,text=True,capture_output=True,timeout=10)
      ok=p.returncode==2 and p.stdout=='' and expect in p.stderr and 'SENTINEL' not in p.stderr
      print(f'{name}: {"PASS" if ok else "FAIL"} exit={p.returncode} stdout_empty={p.stdout==""} expected_message={expect in p.stderr}')
      if not ok:
        print(p.stderr[:500]); failed=True
    raise SystemExit(1 if failed else 0)
