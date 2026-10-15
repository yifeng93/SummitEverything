/**
 * 机器守卫 ⑦ · 深色对比度（FRONTEND-GUIDE §6.2、§11 ⑦）。
 *
 * 从 theme-tokens.css 解析两套 tokens 的**真实色值**，计算并打印 §6.2 列出的 10 组 WCAG 比值：
 *   ink/paper、muted/paper、ink/surface、muted/surface、on-accent/accent、accent/accent-wash、
 *   green/green-wash、danger/danger-wash、warn/warn-wash ≥ 4.5:1；control-border/surface ≥ 3.0:1。
 * 同时核对：深色块覆盖全部颜色 tokens；主题由 <html data-theme> 驱动；index.html 首屏前应用偏好；
 * 尺度 tokens 与 §6.1 一致（含 12px 字号下限）。
 */
import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { THEME_STORAGE_KEY } from './theme'

/** 同 ui-contract.test.ts：jsdom 下没有 file: URL，`.css?raw` 也会被置空，所以直接读磁盘。 */
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
  throw new Error('守卫⑦：找不到 web/ 目录（请从仓库根运行 npm --prefix web test）')
}

const WEB_ROOT = findWebRoot()
const TOKENS_SOURCE = readFileSync(join(WEB_ROOT, 'src/theme-tokens.css'), 'utf8')
const TOKENS_PATH = 'web/src/theme-tokens.css'
const INDEX_CSS_SOURCE = readFileSync(join(WEB_ROOT, 'src/index.css'), 'utf8')
const INDEX_HTML = readFileSync(join(WEB_ROOT, 'index.html'), 'utf8')

const RULE_DARK_CONTRAST = '守卫⑦ 深色对比度（GUIDE §6.2 与 §11 ⑦）：正文/背景与正文/表面 ≥4.5:1，控件边框/表面 ≥3.0:1'
const RULE_DARK_FIRST_CLASS = '守卫⑦ 深色一等公民（GUIDE §6.2）：主题由 <html data-theme> 驱动，深色块覆盖全部颜色 tokens，index.html 首屏前应用偏好'

const stripComments = (css: string) => css.replace(/\/\*[\s\S]*?\*\//g, '')

function readTokenBlock(source: string, selector: string): Map<string, string> {
  const cleaned = stripComments(source)
  const start = cleaned.indexOf(selector)
  if (start === -1) throw new Error(`${TOKENS_PATH} 缺少 token 块 ${selector}（GUIDE §6.1）`)
  const open = cleaned.indexOf('{', start)
  const close = cleaned.indexOf('}', open)
  const tokens = new Map<string, string>()
  for (const match of cleaned.slice(open + 1, close).matchAll(/(--[a-z0-9-]+)\s*:\s*([^;]+);/gi)) {
    tokens.set(match[1], match[2].trim())
  }
  return tokens
}

const LIGHT = readTokenBlock(TOKENS_SOURCE, ':root')
const DARK = readTokenBlock(TOKENS_SOURCE, ':root[data-theme="dark"]')

// ── WCAG 对比度 ─────────────────────────────────────────────────────────────
type Rgb = { r: number; g: number; b: number }

function parseColor(value: string): Rgb {
  const hex = value.trim().match(/^#([0-9a-fA-F]{3,8})$/)
  if (hex) {
    const digits = hex[1].length <= 4
      ? hex[1].slice(0, 3).split('').map((char) => char + char).join('')
      : hex[1].slice(0, 6)
    return { r: parseInt(digits.slice(0, 2), 16), g: parseInt(digits.slice(2, 4), 16), b: parseInt(digits.slice(4, 6), 16) }
  }
  const functional = value.trim().match(/^rgba?\(([^)]+)\)$/i)
  if (functional) {
    const [r, g, b] = functional[1].split(/[\s,/]+/).filter(Boolean).slice(0, 3).map(Number)
    return { r, g, b }
  }
  throw new Error(`无法解析颜色值 ${value}（GUIDE §6.2）`)
}

function relativeLuminance({ r, g, b }: Rgb): number {
  const channel = (value: number) => {
    const scaled = value / 255
    return scaled <= 0.04045 ? scaled / 12.92 : ((scaled + 0.055) / 1.055) ** 2.4
  }
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

function contrastRatio(foreground: string, background: string): number {
  const first = relativeLuminance(parseColor(foreground))
  const second = relativeLuminance(parseColor(background))
  const [high, low] = first > second ? [first, second] : [second, first]
  return (high + 0.05) / (low + 0.05)
}

type Pair = { label: string; foreground: string; background: string; minimum: number }

/** §6.2 点名的 10 组；阈值取自 GUIDE（正文/表面 4.5，控件边框 3.0）。 */
const CONTRAST_PAIRS: Pair[] = [
  { label: 'ink/paper', foreground: '--ink', background: '--paper', minimum: 4.5 },
  { label: 'muted/paper', foreground: '--muted', background: '--paper', minimum: 4.5 },
  { label: 'ink/surface', foreground: '--ink', background: '--surface', minimum: 4.5 },
  { label: 'muted/surface', foreground: '--muted', background: '--surface', minimum: 4.5 },
  { label: 'on-accent/accent', foreground: '--on-accent', background: '--accent', minimum: 4.5 },
  { label: 'accent/accent-wash', foreground: '--accent', background: '--accent-wash', minimum: 4.5 },
  { label: 'green/green-wash', foreground: '--green', background: '--green-wash', minimum: 4.5 },
  { label: 'danger/danger-wash', foreground: '--danger', background: '--danger-wash', minimum: 4.5 },
  { label: 'warn/warn-wash', foreground: '--warn', background: '--warn-wash', minimum: 4.5 },
  { label: 'control-border/surface', foreground: '--control-border', background: '--surface', minimum: 3.0 },
]

/** 不计入门禁、但同样打印出来便于人工判断的补充组。 */
const DIAGNOSTIC_PAIRS: Omit<Pair, 'minimum'>[] = [
  { label: 'quiet/surface', foreground: '--quiet', background: '--surface' },
  { label: 'accent-dark/accent-wash', foreground: '--accent-dark', background: '--accent-wash' },
  { label: 'danger-ink/danger-wash', foreground: '--danger-ink', background: '--danger-wash' },
  { label: 'warn-ink/warn-wash', foreground: '--warn-ink', background: '--warn-wash' },
  { label: 'sidebar-muted/sidebar', foreground: '--sidebar-muted', background: '--sidebar' },
  { label: 'sidebar-fg/sidebar', foreground: '--sidebar-fg', background: '--sidebar' },
]

function tokenValue(tokens: Map<string, string>, theme: string, name: string): string {
  const value = tokens.get(name)
  if (!value) throw new Error(`守卫⑦：${theme} 缺少 token ${name}（GUIDE §6.1）`)
  return value
}

function printRatios(theme: string, tokens: Map<string, string>, pairs: Pair[], gated: boolean): void {
  const lines = [`[守卫⑦] ${theme}主题对比度（GUIDE §6.2）${gated ? ' · 门禁组' : ' · 仅打印'}`, '  组名                          前景        背景        比值']
  for (const pair of pairs) {
    const ratio = contrastRatio(tokenValue(tokens, theme, pair.foreground), tokenValue(tokens, theme, pair.background))
    const status = gated ? (ratio >= pair.minimum ? 'PASS' : 'FAIL') : '--'
    lines.push(`  ${pair.label.padEnd(28)} ${tokenValue(tokens, theme, pair.foreground).padEnd(11)} ${tokenValue(tokens, theme, pair.background).padEnd(11)} ${ratio.toFixed(2)} ${status}`)
  }
  console.log(lines.join('\n'))
}

function gatedFailures(theme: string, tokens: Map<string, string>): string[] {
  return CONTRAST_PAIRS.filter(
    (pair) => contrastRatio(tokenValue(tokens, theme, pair.foreground), tokenValue(tokens, theme, pair.background)) < pair.minimum,
  ).map((pair) => {
    const ratio = contrastRatio(tokenValue(tokens, theme, pair.foreground), tokenValue(tokens, theme, pair.background))
    return `${theme}${pair.label}: ${tokenValue(tokens, theme, pair.foreground)} / ${tokenValue(tokens, theme, pair.background)} = ${ratio.toFixed(2)} < ${pair.minimum}`
  })
}

describe('守卫⑦ 深色对比度（GUIDE §6.2、§11 ⑦）', () => {
  it('浅色 tokens 的 10 组对比度达标（并打印真实比值）', () => {
    printRatios('浅色', LIGHT, CONTRAST_PAIRS, true)
    printRatios('浅色', LIGHT, DIAGNOSTIC_PAIRS.map((pair) => ({ ...pair, minimum: 4.5 })), false)
    expect(gatedFailures('浅色', LIGHT), RULE_DARK_CONTRAST).toEqual([])
  })

  it('深色 tokens 的 10 组对比度达标（并打印真实比值）', () => {
    printRatios('深色', DARK, CONTRAST_PAIRS, true)
    printRatios('深色', DARK, DIAGNOSTIC_PAIRS.map((pair) => ({ ...pair, minimum: 4.5 })), false)
    expect(gatedFailures('深色', DARK), RULE_DARK_CONTRAST).toEqual([])
  })
})

const COLOR_LITERAL = /^(#[0-9a-fA-F]{3,8}|rgba?\(|hsla?\()/

describe('守卫⑦ 深色一等公民（GUIDE §6.2）', () => {
  it('深色块覆盖浅色里定义的每一个颜色 token', () => {
    const colorTokens = [...LIGHT.entries()].filter(([, value]) => COLOR_LITERAL.test(value)).map(([name]) => name)
    expect(colorTokens.length, '守卫⑦：解析不到颜色 tokens，说明 token 文件结构变了（GUIDE §6.1）').toBeGreaterThan(20)
    const missing = colorTokens.filter((name) => !DARK.has(name))
    expect(
      missing,
      `${RULE_DARK_FIRST_CLASS}；深色块缺少这些颜色 token：${missing.join(', ')}。深色下会回退到浅色值（白底白字）`,
    ).toEqual([])
  })

  it('主题由 <html data-theme="dark"> 驱动，而不是只靠 prefers-color-scheme', () => {
    const cleaned = stripComments(TOKENS_SOURCE)
    expect(cleaned).toMatch(/:root\[data-theme="dark"\]/)
    const mediaFallback = cleaned.match(/@media[^{]*prefers-color-scheme/)
    expect(
      mediaFallback?.[0] ?? '',
      `${RULE_DARK_FIRST_CLASS}；颜色不能只挂在 @media (prefers-color-scheme) 上，必须由 data-theme 驱动`,
    ).toBe('')
  })

  it('index.html 在首屏（样式表与模块脚本之前）应用 localStorage 的主题偏好', () => {
    expect(
      THEME_STORAGE_KEY,
      '守卫⑦（GUIDE §6.2）：持久化键必须是规格点名的 sx:theme-preference，改键要同步 index.html 引导脚本',
    ).toBe('sx:theme-preference')
    const themeScript = INDEX_HTML.indexOf(THEME_STORAGE_KEY)
    const moduleScript = INDEX_HTML.indexOf('type="module"')
    const headEnd = INDEX_HTML.indexOf('</head>')
    expect(themeScript, `${RULE_DARK_FIRST_CLASS}；index.html 必须读取 localStorage 的 sx:theme-preference`).toBeGreaterThan(-1)
    expect(moduleScript, '守卫⑦：index.html 找不到模块脚本入口').toBeGreaterThan(-1)
    expect(themeScript, `${RULE_DARK_FIRST_CLASS}；引导脚本必须在模块脚本之前运行，否则会闪白/闪黑`).toBeLessThan(moduleScript)
    expect(themeScript, `${RULE_DARK_FIRST_CLASS}；引导脚本必须在 <head> 里`).toBeLessThan(headEnd)
    expect(INDEX_HTML, `${RULE_DARK_FIRST_CLASS}；引导脚本必须写入 data-theme`).toMatch(/setAttribute\(\s*['"]data-theme['"]/)
    expect(INDEX_HTML, `${RULE_DARK_FIRST_CLASS}；system 必须解析系统偏好`).toMatch(/matchMedia\(\s*['"]\(prefers-color-scheme: dark\)['"]/)
  })
})

const REQUIRED_SCALE: Record<string, string> = {
  '--space-1': '4px',
  '--space-2': '8px',
  '--space-3': '12px',
  '--space-4': '16px',
  '--space-6': '24px',
  '--space-8': '32px',
  '--radius-sm': '6px',
  '--radius': '9px',
  '--radius-lg': '14px',
  '--radius-pill': '999px',
  '--text-caption': '12px',
  '--text-small': '13px',
  '--text-list': '14px',
  '--text-body': '15px',
  '--text-section': '16px',
  '--text-page': '22px',
  '--text-display': '31px',
  '--lh-body': '1.6',
  '--lh-read': '1.75',
  '--measure-read': '72ch',
}

const REQUIRED_COLOR_TOKENS = [
  '--ink', '--muted', '--quiet', '--paper', '--surface', '--surface-2',
  '--line', '--line-strong', '--control-border',
  '--accent', '--accent-dark', '--accent-wash', '--on-accent',
  '--green', '--green-wash',
  '--danger', '--danger-wash', '--danger-ink',
  '--warn', '--warn-wash', '--warn-ink',
  '--sidebar', '--sidebar-muted', '--sidebar-active', '--sidebar-fg',
]

describe('尺度 tokens（GUIDE §6.1、D11）', () => {
  it('间距 / 圆角 / 字号 / 行高 tokens 与 §6.1 完全一致', () => {
    const normalize = (value: string) => value.replace(/\s+/g, '')
    const mismatches = Object.entries(REQUIRED_SCALE)
      .filter(([name, expected]) => LIGHT.get(name) === undefined || normalize(LIGHT.get(name)!) !== normalize(expected))
      .map(([name, expected]) => `${name}: 期望 ${expected}，实际 ${LIGHT.get(name) ?? '（缺失）'}`)
    expect(mismatches, '守卫③ / GUIDE §6.1：尺度 tokens 缺失或值与规格不一致（12px 是字号下限）').toEqual([])
  })

  it('§6.1 点名的颜色语义位都在（含 danger / warn / control-border / sidebar-fg）', () => {
    const missing = REQUIRED_COLOR_TOKENS.filter((name) => !LIGHT.has(name))
    expect(missing, 'GUIDE §6.1：颜色语义位缺失').toEqual([])
  })

  it('根字号保持 15px（§6.1），行高走 --lh-body 1.6', () => {
    const root = stripComments(INDEX_CSS_SOURCE)
    expect(root).toMatch(/font-size:\s*var\(--text-body\)/)
    expect(REQUIRED_SCALE['--lh-body']).toBe('1.6')
  })
})
