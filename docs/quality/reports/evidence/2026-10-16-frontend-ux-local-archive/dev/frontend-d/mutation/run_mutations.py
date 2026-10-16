from __future__ import annotations

import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
OUT.mkdir(parents=True, exist_ok=True)

cases = [
    ("01-metadata", "web/src/components/SettingsView.tsx", "<span>Embedding 配置</span><strong>{settings.embedding_fingerprint ? '已配置' : '未配置'}</strong>", "<span>Embedding 配置</span><strong>{settings.embedding_fingerprint ?? '—'}</strong>", "npm --prefix web test -- --run src/ui-contract.render.test.tsx"),
    ("02-chinese", "web/src/components/AppShell.tsx", 'aria-label="主导航"', 'aria-label="Main navigation"', "npm --prefix web test -- --run src/components/AppShell.test.tsx"),
    ("03-font", "web/src/theme-tokens.css", "--text-caption: 12px;", "--text-caption: 11px;", "npm --prefix web test -- --run src/ui-contract.test.ts"),
    ("04-loading", "web/src/components/TodayView.tsx", "正在读取收件箱…", "收件箱目前没有内容。", "npm --prefix web test -- --run src/components/TodayView.test.tsx"),
    ("05-confirm", "web/src/components/FeishuPanel.tsx", "onClick={() => setConfirmDisconnect(true)}", "onClick={() => void logout()}", "npm --prefix web test -- --run src/components/FeishuPanel.test.tsx"),
    ("06-streaming", "web/src/components/StreamingMarkdown.tsx", "const preview = complete ? content : stabilise(content)", "const preview = content", "npm --prefix web test -- --run src/components/MarkdownText.test.tsx src/components/AskView.test.tsx"),
    ("07-contrast", "web/src/theme-tokens.css", "--muted: #666f6e;", "--muted: #ffffff;", "npm --prefix web test -- --run src/theme.test.ts"),
    ("08-geometry", "web/src/App.css", ".sidebar { width: 200px;", ".sidebar { width: 201px;", "npm --prefix web test -- --run src/ui-contract.test.ts"),
    ("09-no-plan", "web/src/components/TodayView.tsx", "const rows = await api.get<IntakeItem[]>('/intake/items')", "const rows = await api.get<IntakeItem[]>('/intake/items')\n      await api.get('/index/plans')", "npm --prefix web test -- --run src/ui-contract.render.test.tsx"),
    ("10-viewport", "web/src/App.css", ".app-frame { min-height: 100vh;", ".app-frame { min-width: 1200px; min-height: 100vh;", "SUMMIT_E2E_EVIDENCE_DIR=.local/dev/frontend-d/mutation/viewport npm --prefix web run test:e2e -- --config playwright.config.ts"),
]

results = []
for name, relpath, old, new, command in cases:
    path = ROOT / relpath
    original = path.read_text()
    if old not in original:
        raise RuntimeError(f"mutation anchor missing: {name} {relpath} {old!r}")
    if original.count(old) != 1:
        raise RuntimeError(f"mutation anchor not unique: {name} count={original.count(old)}")
    path.write_text(original.replace(old, new, 1))
    try:
        red = subprocess.run(command, cwd=ROOT, shell=True, text=True, capture_output=True)
        (OUT / f"{name}.red.log").write_text(red.stdout + red.stderr)
        (OUT / f"{name}.red.exit").write_text(f"{red.returncode}\n")
    finally:
        path.write_text(original)
    green = subprocess.run(command, cwd=ROOT, shell=True, text=True, capture_output=True)
    (OUT / f"{name}.green.log").write_text(green.stdout + green.stderr)
    (OUT / f"{name}.green.exit").write_text(f"{green.returncode}\n")
    result = {"guard": name, "red_exit": red.returncode, "green_exit": green.returncode}
    results.append(result)
    print(json.dumps(result, ensure_ascii=False))

(OUT / "manifest.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
if any(row["red_exit"] == 0 or row["green_exit"] != 0 for row in results):
    raise SystemExit(1)
