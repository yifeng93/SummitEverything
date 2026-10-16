from pathlib import Path
import subprocess, sys

root = Path.cwd()
web = root / 'web'
logdir = root / '.local/dev/frontend-a/current/mutations'
logdir.mkdir(parents=True, exist_ok=True)

cases = [
    ('guard-1-internal-details', 'src/components/SettingsView.tsx',
     '<p className="settings-card-desc">知识正文保存在这个工作库；索引、聊天历史、凭据与诊断记录按本机 profile 管理。</p>',
     '<p className="settings-card-desc">{String(settings?.embedding_fingerprint)}</p>',
     ['npm','test','--','--run','src/components/SettingsView.cards.test.tsx','-t','keeps internal identifiers']),
    ('guard-3-font-floor', 'src/App.css',
     '.settings-card-desc { margin: 0; color: var(--muted); font-size: var(--text-small);',
     '.settings-card-desc { margin: 0; color: var(--muted); font-size: 11px;',
     ['npm','test','--','--run','src/ui-contract.test.ts','-t','没有低于 12px']),
    ('guard-4-error-not-empty', 'src/components/SettingsView.tsx',
     "label: settingsReadFailed ? '暂时无法读取' : '正在读取'",
     "label: settingsReadFailed ? '没有待处理' : '正在读取'",
     ['npm','test','--','--run','src/components/SettingsView.cards.test.tsx','-t','settings read failure']),
    ('guard-5-cancel-is-not-confirm', 'src/components/ConfirmDialog.tsx',
     'onClick={onCancel}>取消</button>',
     'onClick={onConfirm}>取消</button>',
     ['npm','test','--','--run','src/components/SettingsView.regressions.test.tsx','-t','does not delete a credential']),
    ('guard-6-stream-hides-open-syntax', 'src/components/StreamingMarkdown.tsx',
     'content={complete ? content : stablePrefix(content)}',
     'content={content}',
     ['npm','test','--','--run','src/components/MarkdownText.test.tsx','-t','holds unfinished syntax']),
    ('guard-7-dark-contrast', 'src/theme-tokens.css',
     '  --ink: #e7ebe7;', '  --ink: #222a27;',
     ['npm','test','--','--run','src/theme.test.ts','-t','深色 tokens 的 10 组对比度']),
    ('guard-8-three-settings-cards', 'src/components/SettingsView.tsx',
     'aria-label="飞书">', 'aria-label="飞书连接">',
     ['npm','test','--','--run','src/components/SettingsView.cards.test.tsx','-t','renders the three main cards']),
    ('guard-9-save-does-not-smoke', 'src/components/SettingsView.tsx',
     "await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret })",
     "await api.put('/credentials/deepseek', { account_id: credentialAccountId(updated, 'deepseek'), secret: deepseekSecret }); await api.post('/provider-smoke/deepseek-chat', {})",
     ['npm','test','--','--run','src/components/SettingsView.cards.test.tsx','-t','does not start any provider check']),
    ('guard-10-responsive-overflow', 'src/App.css',
     '.settings-cards { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; max-width: 760px; min-width: 0;',
     '.settings-cards { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; max-width: 760px; min-width: 360px;',
     ['npm','run','test:e2e','--','--grep','offline viewport']),
]

summary=[]
for name, rel, old, new, command in cases:
    path = web / rel
    original = path.read_text()
    if old not in original:
        raise SystemExit(f'{name}: mutation anchor not found')
    path.write_text(original.replace(old, new, 1))
    try:
        result = subprocess.run(command, cwd=web, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        (logdir / f'{name}.log').write_text(f'$ {" ".join(command)}\nEXIT={result.returncode}\n\n{result.stdout}')
        caught = result.returncode != 0
        summary.append((name, result.returncode, caught))
        print(f'{name}: exit={result.returncode} mutation_caught={caught}')
        if not caught:
            print(result.stdout[-2500:])
    finally:
        path.write_text(original)

(logdir / 'summary.txt').write_text('\n'.join(f'{name}: exit={code}, mutation_caught={caught}' for name,code,caught in summary)+'\n')
if any(not caught for _,_,caught in summary):
    sys.exit(1)
