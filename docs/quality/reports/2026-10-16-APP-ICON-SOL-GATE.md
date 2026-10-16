# App 图标 + DMG 卷图标 · Sol 门判断（PR #22，2026-10-16）

- **对象**：分支 `codex/app-icon-20261016`，PR [#22](https://github.com/yifeng93/SummitEverything/pull/22)，base `main` = `8c882ed`。
- **代码受测 tip**：`b77b81486954b300b5b92d4d2106506b7a4ac887`（本文件是其后唯一的 docs 提交）。
- **独立 QA**：[2026-10-16-APP-ICON-QA.md](2026-10-16-APP-ICON-QA.md)，受测 `deed704b16f2e7adee56e18136b4290d713912fa`（QA checkout 已删除）。
- **用户决策（2026-10-16）**：使用其个人品牌 mark（`YifengBranding/assets/logo/logo-mark.svg`「峰·等高线」）；**深色底 + 浅色等高线**；范围 = **App 图标 + DMG 卷图标**（不含 web favicon）；保真档 = **T3**（≥64px 与品牌原件逐像素一致，仅 16/32px 施加最小描边）。

## 判定

| 范围 | 判定 |
|---|---|
| 品牌素材入库（provenance） | **PASS**（两个 SVG 与品牌库原件逐字节相同；记录来源绝对路径、日期、SHA-256；用户对「个人品牌用于产品图标」的豁免已入档） |
| 配色忠于品牌 token | **PASS**（底板 `#1C2124`、圈 `#8FA0A4`/`#B4C0C3`、顶点 `#F4F3F0`，全部取自 `variables.css` 的 `.deep-mode`，无自创色值） |
| 保真档实现 | **PASS**（入库 `.icns` 的 7 档墨色像素 = 22/52/43/414/1901/7987/32668，与 T3 实测逐档一致） |
| macOS App 图标接入 | **PASS**（包内 `Contents/Resources/AppIcon.icns` 与仓库字节相同；`CFBundleIconFile=AppIcon`） |
| DMG 卷图标 | **PASS**（只读挂载内 `.VolumeIcon.icns` 存在且与仓库字节相同；卷属性 `avbstClinmedz` 含 `C`） |
| 打包脚本 fail-closed | **PASS**（icns 块表校验；Sol 独立跑 8/8 对抗输入全 `RuntimeError` 且失败后资源目录为空；QA 独立跑 14/14） |
| 不回归产品面 | **PASS**（`git diff 8c882ed <tip> -- web src pyproject.toml uv.lock` 为空；前端指纹 `784ae1ee…28dbf0` 未变） |
| 自动检查 | **PASS**（pytest **712**、vitest **222 / 26 files**、`test:e2e` **2**、`test:e2e:integration` **1**、typecheck/lint（2 条既存 warning）/build/ruff check/ruff format/mypy 全 exit 0） |
| 真实远端 CI | **PASS**（run [`38838074701`](https://github.com/yifeng93/SummitEverything/actions/runs/38838074701) @ `deed704`、run [`38840793621`](https://github.com/yifeng93/SummitEverything/actions/runs/38840793621) @ `b77b814`，均 completed / success，13 步全 success） |
| **本轮 —— 限「App 图标 + DMG 卷图标」范围** | **PASS，可合入（合并待用户批准）** |
| 人工视觉判读 / 公证 / 真实安装 / 真实服务 | **NOT_RUN**（各自独立门） |

## QA 两条「与声明不符」的裁决

### ① DMG SHA-256 不可复现 —— **裁决：QA 正确，Sol 先前表述有误**

QA 实测自己构建的 DMG 得 `2eb89b37…`，用**完全相同的 app 字节**再建一次得 `6feaf73a…`，与实现者声称的 `390d09dd…` 三者互不相同。根因是 `build-info.json` 的 `build_id` 含 UTC 时间戳，**每次构建必变**（这是既有设计，非本轮引入）。

**结论**：候选 DMG 的 SHA-256 是**构建实例指纹**，不是可复现身份，**不得作为验收依据或可追溯锚点**。Sol 先前把它当产物身份报给用户，属表述错误，在此更正。可追溯身份应使用 `source_sha` + `dirty` + `frontend_sha256` + `.app` 目录树摘要。

### ② `.icns` 内两个 32px representation 不一致 —— **裁决：不是缺陷；QA 的测量方法量到了 iconutil 的解码器**

QA 观察到 `iconutil -c iconset` 解出的 `icon_16x16@2x.png` 与 `icon_32x32.png` 有 80 个像素 RGB 不同、且后者有 4 个纯白半透明像素。Sol 做了**容器层与像素层两级独立复核**：

```
文件 175404 B, 头声明总长 175404 B, 相符=True
块数=11  恰好铺满=True
  ic12 64px  PNG      ic07 128px PNG     ic13 256px PNG    ic08 256px PNG
  ic04 16px  ARGB/RLE                   ic05 32px  ARGB/RLE
  ic14 512px PNG      ic09 512px PNG     ic10 1024px PNG   ic11 32px@2x PNG
  info
```

- 两个 32px 表示用的是**不同容器编码**（`ic04`/`ic05` 为 ARGB/RLE，`ic11` 为 PNG）——这是 `.icns` 的规范做法。
- 逐像素比对：alpha 差异 **0**；RGB 差异 80，`clamp(round(c×255/α))` 公式命中 **66/80**，其余 14 个**全部只差 ±1 单通道**，与 8-bit 预乘/反预乘往返的舍入损失一致，**0 例外**。
- 纯白半透明像素：渲染侧 **0** 个、ARGB 解码侧 **4** 个 → 由解码步骤产生，**不在 `.icns` 内**。

**结论**：`.icns` 内像素正确；差异是 `iconutil -c iconset` 对 ARGB 载荷做有损往返的结果。**因此「用 iconutil 解回再逐字节 `cmp`」不是本产物的有效验收方法**——这一点已写入 `assets/branding/README.md` §8。实现者的反驳成立，QA 的诊断（重复渲染）不成立。

## 已知缺口与记录项（不阻塞本次合入）

| 编号 | 级别 | 内容 | 处置 |
|---|---|---|---|
| G-1 | 缺口 | **CI 不重新生成 `.icns`，也不校验 `.icns` 与两个 SVG 的一致性**。若有人改了 SVG 而忘记重新生成，现有检查不会发现。 | 当前防线：`.icns` 入库 + 单元测试断言其存在/合法/两文件一致。是否加 CI 门（需在 CI 安装 Chromium，约 +1–2 分钟）留给用户决定。 |
| G-2 | 记录 | DMG SHA-256 不可复现（见上①）。 | 已在 QA 报告与本文记录；后续文档不得把 DMG SHA 当可追溯身份。 |
| G-3 | Nit | `iconutil -c iconset` 对 16/32px 的 ARGB 载荷是有损往返。 | 已写入 `assets/branding/README.md`；后续任何人不得用该往返做字节级验收。 |
| G-4 | Nit | 16px 的 44 个次像素 RGB 差异（alpha 全同）。 | 产品不可见；同 G-3 机制。 |
| G-5 | 记录 | 品牌库 README 声明「个人品牌与项目品牌各自独立」，本轮由用户本人豁免。 | 豁免决策已写入 `assets/branding/README.md`。 |

## 证据口径决定

- **`--check` 的墨色指标**统一为 `alpha > 140` 且与三个品牌色之一 Chebyshev ≤ 40；`alpha > 0` 口径下 32px 会得 58 而非 52，README 已注明，避免误判。
- **`cover` 语义**统一为「符号宽度 = `round(824 × cover)` 像素」；T3 的 full 档为 `round(824 × 0.6796) = 560`。
- QA 的 `iconutil` 往返 `cmp` 结论**不作为**缺陷判定依据（见②）。

## 合入判断

- 本轮为**新增能力**（app 与 DMG 有图标），不改产品面、不动 `web/**`、不降低任何既有验收门；全部硬检查与真实 CI 均绿。
- **Sol 判定：本轮可合入 main。**
- **合并动作仍需用户明确批准。Sol 未 merge，也不会自行 merge。**

## 本 PASS 明确不覆盖

Finder / Dock / 菜单栏的**人工视觉判读**（Sol 当前执行环境的模型不支持图像输入，只做了像素统计、ASCII 降采样判读与容器层解析）；Developer ID 签名、公证、Gatekeeper 接受与真实用户安装；真实 provider / 飞书 / Keychain / 真实业务材料；**跨机与跨次构建的字节可复现性**（含 DMG SHA 可追溯性）；非 arm64 平台；`make-appicon.mjs` 的 `strict` / `legible` 备选 profile 的产物；CI 内部日志的逐行审阅。
