/**
 * 机器守卫 · 源码 / CSS 扫描（FRONTEND-GUIDE §11）。
 *
 * 本文件本轮实现并做变异验证：
 *   ① 裸色部分 —— 组件 CSS 与 TSX/TS 内联样式不得出现裸 hex / rgb / hsl（§6.1、§11 ①）
 *   ① allowlist 机制 —— 内部 ID/hash/路径实例的「文件:字段」次数与 ui-contract.allowlist.json 精确相等（§9、§11 ①）
 *   ③ 字号下限 —— web/src/**\/*.css 全部 font-size ≥ 12px，9/10/11px 出现次数为 0（§6.1、§11 ③）
 *   ⑧ 外壳几何 —— 侧栏 200px / ≤800px 64px 图标栏 / ≤560px 底部 5 栏且每项 ≥44px / 粗指针 ≥44px（§0、§8.1）
 * ① 的运行时正文/details/title/aria-label 断言见 ui-contract.render.test.tsx；⑩ 五档浏览器视口由 Playwright 实际执行。
 */
import { readFileSync, readdirSync } from 'node:fs'
import { dirname, join, relative } from 'node:path'
import { describe, expect, it } from 'vitest'

/**
 * vitest 的 jsdom 环境里 import.meta.url 不是 file: URL，且 `.css?raw` 会被 CSS 插件置空，
 * 所以守卫直接从磁盘读源码文本（需要 tsconfig.app.json 的 "node" types）。
 */
function findWebRoot(): string {
  let candidate = process.cwd()
  for (let depth = 0; depth < 4; depth += 1) {
    for (const relativePath of ['src/theme-tokens.css', 'web/src/theme-tokens.css']) {
      const probe = join(candidate, relativePath)
      try {
        readFileSync(probe)
        return dirname(dirname(probe))
      } catch {
        /* 继续向上找 */
      }
    }
    candidate = dirname(candidate)
  }
  throw new Error('守卫③/⑦：找不到 web/ 目录（请从仓库根运行 npm --prefix web test）')
}

const WEB_ROOT = findWebRoot()
const REPO_ROOT = dirname(WEB_ROOT)
const SRC_ROOT = join(WEB_ROOT, 'src')
/** tokens 唯一真源；它是仓库里唯一允许出现颜色字面量的文件。 */
const TOKEN_FILE = 'web/src/theme-tokens.css'
const ALLOWLIST_FILE = join(SRC_ROOT, 'ui-contract.allowlist.json')
/** 字号必须走 --text-* tokens；根字号 15px（§6.1）。 */
const ROOT_FONT_SIZE_PX = 15

const RULE_FONT_FLOOR = '守卫③ 字号下限（FRONTEND-GUIDE §11 ③ 与 §6.1）：web/src 下的 font-size 不得低于 12px；.sr-only 白名单'
const RULE_FONT_TOKEN = '守卫③ 字号 token（FRONTEND-GUIDE §6.1）：字号只用 --text-* token，不再混用 rem/裸 px'
const RULE_BARE_COLOR = '守卫① 裸色（FRONTEND-GUIDE §11 ① 与 §6.1）：组件 CSS 与 TSX 内联样式不得出现裸 hex / rgb / hsl'
const RULE_ALLOWLIST = '守卫① 内部标识基线（FRONTEND-GUIDE §11 ① 与 §9）：每个「文件:字段」的出现次数必须与 ui-contract.allowlist.json 精确相等'

// ── 通用文件扫描 ────────────────────────────────────────────────────────────
function listFiles(dir: string, predicate: (path: string) => boolean): string[] {
  const found: string[] = []
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = join(dir, entry.name)
    if (entry.isDirectory()) found.push(...listFiles(full, predicate))
    else if (predicate(full)) found.push(full)
  }
  return found.sort()
}

/** 仓库相对路径（'web/src/App.css'），用于「文件:字段」基线键与失败消息。 */
function webPath(absolute: string): string {
  return relative(REPO_ROOT, absolute)
}

const cssFiles = () => listFiles(SRC_ROOT, (path) => path.endsWith('.css'))
const sourceFiles = () =>
  listFiles(SRC_ROOT, (path) => /\.(ts|tsx)$/.test(path) && !/\.test\./.test(path) && !relative(SRC_ROOT, path).startsWith('api/'))

// ── 极简 CSS 解析（够用即可：注释、嵌套 @media、声明行号）──────────────────────
type CssDeclaration = { property: string; value: string; line: number }
type CssRule = { selectors: string[]; declarations: CssDeclaration[]; atRule: string }

function parseCss(source: string): CssRule[] {
  // 用空格替换注释内容，保持行号不漂移。
  const text = source.replace(/\/\*[\s\S]*?\*\//g, (match) => match.replace(/[^\n]/g, ' '))
  const lineOf = (index: number) => text.slice(0, index).split('\n').length
  const rules: CssRule[] = []

  const parseDeclarations = (body: string, bodyStart: number): CssDeclaration[] => {
    const declarations: CssDeclaration[] = []
    let cursor = 0
    for (const raw of body.split(';')) {
      const trimmed = raw.trim()
      if (trimmed) {
        const colon = trimmed.indexOf(':')
        if (colon > 0) {
          declarations.push({
            property: trimmed.slice(0, colon).trim().toLowerCase(),
            value: trimmed.slice(colon + 1).trim(),
            line: lineOf(bodyStart + cursor),
          })
        }
      }
      cursor += raw.length + 1
    }
    return declarations
  }

  const parseBlock = (block: string, origin: number, atRule: string) => {
    let index = 0
    while (index < block.length) {
      const open = block.indexOf('{', index)
      if (open === -1) break
      const prelude = block.slice(index, open).trim()
      let depth = 1
      let cursor = open + 1
      while (cursor < block.length && depth > 0) {
        if (block[cursor] === '{') depth += 1
        else if (block[cursor] === '}') depth -= 1
        cursor += 1
      }
      const body = block.slice(open + 1, cursor - 1)
      if (prelude.startsWith('@')) {
        parseBlock(body, origin + open + 1, prelude)
      } else if (!body.includes('{')) {
        rules.push({
          selectors: prelude.split(',').map((selector) => selector.trim()).filter(Boolean),
          declarations: parseDeclarations(body, origin + open + 1),
          atRule,
        })
      }
      index = cursor
    }
  }

  parseBlock(text, 0, '')
  return rules
}

/** 读取 theme-tokens.css 的自定义属性（浅色 :root 为准）。 */
function collectTokens(): Map<string, string> {
  const tokens = new Map<string, string>()
  for (const rule of parseCss(readFileSync(join(SRC_ROOT, 'theme-tokens.css'), 'utf8'))) {
    if (!rule.selectors.includes(':root')) continue
    for (const declaration of rule.declarations) {
      if (declaration.property.startsWith('--')) tokens.set(declaration.property, declaration.value)
    }
  }
  return tokens
}

const TOKENS = collectTokens()

// ── 字号解析 ────────────────────────────────────────────────────────────────
/** 只认值开头的 token 引用，避免把 font 简写尾巴上的 var(--mono) 误当字号。 */
const TOKEN_REFERENCE = /^var\(\s*(--[a-z0-9-]+)\s*\)/i
/** 字号只允许引用 --text-*（§6.1）。 */
const TEXT_TOKEN_REFERENCE = /^var\(\s*--text-[a-z0-9-]+\s*\)/i
const DIMENSION = /(-?\d*\.?\d+)\s*(px|rem|em|pt)/i

function toPx(amount: number, unit: string): number {
  if (unit === 'px') return amount
  if (unit === 'pt') return (amount * 4) / 3
  return amount * ROOT_FONT_SIZE_PX // rem / em：根字号 15px（§6.1）
}

/** 解析一个字号值；返回 null 表示这条声明不携带字号（例如 font: inherit）。 */
function resolveFontSize(value: string): { px: number | null; error?: string } {
  const trimmed = value.trim()
  const tokenMatch = trimmed.match(TOKEN_REFERENCE)
  if (tokenMatch) {
    const tokenValue = TOKENS.get(tokenMatch[1])
    if (!tokenValue) return { px: null, error: `引用了未定义的 token ${tokenMatch[1]}` }
    return resolveFontSize(tokenValue)
  }
  if (/^clamp\(/i.test(trimmed)) {
    const first = trimmed.slice(trimmed.indexOf('(') + 1).split(',')[0]
    return resolveFontSize(first)
  }
  const dimension = trimmed.match(DIMENSION)
  if (dimension) return { px: toPx(Number(dimension[1]), dimension[2].toLowerCase()) }
  if (trimmed === '0') return { px: 0 }
  return { px: null }
}

type Sightings = { file: string; line: number; selector: string; value: string; px: number; error?: string }

function fontSizeSightings(): Sightings[] {
  const sightings: Sightings[] = []
  for (const path of cssFiles()) {
    for (const rule of parseCss(readFileSync(path, 'utf8'))) {
      // 白名单：.sr-only 是唯一允许隐藏文本的辅助类（§6.1）。
      if (rule.selectors.some((selector) => selector.includes('.sr-only'))) continue
      for (const declaration of rule.declarations) {
        const isSize = declaration.property === 'font-size'
        const isShorthand = declaration.property === 'font' && !/^(inherit|initial|unset|revert|revert-layer)$/i.test(declaration.value)
        if (!isSize && !isShorthand) continue
        const resolved = resolveFontSize(declaration.value)
        if (resolved.px === null && !resolved.error) continue
        sightings.push({
          file: webPath(path),
          line: declaration.line,
          selector: rule.selectors.join(', '),
          value: declaration.value,
          px: resolved.px ?? -1,
          error: resolved.error,
        })
      }
    }
  }
  return sightings
}

const describeSighting = (sighting: Sightings) =>
  `${sighting.file}:${sighting.line} 「${sighting.selector}」 font-size: ${sighting.value}` +
  (sighting.error ? `（${sighting.error}）` : ` → ${sighting.px}px`)

describe('守卫③ 字号下限（GUIDE §11 ③、§6.1）', () => {
  it('web/src 下没有低于 12px 的 font-size 声明，且 9/10/11px 出现次数为 0', () => {
    const sightings = fontSizeSightings()
    const belowFloor = sightings.filter((sighting) => sighting.error || sighting.px < 12)
    const nineToEleven = sightings.filter((sighting) => [9, 10, 11].includes(sighting.px))

    expect(sightings.length, '字号扫描没有命中任何声明，说明扫描逻辑坏了（见 GUIDE §11 ③）').toBeGreaterThan(50)
    expect(belowFloor.map(describeSighting), RULE_FONT_FLOOR).toEqual([])
    expect(nineToEleven.map(describeSighting), `${RULE_FONT_FLOOR}；9/10/11px 必须为 0 次`).toEqual([])
  })

  it('字号只用 --text-* token（不再混用 rem / 裸 px）', () => {
    const offenders = fontSizeSightings()
      .filter((sighting) => !TEXT_TOKEN_REFERENCE.test(sighting.value))
      .map(describeSighting)
    expect(offenders, RULE_FONT_TOKEN).toEqual([])
  })
})

describe('守卫① 裸色（GUIDE §11 ①、§6.1）', () => {
  const COLOR_LITERAL = /#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(/g

  function colorOffenders(path: string, source: string): string[] {
    const offenders: string[] = []
    source.split('\n').forEach((line, index) => {
      for (const match of line.matchAll(COLOR_LITERAL)) {
        offenders.push(`${webPath(path)}:${index + 1} 出现裸色 ${match[0]}：${line.trim().slice(0, 120)}`)
      }
    })
    return offenders
  }

  it('组件 CSS 不得出现裸 hex / rgb / hsl（theme-tokens.css 是唯一例外）', () => {
    const offenders: string[] = []
    for (const path of cssFiles()) {
      if (webPath(path) === TOKEN_FILE) continue
      offenders.push(...colorOffenders(path, readFileSync(path, 'utf8')))
    }
    expect(offenders, `${RULE_BARE_COLOR}；颜色只在 ${TOKEN_FILE} 定义，其它文件用 var(--token)`).toEqual([])
  })

  it('TSX / TS 内联样式不得出现裸 hex / rgb / hsl', () => {
    const offenders: string[] = []
    for (const path of sourceFiles()) {
      offenders.push(...colorOffenders(path, readFileSync(path, 'utf8')))
    }
    expect(offenders, `${RULE_BARE_COLOR}；内联样式请改用 var(--token)`).toEqual([])
  })
})

describe('守卫① 内部标识基线（GUIDE §11 ①、§9）', () => {
  type Allowlist = {
    fields: string[]
    entries: Record<string, number>
    attribution: Record<string, { slice: string; reason: string }>
  }
  const allowlist = JSON.parse(readFileSync(ALLOWLIST_FILE, 'utf8')) as Allowlist

  function countSightings(): Map<string, number> {
    const counts = new Map<string, number>()
    for (const path of sourceFiles()) {
      const source = readFileSync(path, 'utf8')
      for (const field of allowlist.fields) {
        const pattern = field === '.slice(0, 8)' ? /\.slice\(\s*0\s*,\s*8\s*\)/g : new RegExp(`\\b${field}\\b`, 'g')
        const found = source.match(pattern)?.length ?? 0
        if (found > 0) counts.set(`${webPath(path)}:${field}`, found)
      }
    }
    return counts
  }

  it('每个「文件:字段」的出现次数与 allowlist 精确相等（多一个、少一个都要显式改基线）', () => {
    const counts = countSightings()
    const keys = new Set([...counts.keys(), ...Object.keys(allowlist.entries)])
    const mismatches: string[] = []
    for (const key of [...keys].sort()) {
      const found = counts.get(key) ?? 0
      const allowed = allowlist.entries[key]
      if (allowed === undefined) mismatches.push(`${key}: 源码出现 ${found} 次，但 allowlist 没有登记（新增内部标识实例）`)
      else if (found !== allowed) mismatches.push(`${key}: 源码出现 ${found} 次，allowlist 登记 ${allowed} 次`)
    }
    expect(mismatches, RULE_ALLOWLIST).toEqual([])
  })

  it('allowlist 每条都写明归属切片与理由，且与 entries 键集合一致', () => {
    const missing = Object.keys(allowlist.entries).filter((key) => !allowlist.attribution[key]?.slice)
    expect(missing, '守卫① 基线（GUIDE §9）：allowlist 的每条都要写归属切片，否则后续切片不知道该清哪一条').toEqual([])
    expect(Object.keys(allowlist.attribution).filter((key) => !(key in allowlist.entries))).toEqual([])
  })
})

/**
 * 外壳几何与响应式（逐页规格 §0、GUIDE §8.1）。
 *
 * jsdom 量不到布局与 scrollWidth（真正的五档断言是守卫 ⑩，仍登记为 todo），
 * 所以这一组直接断言 App.css 里被点名的几何值；改坏几何必须让这里的断言变红。
 */
const RULE_SHELL_GEOMETRY = '守卫⑧ 外壳几何（逐页规格 §0 与 GUIDE §8.1）：侧栏 200px、≤800px 64px 图标栏、≤560px 底部 5 栏每项 ≥44px、粗指针 ≥44px'

function declarationValue(
  rules: ReturnType<typeof parseCss>,
  selector: string,
  property: string,
  atRuleFragment = '',
): string | undefined {
  for (const rule of rules) {
    if (atRuleFragment && !rule.atRule.includes(atRuleFragment)) continue
    if (!rule.selectors.includes(selector)) continue
    const found = rule.declarations.find((declaration) => declaration.property === property)
    if (found) return found.value
  }
  return undefined
}

describe('守卫⑧ 外壳几何与响应式（逐页规格 §0、GUIDE §8.1）', () => {
  const appCss = parseCss(readFileSync(join(SRC_ROOT, 'App.css'), 'utf8'))
  const px = (value: string | undefined) => (value ? Number(value.match(/(-?\d*\.?\d+)px/)?.[1] ?? NaN) : NaN)

  it('桌面：侧栏 200px、顶栏 62px、主内容 max-width 1200px、导航项高 44px', () => {
    expect(declarationValue(appCss, '.sidebar', 'width'), `${RULE_SHELL_GEOMETRY}；侧栏必须是 200px`).toBe('200px')
    expect(declarationValue(appCss, '.sidebar', 'flex'), `${RULE_SHELL_GEOMETRY}；侧栏不得被内容撑开`).toContain('200px')
    expect(declarationValue(appCss, '.topbar', 'height'), `${RULE_SHELL_GEOMETRY}；顶栏必须是 62px`).toBe('62px')
    expect(declarationValue(appCss, '.content-wrap', 'max-width'), `${RULE_SHELL_GEOMETRY}；主内容区必须 max-width: 1200px 居中`).toBe('1200px')
    expect(px(declarationValue(appCss, '.nav-item', 'min-height')), `${RULE_SHELL_GEOMETRY}；导航项每项高 44px`).toBeGreaterThanOrEqual(44)
    expect(declarationValue(appCss, '.nav-item.active::before', 'width'), `${RULE_SHELL_GEOMETRY}；当前项左侧 3px 强调条`).toBe('3px')
  })

  it('≤800px：侧栏折成 64px 图标栏', () => {
    expect(declarationValue(appCss, '.sidebar', 'width', 'max-width: 800px'), `${RULE_SHELL_GEOMETRY}；≤800px 折成 64px 图标栏`).toBe('64px')
    expect(declarationValue(appCss, '.sidebar', 'flex-basis', 'max-width: 800px')).toBe('64px')
  })

  it('≤560px：底栏是 5 栏，每一项 ≥44px', () => {
    expect(declarationValue(appCss, '.primary-nav', 'grid-template-columns', 'max-width: 560px'), `${RULE_SHELL_GEOMETRY}；≤560px 变底部 5 栏`).toMatch(/repeat\(\s*5\s*,/)
    expect(declarationValue(appCss, '.sidebar', 'position', 'max-width: 560px'), `${RULE_SHELL_GEOMETRY}；底栏固定在视口底部`).toBe('fixed')
    expect(px(declarationValue(appCss, '.nav-item', 'min-height', 'max-width: 560px')), `${RULE_SHELL_GEOMETRY}；底部导航每项 ≥44px`).toBeGreaterThanOrEqual(44)
  })

  it('粗指针：导航项与图标按钮 ≥44px', () => {
    expect(px(declarationValue(appCss, '.nav-item', 'min-height', 'pointer: coarse')), `${RULE_SHELL_GEOMETRY}；粗指针下导航项 ≥44px`).toBeGreaterThanOrEqual(44)
    expect(px(declarationValue(appCss, '.toast-close', 'min-width', 'pointer: coarse')), `${RULE_SHELL_GEOMETRY}；粗指针下图标按钮 44×44`).toBeGreaterThanOrEqual(44)
    expect(px(declarationValue(appCss, '.toast-close', 'min-height', 'pointer: coarse'))).toBeGreaterThanOrEqual(44)
  })
})
