# App 图标 + DMG 卷图标 独立 QA（固定 SHA `deed704`）

- 受测产品源码 SHA：`deed704b16f2e7adee56e18136b4290d713912fa`（分支 `codex/app-icon-20261016`，base `main` = `8c882ed`）。
- QA 独立 checkout：`/Users/yifengstudio/.codex/worktrees/qa-appicon`（`git worktree add --detach`，detached HEAD）。
  `git rev-parse HEAD` 实测 = `deed704b16f2e7adee56e18136b4290d713912fa`，与受测 SHA 逐字符相同。
- QA 未改产品源码、未改任何已有 tracked 测试、未 push / merge / rebase / 删分支。原始日志在 `.local/qa/appicon/`（脱敏后的小型证据入库）。
- QA 判定：**PASS（限定范围）**，附带 **2 条与实现者声明不符之处**（均可复现性/二进制细节，非产品面缺陷）与 **6 条 Nit**。
  范围 = A 不回归 + B 素材 provenance + C `.icns` 保真度独立复算 + D 构建集成 fail-closed + E 真实产物 + F 边界与凭据。
  范围外一律不计入判定，见文末「本 PASS 明确不覆盖」。

证据根（QA checkout）：`.local/qa/appicon/`。入库脱敏证据：`docs/quality/reports/evidence/2026-10-16-appicon-qa/`。

## 依赖安装与 CI 独立确认

| 项 | 命令 | 实测 |
| :-- | :-- | :-- |
| Python 依赖 | `uv sync --locked --group dev` | exit 0 |
| 构建组依赖 | `uv sync --locked --group dev --group build` | exit 0 |
| Web 依赖 | `npm --prefix web ci` | exit 0（`found 0 vulnerabilities`） |

CI run `38838074701`（QA 通过 `gh run view` 独立查询 GitHub，不依赖实现者转述）：

```
conclusion=success  status=completed  event=pull_request
headSha=deed704b16f2e7adee56e18136b4290d713912fa
workflowName=offline-arm64 checks (python, web, native, DMG)
job: offline-arm64 in 5m7s (ID 116771574784)
annotation: src/App.tsx:124:26 与 src/components/ProjectsView.tsx:62:26 的
            setState-in-effect 警告（该两文件在本轮 diff 为空，属既有告警）
```

**headSha 与受测 SHA 相同，CI 结论为 success —— PASS。**

---

## A. 不回归 — **PASS**

### A1 改动面（最重要一条）

```
git diff --stat 8c882ed deed704 -- web src pyproject.toml uv.lock native/Tests
→ 无输出，exit 0
```

全区间改动面（`git diff --name-status 8c882ed deed704`）实测 **8 个文件**，全部落在允许面：

```
A  assets/branding/README.md
A  assets/branding/favicon.svg
A  assets/branding/logo-mark.svg
A  assets/branding/make-appicon.mjs
A  native/Resources/AppIcon.icns        (Bin 0 -> 175404)
A  native/Resources/VolumeIcon.icns     (Bin 0 -> 175404)
M  scripts/build_macos_app.py           (+100 -12)
A  tests/unit/test_build_app_icon.py    (+132)
```

`web/`、`src/`、`pyproject.toml`、`uv.lock`、`native/Tests` 零改动 → **产品面未被图标改动触及，PASS**。

### A2 前端指纹（web 未动）

```
npm --prefix web run build                                  → exit 0
PYTHONPATH=... uv run python -c "...fingerprint_web_dist('web/dist')"
→ 784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0
```

与期望值 `784ae1ee…dbf0` **逐字符相同 → PASS**（与 PR #21 时 QA 记录的指纹一致，web 面未漂移）。

### A3 自动门（12/12）

| 门 | 实测结果 | exit |
| :-- | :-- | :-- |
| `uv run pytest -q` | **699 passed, 1 warning** in 78.55s（0 failed） | 0 |
| `uv run ruff check src tests` | All checks passed! | 0 |
| `uv run ruff format --check src tests` | 无输出 | 0 |
| `uv run mypy src` | 无输出（Success） | 0 |
| `npm --prefix web test -- --run` | Test Files 26 passed / Tests **222 passed** | 0 |
| `npm --prefix web run typecheck` | 无输出 | 0 |
| `npm --prefix web run lint` | **2 warnings, 0 errors** | 0 |
| `npm --prefix web run build` | 成功 | 0 |
| `npm --prefix web run test:e2e` | **2 passed**（first-use / viewport） | 0 |
| `npm --prefix web run test:e2e:integration` | **1 passed**（approval-today） | 0 |

**计数与实现者声明一致（699 passed / 0 failed），没有门变软、没有计数下降、没有 todo/skipped → PASS。**
2 条 lint warning 位于 `src/App.tsx`、`src/components/ProjectsView.tsx`；该两文件在 `8c882ed..deed704` 零改动（A1 已证），CI annotation 亦指向同两处 → **既有告警，非本轮回归**。

---

## B. 素材 provenance — **PASS**

```
shasum -a 256 assets/branding/logo-mark.svg  → e389f6ba40b9473858fafda85c49668f119bb88e0a2840d503568e0f69fd4dfb ✓
shasum -a 256 assets/branding/favicon.svg    → 2ae04fc3cac92c5c07a3e5a0ea298654f8bb1719d3d825f6bf8635bb01a78ab3 ✓
diff -q assets/branding/logo-mark.svg /Users/yifengstudio/Desktop/Active/YifengBranding/assets/logo/logo-mark.svg → exit 0，无输出 ✓
diff -q assets/branding/favicon.svg   /Users/yifengstudio/Desktop/Active/YifengBranding/assets/logo/favicon.svg   → exit 0，无输出 ✓
```

两个 SHA 与期望逐字符相同，且与品牌库原件**逐字节相同**（未编辑）→ **PASS**。

---

## C. 入库 `.icns` 的保真度（独立复算）— **PASS**

### C1 文件身份

```
file native/Resources/AppIcon.icns   → Mac OS X icon, 175404 bytes, "ic12" type
file native/Resources/VolumeIcon.icns→ Mac OS X icon, 175404 bytes, "ic12" type
head -c 4 native/Resources/AppIcon.icns → 6963 6e73 = "icns" ✓
cmp AppIcon.icns VolumeIcon.icns → exit 0（字节相同）✓
sha256(AppIcon.icns) = sha256(VolumeIcon.icns) = f34b3ef6e86e92d92f036dfef2adffaee44a429aec0f7898adac4403a6c61b00
```

`.icns` 内部块解析（QA 自写）：`ic12, ic07, ic13, ic08, ic04, ic14, ic09, ic05, ic10, ic11, info` —— 无未知块，全部为标准 PNG 型块。**PASS**。

### C2 10 个 representation

```
iconutil -c iconset native/Resources/AppIcon.icns -o <tmp>/AppIcon.iconset → exit 0
ls | wc -l → 10
icon_16x16.png  icon_16x16@2x.png  icon_32x32.png  icon_32x32@2x.png  icon_128x128.png
icon_128x128@2x.png  icon_256x256.png  icon_256x256@2x.png  icon_512x512.png  icon_512x512@2x.png
```

文件名与尺寸齐全（16, 16@2x, 32, 32@2x, 128, 128@2x, 256, 256@2x, 512, 512@2x）→ **PASS**。

### C3 墨色像素逐档实测（QA 自写 Pillow 脚本，不复用实现者脚本）

判定口径按 QA 任务书：`alpha > 140` 且与 `#8FA0A4` / `#B4C0C3` / `#F4F3F0` 三者之一 Chebyshev 距离 ≤ 40。

| 尺寸（来源文件） | QA 实测 | 实现者声称 | 判定 |
| ---: | ---: | ---: | :-- |
| 16（`icon_16x16.png`） | **22** | 22 | ✓ |
| 32（`icon_16x16@2x.png`） | **52** | 52 | ✓ |
| 32（`icon_32x32.png`） | **52** | 52 | ✓ |
| 64（`icon_32x32@2x.png`） | **43** | 43 | ✓ |
| 128（`icon_128x128.png`） | **414** | 414 | ✓ |
| 256（`icon_128x128@2x.png`） | **1901** | 1901 | ✓ |
| 256（`icon_256x256.png`） | **1901** | 1901 | ✓ |
| 512（`icon_256x256@2x.png`） | **7987** | 7987 | ✓ |
| 512（`icon_512x512.png`） | **7987** | 7987 | ✓ |
| 1024（`icon_512x512@2x.png`） | **32668** | 32668 | ✓ |

**逐档全部相符，无一档不符 → PASS。**

QA 另核（README §5 自称口径 `alpha > 0`）：16→22、16@2x→52、32→**58**、64→43、128→414、128@2x→1901、256→1901、256@2x→7987、512→7987、1024→32668。
唯一差异是 `icon_32x32.png` 在 `alpha>0` 下为 **58** 而非 52；差额来自该文件的 6 个半透明像素（见 Nit N-2），不是计数下降。

### C4 四角透明 + 底板色

- 10 个 representation 的四角 `alpha` 全部实测 `[0, 0, 0, 0]` → **圆角外透明，PASS**。
- 底板色实测存在精确 `#1C2124` = `(28,33,36)` 像素：1024 档 **612113** 个；全档位均有精确底板色像素 → **品牌深色 token，PASS**。
- 品牌三色（按最近邻分类、`alpha>0`、距离 ≤40）：**≥32px 四种 token（底板 + primary + primaryDeep + ink）全部出现**，与 README §5 自检声明一致。

### C5 `≥64px 与品牌原件逐像素一致` — **PASS（0 容差，实测 0 差异像素）**

QA 自写最小合成脚本（`.local/qa/appicon/qa_compose.py`，只读 `assets/branding/logo-mark.svg`，不读实现者生成器逻辑），按 1024 画布 + `824×824 rx=185.4` 底板 `#1C2124`、`translate(100,100)` 网格、调色板 外/中圈 `#8FA0A4` / 内圈 `#B4C0C3` / 顶点方块 `#F4F3F0`、`stroke` 原样不放大，用 Playwright Chromium（`web/node_modules`，同一渲染器）在**目标尺寸直接渲染**，与 `iconutil` 解出的对应 representation 逐像素比对：

| 尺寸 | 对比的 representation | 差异像素 | 最大通道差 |
| ---: | :-- | ---: | ---: |
| 64 | `icon_32x32@2x.png` | **0** | **0** |
| 128 | `icon_128x128.png` | **0** | **0** |
| 256 | `icon_256x256.png` | **0** | **0** |
| 256 | `icon_128x128@2x.png` | **0** | **0** |
| 512 | `icon_256x256@2x.png` | **0** | **0** |
| 512 | `icon_512x512.png` | **0** | **0** |
| 1024 | `icon_512x512@2x.png` | **0** | **0** |

**≥64px 与品牌原件逐像素一致，未做任何加粗，实测 0 差异像素 → PASS（最高强度证据）。**

参数标定（QA 独立定位）：实现者文档写的 `cover=0.6796` 是四舍五入的展示值；实际可复现的几何是**符号宽度 = `round(824 × 0.6796) = 560px`**（即 `translate(232, 276.8) scale(5.6)`）。
若按字面 `824 × 0.6796 = 559.9904` 渲染，1024 档会得到 1359 个差异像素（最大 Δ39）；改用 560px 后降为 **0**。因此 560px 是真实参数，`cover=0.6796` 是文档精度问题（Nit N-6），**不影响几何忠实性结论**。

**重编码归因实验（排除 iconutil 嫌疑）**：把 QA 自己的 1024 渲染打成 iconset → `iconutil -c icns` → 再 `iconutil -c iconset` 解回，与原始 PNG 比对 = **0 差异像素** → **iconutil 往返是无损的**，C5 的 0 差异不是重编码掩盖出来的。

### C5b 16/32px「有意偏离原始描边」独立复现

- `icon_16x16@2x.png`（32px，使用 `favicon.svg` 小变体 + 0.90px 最小物理描边、`cover=0.7779` → 符号宽度 `round(824×0.7779)=641`）：QA 独立渲染与之比对 = **5 差异像素，最大通道差 2**（近乎逐像素一致）。
- `icon_16x16.png`：**alpha 通道逐字节相同（0 差异）**；44 个 RGB 差异**全部**位于 `alpha<255` 的半透明像素，`alpha=255` 的像素**零差异** → 几何一致，仅半透明像素的存储色不同（Nit N-3）。
- README 声称的对照数字 QA 独立复现：`strict`（不加粗）在 16px 实测 **5 个品牌色像素**（QA 自渲自数 = 5，与 README §5「strict 16 → 5」一致）。
- 算术复核：`1.5/100 = 1.500%`、`2.6/67 = 3.881% ≈ 3.9%`、`1.5 × (824×0.6796/100) × (16/1024) = 0.13125 ≈ 0.13` 物理像素 —— 与 README §4 陈述一致。

### C6 `assets/branding/README.md` 逐条核对

| 必须写明的内容 | 实测 | 判定 |
| :-- | :-- | :-- |
| 16/32px 偏离原始描边的**原因** | §4「为什么 16/32px 要偏离原始描边」：小尺寸可读性；给出 1.5% / 3.9% 原描边占比与 0.13 物理像素推算 | ✓ 属实 |
| 偏离的**数值** | §3/§4：`minStroke 0.90px`（16/32px），≥64px 不做任何处理 | ✓ 属实（QA 独立复现 5px / 22px） |
| 来源**绝对路径与日期** | §1 表：两个品牌库绝对路径 + 取用日期 `2026-10-16` | ✓ 路径经 `diff -q` 验证为逐字节相同；日期与 `051dbf0`/`3f2a8dc`/`deed704` 提交日（2026-10-16 09:50）一致 |
| 用户对「个人品牌用于产品图标」的**豁免决策** | §2 明确记载 2026-10-16 用户决定将该个人品牌 mark 用作产品图标，并引用品牌库 README〈品牌架构〉 | ✓ 引文经 QA 在 `/Users/yifengstudio/Desktop/Active/YifengBranding/README.md` 第 11 行核实存在 |

四条全部属实 → **PASS**。（唯一措辞瑕疵：README §5 把「品牌色像素」定义为 `alpha > 0`，但表中 32px 报 52，而入库文件在 `alpha>0` 下为 58；见 Nit N-5。）

---

## D. 构建集成的 fail-closed 行为（对抗性）— **PASS**

QA 自写独立对抗 harness `.local/qa/appicon/qa_adversarial.py`（`importlib` 载入 `scripts/build_macos_app.py`，**不复用** `tests/unit/test_build_app_icon.py`）：**18/18 PASS，exit 0**。

### D1 不存在路径 → RuntimeError（不是静默跳过）

```
embed_app_icon(res, source=<tmp>/nope.icns)
→ RuntimeError: Missing app icon: .../nope.icns                      ✓
失败后资源目录仍为空 list(res.iterdir()) == []                        ✓
以目录冒充 .icns → RuntimeError: Missing app icon: .../adir.icns      ✓
```

### D2 坏文件 → RuntimeError

| 输入 | 结果 |
| :-- | :-- |
| `b"icns"`（4 字节，<8） | `RuntimeError: Not a valid .icns file (bad header)` ✓ |
| `b"icn"`（3 字节） | 同上 ✓ |
| `b""`（0 字节） | 同上 ✓ |
| `b"icns\x00\x00\x00"`（7 字节） | 同上 ✓ |
| `b"not-an-icns"`（头不是 icns） | 同上 ✓ |
| PNG 头 `\x89PNG\r\n\x1a\n…` | 同上 ✓ |

### D3 合法 icns → 复制成功、返回 `"AppIcon"`、字节一致

```
stem = embed_app_icon(res3, source=native/Resources/AppIcon.icns)
→ stem == "AppIcon" ✓    (res3/"AppIcon.icns").read_bytes() == 原件 ✓
默认源（不传 source）同样等于入库图标 ✓
```

### D4 篡改实验（真实构建路径，端到端）

在 QA checkout 里临时替换 `native/Resources/AppIcon.icns`，跑**真实发布脚本** `scripts/release-macos.sh`（`SUMMIT_ALLOW_DIRTY=1`，因为篡改后 tree 为 dirty 会被 dirty 门先拦下，那样就无法归因到图标门）：

| 场景 | 篡改内容 | `RELEASE_EXIT` | 产出 `.app` | 产出 `.dmg` | 失败原因 |
| :-- | :-- | ---: | :-- | :-- | :-- |
| 1 | `not-an-icns-at-all`（坏头） | **1** | **NO** | **NO** | `RuntimeError: Not a valid .icns file (bad header): .../native/Resources/AppIcon.icns` |
| 2 | `icns`（正确 magic 但仅 4 字节） | **1** | **NO** | （未到） | 同上 |
| 3 | 文件缺失 | **1** | **NO** | （未到） | `RuntimeError: Missing app icon: ...` |

`embed_app_icon` 在 `build()` 中是**无条件调用**（`scripts/build_macos_app.py:280`，不在任何开关/异常吞并之后），因此不存在绕过它的构建路径 → **fail closed，PASS**；未产出无图标的包。

还原与清洁：`git checkout -- native/Resources/AppIcon.icns` → SHA 回到 `f34b3ef6…`，`git status --porcelain` 为空（见文末）。

**补充观察（Nit N-4）**：`embed_app_icon` 只校验「存在 + 长度 ≥8 + 前 4 字节为 `icns`」。QA 探针证实 **`b"icns\x00\x00\x00\x08"`（8 字节垃圾体）与「真实 icns 截断到 4096 字节」都会被接受并拷入包内**。即：门对「缺失 / 坏头」是 fail-closed，对「头合法但内容损坏」不是。

### D5 `create_dmg` 安全属性复核（逐条给出代码位置与判定）

对比基线 `8c882ed:scripts/build_macos_app.py`：

| 原有安全属性 | 新代码位置（`deed704`） | 判定 |
| :-- | :-- | :-- |
| 拒绝覆盖已存在 DMG | `build_macos_app.py:119-120`（`dmg.exists()` → `FileExistsError`），另在 `:196-197` 的 `build()` 入口再拒一次 | **保留 ✓**（且双层） |
| `UDZO` 只读压缩 | `:147` 先 `create -format UDRW` 做可写中间体；`:163` `convert … -format UDZO` 产出最终只读镜像。QA 实测 `hdiutil imageinfo` → `Format: UDZO` | **保留 ✓**（改为两段式，最终产物仍 UDZO） |
| `hdiutil verify` | `:165` `run_hdiutil(["verify", str(staged_dmg)])` | **保留 ✓**（实测 exit 0，`checksum … is VALID`） |
| 只读挂载后校验 app 存在 | `:171` `attach -readonly -nobrowse -mountpoint`；`:180-181` `if not bundled_app.is_dir(): raise` | **保留 ✓** |
| `codesign --verify --deep --strict` | `:182` | **保留 ✓**（实测 exit 0） |
| detach 干净（两个挂载阶段都在 `finally`） | `:157-161`（可写阶段）、`:186-187`（只读阶段） | **保留并加强 ✓** |
| **新增**：挂载内 `.VolumeIcon.icns` 必须存在 | `:183-184` `if not (mount / ".VolumeIcon.icns").is_file(): raise RuntimeError("Mounted DMG is missing .VolumeIcon.icns")` | **新增 fail-closed ✓** |
| **新增**：源卷图标缺失即失败 | `:123-124` `if not volume_icon.is_file(): raise RuntimeError("Missing DMG volume icon: …")` | **新增 fail-closed ✓** |

**未发现原有检查被删除或放宽（无「门变软」）→ PASS。**

### D6 `run_hdiutil` 与 `resolve_setfile`

- `run_hdiutil`（`:39-50`）实测：对不存在的镜像调用 → `RuntimeError: hdiutil exited 1: hdiutil verify /definitely/not/here.dmg` + **原始 stderr 逐行带出**（`hdiutil: verify: unable to recognize … as a disk image` / `hdiutil: verify failed - 无此文件或目录`）。命令与 stderr 都原样带出 → **可识别 `hdiutil: create failed - Resource busy` 类抖动，PASS**。
- `resolve_setfile`（`:53-69`）三条失败路径 QA 用 monkeypatch 独立触发，全部明确报错而非静默跳过：
  - `xcrun` 不存在（`FileNotFoundError`）→ `RuntimeError: … xcrun is not available; install the Xcode command line tools` ✓
  - `xcrun -f SetFile` 失败（`CalledProcessError`）→ `RuntimeError: … `xcrun -f SetFile` failed; install the Xcode command line tools` ✓
  - 返回空路径 → `RuntimeError: `xcrun -f SetFile` returned an empty path` ✓
  - 本机成功路径：`/Applications/Xcode.app/Contents/Developer/usr/bin/SetFile`（存在）✓

---

## E. 真实产物 — **PASS（DMG SHA 除外，见 N-1）**

QA 在 QA checkout 中自建一次（此前无产物）：

```
uv sync --locked --group dev --group build   → exit 0
npm --prefix web ci                          → exit 0
scripts/release-macos.sh \
  "$PWD/.local/dev/qa-appicon/artifacts/SummitEverything Internal.app" \
  "$PWD/.local/dev/qa-appicon/artifacts/SummitEverything-Internal.dmg"
RELEASE_EXIT=0
构建日志含：Embedded app icon AppIcon.icns as AppIcon
```

| 检查项 | 命令 | 实测 | 判定 |
| :-- | :-- | :-- | :-- |
| `CFBundleIconFile` | `plutil -extract CFBundleIconFile raw <app>/Contents/Info.plist` | `AppIcon`（exit 0） | **PASS** |
| 包内图标 == 仓库图标 | `sha256` + `cmp` | 两侧均 `f34b3ef6…6c61b00`，`cmp` exit 0 | **PASS** |
| App 签名 | `codesign --verify --deep --strict <app>` | exit 0 | **PASS** |
| DMG 格式 | `hdiutil imageinfo <dmg>` | `Format: UDZO` | **PASS** |
| DMG 校验 | `hdiutil verify <dmg>` | exit 0，`checksum … is VALID` | **PASS** |
| 卷根含 `.VolumeIcon.icns` | 只读挂载 + `ls -la <mount>` | 存在，175404 字节，`sha256 = f34b3ef6…` == 仓库 `VolumeIcon.icns`，`cmp` exit 0 | **PASS** |
| 卷「自定义图标」位 | `xcrun -f GetFileInfo` → `GetFileInfo -a <mount>` | `avbstClinmedz` —— **含大写 `C`** | **PASS** |
| 卷内 app 签名 | `codesign --verify --deep --strict <mount>/SummitEverything Internal.app` | exit 0 | **PASS** |
| detach | `hdiutil detach <mount>` | exit 0，`"disk5" ejected.`，挂载点已移除 | **PASS** |
| 打包 smoke | `SUMMIT_APP="<app>" uv run python scripts/smoke_packaged_app.py` | `PASS: onedir backend starts with empty PATH; …`，exit 0 | **PASS** |
| **DMG SHA-256** | `shasum -a 256 <dmg>` | **`2eb89b3742588bf2c1d2dcba56f5c927aab288ea26e032f6d5d9a62c638f12d4`** | **与声称不符，见 N-1** |

包内 `build-info.json` 实测：`source_sha=deed704b16f2e7adee56e18136b4290d713912fa`、`dirty=false`、`frontend_sha256=784ae1ee176a851e1f189f67d1dc84fa239bcff607e94e883e845d98fe28dbf0`、`build_id=20261016T020900Z-784ae1ee176a` —— 源码身份与前端指纹均正确。

---

## F. 边界与凭据 — **PASS**

1. **无 token / 密钥 / 真实业务数据**（区间 `e8e1dba..deed704`，注意本轮 QA 的区间是 `8c882ed..deed704`）。
   - 文本面：对全部新增行做 `api[_-]?key|secret|token|password|bearer|sk-…|ghp_|AKIA|BEGIN … PRIVATE KEY|feishu|app_id|app_secret|keychain|notar` 扫描，命中的全部是设计 token 语义的 `TOKENS`（`assets/branding/make-appicon.mjs` 的调色板常量与 README 的「深色 token 映射表」），**无一条凭据形状命中**。
   - 二进制面（`.icns` 两个文件，无法用文本扫描）：QA 用三种互补手段检查 —— ① `strings -n 20` 只得到 4 条，全部是 `iconutil` 写入的标准 `info` 块 plist 键（`NSDictionary` / `assetcatalog-reference` 等）；② 逐块解析确认块类型仅 `ic04–ic14` + `info`（全部为标准 PNG 载荷型，无自定义/附块）；③ 确认两个文件字节相同且等于 CI 可复算的生成物。**无嵌入文本、无用户资料。**
2. **只 vendor 了明确需要的两个 SVG**：`8c882ed..deed704` 在 `assets/` 下新增的仅 `favicon.svg`、`logo-mark.svg`、`README.md`、`make-appicon.mjs`。品牌库的 `variables.css`、docs、patterns、showcase、`assets/tools/contour-gen.py` 等**一律未进入本仓库**（README 只以路径文字引用品牌库色值来源，未复制文件）。**PASS**。
3. **未触碰真实 provider / 飞书 / Keychain / 用户真实资料 / 已安装 App / 公证**：
   - `.github/workflows` 在本区间**零改动**；
   - 全区间 diff 中无 `notar`/`staple`/`feishu`/`keychain`/`security find-*` 命中；签名仍是本地 ad-hoc（`codesign --force --deep --sign -`），**未做 Apple 公证/装订**；
   - 构建产物只写入 `.local/dev/...`（gitignored），未安装、未替换任何已安装 App。
   - **一处需登记的事实**（观察项，非缺陷）：vendored 的 `logo-mark.svg` 其 `aria-label` 与注释含用户本人姓名（`罗艺峰`）。这是品牌 mark 原件的组成部分，且用户已亲自豁免「个人品牌 mark 用于产品图标」，故属授权范围；记录在此以备边界追溯。

---

## 与实现者声明不符之处

### N-1（与声明不符）DMG SHA-256 不可复现

- 实现者声称：`390d09dd0aba84e77e32dc491652e8285e0ba8c9e2ef8bec64097f49c48f92ab`
- QA 实测：`2eb89b3742588bf2c1d2dcba56f5c927aab288ea26e032f6d5d9a62c638f12d4`
- **是否属可复现性差异：是，且已被 QA 独立证明。** 两条证据：
  1. 包内 `build-info.json` 的 `build_id` 由 `datetime.now(UTC)` 生成（`build_macos_app.py:230`），**每次构建必然不同**，因此同一 SHA 的 DMG 永远不可能字节复现；
  2. QA 用**完全相同的 app 字节**再调一次 `create_dmg` 产出第二个 DMG：`2eb89b37…` vs `6feaf73a…` —— **两次构建即使输入 app 完全一致也字节不同**（UDIF/HFS+ 时间戳），证明差异不是本轮源码或图标内容导致。
- 结论：实现者声称的那个 SHA 是**某一次构建实例的指纹，不是可复现常量，也无法追溯**。不判为实现缺陷（图标/DMG 的实质属性与内容均 PASS），但该声明**不可作为验收依据**，应改为「构建实例指纹 + 内容摘要」或干脆不写入交接。

### N-2（与声明不符）`.icns` 内含**两个互不相同**的 32px representation

- 声明口径是「同一 profile 下 16/32px 用 `favicon.svg` 小变体 + 0.90px 最小描边」，隐含 32px 只有一种渲染。实测 `ic11`（`icon_16x16@2x.png`）与 `ic05`（`icon_32x32.png`）**内容不同**：
  - alpha 通道**逐字节相同（0 差异）** → 几何完全一致；
  - 但 80 个像素的 RGB 不同，**全部位于 `alpha<255` 的半透明像素**，最大通道差 **213**；
  - 其中 4 个是板圆角处的**纯白半透明像素** `(255,255,255, alpha≈20)`，而 `ic11` 同位置是暗色 `(26,26,26, alpha=20)`；其余为 `(198,198,248,36)`、`(130,148,148,55)` 一类偏亮值。
  - 全部 10 个 representation 中，**只有 `icon_32x32.png` 存在白色半透明像素**（4 个，最大 alpha 21），其余 9 个为 0。
- 这是「在白色/非透明画布上合成」的典型痕迹，说明 `icon_32x32.png` 与其余 9 档走的不是同一条渲染/保存路径。
- 影响评估：`alpha ≤ 21/255 ≈ 8%`，在深色或浅色背景上均不可辨，**不构成产品可见缺陷**；但它同时是 README §5 中 32px 在 `alpha>0` 口径下计到 58 而非 52 的原因（QA 探针已定位到那 6 个像素）。

### N-3（Nit）`icon_16x16.png` 有 44 个半透明像素色值不可独立复现

alpha 通道逐字节相同（0 差异）、`alpha=255` 像素零差异；44 个 RGB 差异**全部**在 `alpha<255` 像素上，最大通道差 93。与 N-2 同类（半透明像素的存储色路径差异），不改变几何、墨色计数与四角透明结论。

### 其余 Nit

- **N-4** `embed_app_icon` 只做「存在 + ≥8 字节 + 前 4 字节 `icns`」校验。QA 探针证明 `b"icns\x00\x00\x00\x08"` 与「截断的真实 icns」都会被接受并装箱 → 对「头合法但体损坏」不是 fail-closed。建议加总长度/块结构校验（或直接调用 `iconutil` 验证）。
- **N-5** README §5 把「品牌色像素」定义为 `alpha > 0`，但表格 32px 列报 52，而入库 `icon_32x32.png` 在 `alpha>0` 口径下实测 58（`alpha>140` 口径才是 52）。定义与数字口径不一致，建议在 README 明确写成 `alpha > 140`，或把 32px 一行同时给出两个口径。
- **N-6** README §3/§4 的 `cover=0.6796` 是展示值；真实几何是符号宽度取整为 **560px**（`round(824×0.6796)`）。按字面 `824×0.6796=559.9904` 无法复现入库字节（1024 档差 1359 像素）。建议文档补一句「符号宽度 = `round(824 × cover)`」。
- **N-7** 生成器 `make-appicon.mjs` 与两个 SVG 入库，但 `.icns` 是**提交入库的生成物**；CI 在 PR #22 中**不重跑生成、不校验 `.icns` 与 SVG 的一致性**（README §7 自述「CI 不依赖 Playwright」）。即：SVG 或 profile 参数日后漂移时，CI 不会发现入库 `.icns` 已过期。本轮 `assets/branding/` 尚未加入 `tests/` 触发路径以外的守卫，建议后续加一个「`--check-only` 或产物哈希比对」的轻量门。（**本轮未改变任何既有门，故不判 FAIL。**）

---

## 限制与未测项（诚实声明）

1. **本机 wall-clock 为 2026-10-16**，`build-info.json` 的 `build_id=20261016T020900Z-784ae1ee176a` 与之一致；QA 无法独立校验实现者所称「用户 2026-10-16 决定」的日期本身，只能核实该日期在 README、提交时间与产物元数据三处自洽。
2. C5 的 0 差异是在**本机同一 Chromium 构建**上达成的。QA 用 `iconutil` 无损往返实验排除了重编码因素，但未验证在**另一台机器 / 另一版 Chromium** 上是否仍为 0 差异。
3. D4 三个篡改场景均以 `SUMMIT_ALLOW_DIRTY=1` 运行（因为篡改会让 tree 变 dirty，dirty 门会先于图标门拦下，从而无法归因）。因此 D4 证明的是「图标门本身 fail-closed」，**不覆盖**「dirty 门 + 图标门」的联合顺序。
4. E 的 DMG 只验证了 **ad-hoc 签名 + 本地挂载**，未做公证、未在第二台机器上挂载、未做安装后首启。
5. 未审 `assets/branding/make-appicon.mjs` 的**全部代码路径**（在库中未被执行）；QA 只独立复算了**产物**与 README 中的对照数字。`legible` / `strict` 两个备选 profile 未入库，其产物**未验收**。
6. 未做人工视觉判读（Finder/Dock/菜单栏实际观感、深浅色模式下的观感）。

## 本 PASS 明确不覆盖

- **产品面**：本轮 `web/`、`src/`、`pyproject.toml`、`uv.lock`、`native/Tests` 零改动，A 组只证明「既有门仍为 699 passed / 指纹未漂移」，**不构成对这些模块本轮行为的验收**（本轮没有它们的改动可验收）。
- **视觉/人因**：图标在真实 Finder、Dock、Launchpad、深浅色菜单栏、Retina/非 Retina 下的观感；「品牌可识别性」这一主观判断。
- **分发与安装**：公证（notarization）/装订（stapling）/Gatekeeper 首次放行、真实安装、卸载、首启向导。
- **真实外部面**：真实 provider 调用、真实飞书、Keychain、用户真实资料/材料、真实凭据。
- **可复现性**：DMG 与 `.icns` 的字节级跨机可复现性；实现者声称的 DMG SHA 的可追溯性（已判为不可复现，见 N-1）。
- **平台**：仅 arm64 macOS 本机；Intel、其他 macOS 版本、Windows 未测。
- **生成器全量正确性**：`make-appicon.mjs` 的非默认 profile 与非默认代码路径。
- **CI 内部日志**：QA 只独立核了 run `38838074701` 的 `conclusion` / `headSha` / workflow 名与 job 时长，**未逐行审阅 CI 内部日志**（CI 的 native/DMG 步骤内容未被独立复核）。

---

## 清洁性收尾（QA 自证）

- 篡改实验后：`git checkout -- native/Resources/AppIcon.icns`；图标 SHA 回到 `f34b3ef6e86e92d92f036dfef2adffaee44a429aec0f7898adac4403a6c61b00`。
- `git status --porcelain` → 只剩本报告（`?? docs/quality/reports/2026-10-16-APP-ICON-QA.md`）这一条**未跟踪新增**，**无任何 tracked 改动**；三个篡改场景结束后 QA 均实测确认图标已还原。
- QA 未改产品源码、未改任何已有 tracked 测试；本轮新增的入库文件只有本报告与 `docs/quality/reports/evidence/2026-10-16-appicon-qa/` 下的脱敏证据。
- QA worktree 已按纪律 `git worktree remove --force` + `git worktree prune` 清理，`git worktree list` 只剩 2 条（见回报）。
