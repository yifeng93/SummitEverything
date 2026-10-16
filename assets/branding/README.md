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

`cover` = 符号宽度占底板 824 的比例，符号居中。生成器把 `scale = (824 × cover) / box` 写进 SVG 时
会四舍五入到 3 位小数（`scale.toFixed(3)`），所以**实际符号宽度是 `round(824 × cover)` 像素**：
`faithful` 的 full 档 `824 × 0.6796 = 559.9904` → `scale = 5.599904` → `toFixed(3) = 5.600`
→ **真实几何是符号宽度 560px**。按字面 559.9904（`scale = 5.599904`，不取整）渲染无法复现入库字节
（QA 实测 1024 档 1359 个差异像素、最大 Δ39）；取整到 560px 后差异为 0。

| profile | 说明 | 状态 |
| :-- | :-- | :-- |
| **`faithful`** | **默认（用户 2026-10-16 选定）**。≥64px 与品牌原件**逐像素一致**；仅 16/32px 施加 0.90px 最小描边。 | ★ 入库 `.icns` 用此档 |
| `strict` | 完全忠实，不做任何加粗。16px 实测仅 5 个品牌色像素 ≈ 不可见。 | 备选，未选 |
| `legible` | 最初建议的 T2 方案，全档位加粗。 | 备选，未选 |

### 为什么 16/32px 要偏离原始描边

**这是为小尺寸可读性对原始 SVG 描边的有意偏离。** 品牌原件的描边相对 viewBox 很细：
`logo-mark.svg` 外圈 **1.5%**（1.5/100），`favicon.svg` 外圈 3.9%（2.6/67）。以
`logo-mark.svg` 的 full 档在 16px 折算：`1.5 × (560 / 100) × (16/1024) = 1.5 × 5.6 × 0.015625 ≈`
**0.13 物理像素**（560 = `round(824 × 0.6796)`），渲染后直接消失。实测 `strict`（不加粗）在 16px 只剩
**5 个品牌色像素**，最重的内圈完全无法成形——等于没有图标。

因此 `faithful` 在 16/32px 施加 **0.90px** 最小物理描边：
对每个 `<path stroke-width="w">`，其物理像素 = `w × scale × (S/1024)`，
其中 `scale = (824 × cover) / viewBox宽`（再 `toFixed(3)`）；低于 0.90px 时把 `w` 乘以 `目标/实际`。
**≥64px 不做任何处理**——该区间与品牌原件逐像素一致（已实测）。

## 5. 墨色像素下限（自检阈值）

自检把「品牌色像素」定义为：**`alpha > 140` 且该像素颜色与
`#8FA0A4` / `#B4C0C3` / `#F4F3F0` 三者之一的 Chebyshev（各通道最大）距离 ≤ 40**
（生成器里的 `INK_ALPHA_FLOOR = 140`、`COLOUR_TOLERANCE = 40`，与此处口径一致）。
阈值取实测值的约 80%，用来兜住「渲染空白」或「描边过细」的静默劣化。

下表数字即按该口径实测（2026-10-16 独立 QA 用自写脚本复算，逐档相同）。

> 口径提示：若改用 `alpha > 0`，`iconutil -c iconset` **解出的** `icon_32x32.png` 会得到
> **58** 而非 52（渲染稿本身两种口径都是 52）。那 6 个多出来的像素是 `iconutil` 重新解码
> `ic05` 的 `ARGB` 载荷时把半透明像素提亮造成的，见 §8。

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
node assets/branding/make-appicon.mjs                    # faithful（默认）+ 自检 + 重新打包
node assets/branding/make-appicon.mjs --profile legible  # 指定 profile
node assets/branding/make-appicon.mjs --check            # 只校验已入库 .icns（不启动浏览器）
node assets/branding/make-appicon.mjs --check-only       # 与 --check 相同
```

生成器用 Playwright（Chromium）**每个不同像素尺寸只渲染一次**（16/32/64/128/256/512/1024 共 7 张），
再把同一张 PNG 复制成所有需要的 iconset 文件名（32 → `icon_16x16@2x.png` + `icon_32x32.png`；
256 → `icon_128x128@2x.png` + `icon_256x256.png`；512 → `icon_256x256@2x.png` + `icon_512x512.png`），
复制后用 `cmp` 断言同尺寸文件名之间逐字节相同，然后才 `iconutil -c icns` 打包，
输出 `native/Resources/AppIcon.icns` 与 `native/Resources/VolumeIcon.icns`（两者字节相同）。
渲染用透明底（`omitBackground: true` + `background: transparent`），四角 `alpha = 0`。

`--check`（等同 `--check-only`）不启动浏览器，依次断言：块表合法且含 10 个 representation、
两个入库文件逐字节相同、容器内共享像素尺寸的块**逐像素相同**、喂给 `iconutil` 的 iconset 同尺寸
文件名逐字节相同、各档像素下限，并如实打印 `iconutil` 解回时的重编码差异（见 §8）。

自检用 Pillow 做像素统计，需要一个能 `import PIL` 的解释器（本机系统 `python3` 自带 11.3）。

三个 profile 的对照预览 PNG 一律写到 `/tmp/appicon-preview/{strict,faithful,legible}/icon-<size>.png`，
方便人工比对；**只有默认 profile 的 `.icns` 入库**。

## 7. 入库的生成物与 CI 边界

`native/Resources/AppIcon.icns`、`native/Resources/VolumeIcon.icns` 是**提交入库的生成物**，
源头是本目录的两个 SVG + `make-appicon.mjs` + 上表的 profile 配置。

| 文件 | 字节 | SHA-256 |
| :-- | ---: | :-- |
| `native/Resources/AppIcon.icns` | 175404 | `f34b3ef6e86e92d92f036dfef2adffaee44a429aec0f7898adac4403a6c61b00` |
| `native/Resources/VolumeIcon.icns` | 175404 | 同上（`cmp` 逐字节相同，是 `copyFileSync` 的副本） |

该 SHA-256 由 2026-10-16 修复轮重新生成后实测：**与修复前逐字节相同**。生成是确定性的
（每个像素尺寸只渲染一次 → 同一份 iconset 字节 → `iconutil` 产出同一份 `.icns`），本轮的
「同尺寸只渲染一次」修复没有改变产物字节，只把该性质变成 `--check` 的硬断言。

**CI 不依赖 Playwright**：`.icns` 已入库，构建（`scripts/build_macos_app.py`）只做拷贝，
不渲染、不装浏览器。构建侧对 `.icns` 做 fail-closed 校验（头 + 块表 + 总长度 + 无越界/残留），
缺文件、坏头、截断、长度不符都直接失败，不会产出无图标或坏图标的包。
需要校验生成物本身时用 `--check`（只调用 `iconutil` 与 Pillow，不启动浏览器）。

未采用 asset catalog / `actool`：本轮范围是 App + DMG 图标，保持简单。

## 8. 已知缺口（2026-10-16 QA）

独立 QA（`docs/quality/reports/2026-10-16-APP-ICON-QA.md`，固定 SHA `deed704`）确认的当前边界：

- **CI 不重新生成 `.icns`**：workflow 里没有渲染步骤，也不依赖 Playwright。
- **CI 不校验 `.icns` 与两个 SVG / profile 参数的一致性**：`logo-mark.svg`、`favicon.svg` 或
  `PROFILES` 日后漂移时，CI 不会发现入库 `.icns` 已过期。
- **当前替代防线** = 「`.icns` 入库 + 单元测试断言其存在 / 合法 / 两个文件一致」：
  `tests/unit/test_build_app_icon.py` 断言 `AppIcon.icns`、`VolumeIcon.icns` 存在、块表合法、
  两者逐字节相同，以及 `iconutil -c iconset` 解出恰好 10 个 representation。这只能证明
  **产物未损坏**，**不能证明产物与 SVG 一致**；一致性目前只能靠 `node assets/branding/make-appicon.mjs`
  重新生成后 `git diff --exit-code native/Resources` 人工确认。

### iconutil 对 16px / 32px 1x 的编码行为（已核实，不是「渲染了两次」）

入库 `.icns` 内部，`ic05`（32x32）与 `ic04`（16x16）以 `ARGB` RLE 存储，其余 8 档以 PNG 存储。
`--check` 每次都会重算并在不满足时失败，当前实测：

- `ic05` 解出的像素与 `ic11`（`icon_16x16@2x.png` 的 PNG 块）**逐像素完全相同**，`ic13`/`ic08`、
  `ic14`/`ic09` 同理 → 容器内同一像素尺寸确实只有一份图像。
- 把 `.icns` 解回 iconset 时，`iconutil -c iconset` 会把 `ARGB` 载荷再除一次 alpha
  （`clamp(round(c × 255 / α))`），因此解出的 `icon_32x32.png` 与 `icon_16x16@2x.png`
  **字节不同**：80 个像素 RGB 不同、最大 Δrgb 231、**alpha 通道完全相同**；
  并产生 4 个全白半透明像素 `(255,255,255, α≈20)`。`icon_16x16.png`（`ic04`）同理：
  与渲染稿 44 个像素 RGB 不同、alpha 完全相同、无全白像素（`ic04` 的 alpha 分布不同）。
- 结论：**输入给 `iconutil` 的 iconset 是同一份字节**（`--check` 用 `cmp` 断言，打包前也会断言），
  渲染侧 `omitBackground` + `background: transparent` 均已生效（渲染出的 PNG 里全白半透明像素数为 0）。
  上述差异是 `iconutil -c iconset` 解码 `ARGB` 块时**自己造出来的**，`.icns` 里存的像素是正确的，
  也与「同一尺寸渲染两次」无关。
- 注意：**不要用 `iconutil -c iconset` → `iconutil -c icns` 往返 `.icns`**。每往返一次，16/32px 1x 块的
  半透明像素会被再提亮一次（最终 clamp 到 255），即往返不是幂等的；要改图标只能从 SVG 用
  `node assets/branding/make-appicon.mjs` 重新生成。

