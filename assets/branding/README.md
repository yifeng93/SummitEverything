# App 图标资产（品牌 mark 入库）

本目录把**个人品牌 mark** 接进 SummitEverything 的 macOS 交付面：App 图标与 DMG 卷图标。
范围仅限 **macOS App 图标 + DMG 卷图标**——本轮不动 Web，前端指纹保持不变。

---

## 1. 来源与完整性

逐字节复制自个人品牌资产库，未做任何编辑：

| 本目录文件 | 来源绝对路径 | 取用日期 | SHA-256 |
| :-- | :-- | :-- | :-- |
| `logo-mark.svg` | `/Users/yifengstudio/Desktop/Active/YifengBranding/assets/logo/logo-mark.svg` | 2026-10-16 | `e389f6ba40b9473858fafda85c49668f119bb88e0a2840d503568e0f69fd4dfb` |
| `favicon.svg` | `/Users/yifengstudio/Desktop/Active/YifengBranding/assets/logo/favicon.svg` | 2026-10-16 | `2ae04fc3cac92c5c07a3e5a0ea298654f8bb1719d3d825f6bf8635bb01a78ab3` |

复核方式：

```sh
shasum -a 256 assets/branding/logo-mark.svg assets/branding/favicon.svg
```

调色板取自同一品牌库的唯一色值来源 `assets/variables.css`。

## 2. 用户决策记录：个人品牌 mark 用于产品图标

品牌库 README 明确写着：

> **这是个人品牌，不是项目品牌。** 与「在场·见地」等项目品牌**明确区隔、各自独立**。
> ——`/Users/yifengstudio/Desktop/Active/YifengBranding/README.md`，〈品牌架构〉一节

「个人品牌与项目品牌各自独立」这条边界**由用户本人豁免**：2026-10-16，用户明确决定把这个
**个人品牌 mark** 用作 SummitEverything（产品）的 macOS App 图标与 DMG 卷图标。这是用户亲自
批准的例外，不是执行者推断；边界本身未被修改，仅在本项目的图标用途上被豁免。

同一次决策还确定了：**深色底 + 浅色等高线**（取 `.deep-mode` 深色块），范围限定
**App 图标 + DMG 卷图标**，本轮不动 Web。

## 3. 深色 token 映射表

全部取自品牌库 `assets/variables.css` 的 `.deep-mode` 块，**不得自创色值**：

| 用途 | 色值 | 来源 token |
| :-- | :-- | :-- |
| 底板（Apple 图标网格圆角方） | `#1C2124` | `--color-paper` (deep) |
| 外/中圈 | `#8FA0A4` | `--color-primary` (deep) |
| 内圈（最重） | `#B4C0C3` | `--color-primary-deep` (deep) |
| 顶点方块 | `#F4F3F0` | `--color-ink` (deep) |

画布 1024×1024、透明底；底板为 Apple 的 macOS 图标网格
`<rect x="100" y="100" width="824" height="824" rx="185.4" fill="#1C2124"/>`，
**四角保持透明**（`alpha = 0`）。

符号本身不重画：`logo-mark.svg`（viewBox `0 0 100 84`，3 圈 + 顶点方块）与
`favicon.svg`（viewBox `0 0 67 67`，2 圈 + 顶点方块）的内层 markup 被**原样引用**，
只通过 `<style>` 换色并整体缩放居中。

## 4. Profile：尺寸 → 配置

尺寸→配置做成**具名 profile**，可一键切换；`make-appicon.mjs` 里三档全部保留。

```js
faithful:  small@<=32 {variant:'small', box:67,  cover:0.7779, minStroke:0.90}
           full@>=64  {variant:'full',  box:100, cover:0.6796, minStroke:0}
strict:    small@<=32 {variant:'small', box:67,  cover:0.7779, minStroke:0}
           full@>=64  {variant:'full',  box:100, cover:0.6796, minStroke:0}
legible:   small@<=32 {variant:'small', box:67,  cover:0.72, minStroke:1.25}
           small@<=64 {variant:'small', box:67,  cover:0.66, minStroke:1.00}
           full@<=128 {variant:'full',  box:100, cover:0.62, minStroke:0.85}
           full@>=256 {variant:'full',  box:100, cover:0.58, minStroke:0}
```

`cover` = 符号宽度占底板 824 的比例，符号居中。

| profile | 说明 | 状态 |
| :-- | :-- | :-- |
| **`faithful`** | **默认（用户 2026-10-16 选定）**。≥64px 与品牌原件**逐像素一致**；仅 16/32px 施加 0.90px 最小描边。 | ★ 入库 `.icns` 用此档 |
| `strict` | 完全忠实，不做任何加粗。16px 实测仅 5 个品牌色像素 ≈ 不可见。 | 备选，未选 |
| `legible` | 最初建议的 T2 方案，全档位加粗。 | 备选，未选 |

### 为什么 16/32px 要偏离原始描边

**这是为小尺寸可读性对原始 SVG 描边的有意偏离。** 品牌原件的描边相对 viewBox 很细：
`logo-mark.svg` 外圈 **1.5%**（1.5/100），`favicon.svg` 外圈 3.9%（2.6/67）。以
`logo-mark.svg` 的 full 档在 16px 折算：`1.5 × (824 × 0.6796 / 100) × (16/1024) ≈`
**0.13 物理像素**，渲染后直接消失。实测 `strict`（不加粗）在 16px 只剩
**5 个品牌色像素**，最重的内圈完全无法成形——等于没有图标。

因此 `faithful` 在 16/32px 施加 **0.90px** 最小物理描边：
对每个 `<path stroke-width="w">`，其物理像素 = `w × scale × (S/1024)`，
其中 `scale = (824 × cover) / viewBox宽`；低于 0.90px 时把 `w` 乘以 `目标/实际`。
**≥64px 不做任何处理**——该区间与品牌原件逐像素一致（已实测）。

## 5. 墨色像素下限（自检阈值）

自检把「品牌色像素」定义为：**`alpha > 0` 且该像素颜色与
`#8FA0A4` / `#B4C0C3` / `#F4F3F0` 三者之一的 Chebyshev（各通道最大）距离 ≤ 40**。
阈值取实测值的约 80%，用来兜住「渲染空白」或「描边过细」的静默劣化。

| size | `faithful`（默认）实测 | 下限 | `strict` 实测 | 下限 | `legible` 下限 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 16 | 22 | 17 | 5 | 4 | 25 |
| 32 | 52 | 41 | 40 | 32 | 55 |
| 64 | 43 | 34 | 43 | 34 | 140 |
| 128 | 414 | 330 | 414 | 330 | 260 |
| 256 | 1901 | 1520 | 1901 | 1520 | 1000 |
| 512 | 7987 | 6390 | 7987 | 6390 | 4500 |
| 1024 | 32668 | 26130 | 32668 | 26130 | 18000 |

自检同时断言：四角 `alpha = 0`；底板色存在；≥32px 四种 token 色全部出现。
（16px 只要求底板 + ≥2 种品牌色：`strict` 下最重的内圈在 16px 物理上无法成形。）

## 6. 重新生成

```sh
npm --prefix web ci                       # Playwright 来自仓库 web/node_modules
node assets/branding/make-appicon.mjs                    # faithful（默认）+ 自检
node assets/branding/make-appicon.mjs --profile legible  # 指定 profile
node assets/branding/make-appicon.mjs --check-only       # 只校验已入库 .icns
```

生成器会用 Playwright（Chromium）渲染各尺寸 PNG，再用 `iconutil -c icns` 打包，
输出 `native/Resources/AppIcon.icns` 与 `native/Resources/VolumeIcon.icns`（两者字节相同）。
自检用 Pillow 做像素统计，需要一个能 `import PIL` 的解释器（系统 `python3` 自带 11.3）。

三个 profile 的对照预览 PNG 一律写到 `/tmp/appicon-preview/{strict,faithful,legible}/icon-<size>.png`，
方便人工比对；**只有默认 profile 的 `.icns` 入库**。

## 7. 入库的生成物与 CI 边界

`native/Resources/AppIcon.icns`、`native/Resources/VolumeIcon.icns` 是**提交入库的生成物**，
源头是本目录的两个 SVG + `make-appicon.mjs` + 上表的 profile 配置。

**CI 不依赖 Playwright**：`.icns` 已入库，构建（`scripts/build_macos_app.py`）只做拷贝，
不渲染、不装浏览器。需要校验时用 `--check-only`（只调用 `iconutil` 与 Pillow，不启动浏览器）。

未采用 asset catalog / `actool`：本轮范围是 App + DMG 图标，保持简单。
