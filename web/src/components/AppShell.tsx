import type { ReactNode } from 'react'
import { THEME_LABELS, THEME_PREFERENCES, type ThemePreference } from '../theme'
import { useSaveStatus } from '../save-status'
import { useServiceStatus } from '../service-status'
import { NAV_ITEMS, sectionLabel, type ShellSection } from '../navigation'
import type { Toast } from '../toast'
import { ToastHost } from './ToastHost'

/**
 * 应用外壳（逐页规格 §0）。壳不承载业务，只回答三件事：
 * 我在哪（侧栏当前项 + 顶栏当前页名）、这个应用现在什么状态（保存三态、本机服务可达性）、怎么换工作库。
 *
 * 硬规格：
 * - 左侧栏 200px，主导航**恰好 5 项**、顺序固定：今日 / 审批 / 项目 / 知识问答 / 设置；
 *   当前项 `aria-current="page"` + 左侧 3px 强调条；审批项带待处理数量徽章（0 时不显示）。
 * - 侧栏底部：工作库名 + 首字头像 + 「切换…」；下方一行真实的本机服务状态（可达/不可达，两种文案两种颜色）。
 *   **不**用 `⌄` 暗示不存在的下拉。
 * - 顶栏 62px：左当前页名（只有页面阅读时才显示「项目 / 页面名」层级）；右真实的保存三态 + 主题三选。
 * - 主内容区 `max-width: 1200px` 居中（由 App.css 的 .content-wrap 承担）。
 * - 全局提示走右下角 toast，不再有常驻红色横幅。
 */
type Props = {
  section: ShellSection
  onSelect: (section: ShellSection) => void
  workspaceName: string
  onSwitchWorkspace: () => void
  /** 待处理总数（来源 + 稿件）；0 时不显示徽章。 */
  approvalCount: number
  /** 页面阅读时给出的「页面名」；为空时顶栏只显示当前页名。 */
  openPageTitle?: string | null
  themePreference: ThemePreference
  onThemePreferenceChange: (preference: ThemePreference) => void
  toasts: Toast[]
  onDismissToast: (id: number) => void
  children: ReactNode
}

/** 顶栏保存状态：真实三态 + 未保存过时不说话（不再有永远为真的「本机已保存」）。 */
function SaveIndicator() {
  const { phase, retry } = useSaveStatus()
  if (phase === 'idle') return null
  return (
    <div className={'save-state is-' + phase} role="status" aria-live="polite">
      {phase === 'saving' && <><span className="save-dot" aria-hidden="true" />保存中…</>}
      {phase === 'saved' && <>已保存</>}
      {phase === 'failed' && (
        <button type="button" className="text-button save-retry" onClick={() => retry?.()}>
          保存失败，点击重试
        </button>
      )}
    </div>
  )
}

export function AppShell({
  section,
  onSelect,
  workspaceName,
  onSwitchWorkspace,
  approvalCount,
  openPageTitle,
  themePreference,
  onThemePreferenceChange,
  toasts,
  onDismissToast,
  children,
}: Props) {
  const { reachable } = useServiceStatus()
  const currentLabel = sectionLabel(section)

  return (
    <div className="app-frame">
      <a className="skip-link" href="#main-content">跳到主内容</a>

      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">S</span>
          <div><strong>SummitEverything</strong><span>个人知识工作台</span></div>
        </div>

        <nav aria-label="主导航" className="primary-nav">
          {NAV_ITEMS.map((item) => {
            const badge = item.id === 'approval' ? approvalCount : 0
            return (
              <button
                key={item.id}
                className={section === item.id ? 'nav-item active' : 'nav-item'}
                aria-current={section === item.id ? 'page' : undefined}
                aria-label={badge > 0 ? `${item.label}，${badge} 项待处理` : item.label}
                title={item.label}
                onClick={() => onSelect(item.id)}
              >
                <span className={'nav-symbol nav-' + item.id} aria-hidden="true" />
                <span className="nav-label">{item.label}</span>
                {badge > 0 && <span className="nav-badge">{badge > 99 ? '99+' : badge}</span>}
              </button>
            )
          })}
        </nav>

        <div className="sidebar-bottom">
          <button className="workspace-name" aria-label="切换工作库" title="切换工作库" onClick={onSwitchWorkspace}>
            <span className="workspace-avatar" aria-hidden="true">{workspaceName.slice(0, 1)}</span>
            <span className="workspace-name-text"><strong>{workspaceName}</strong><small>切换…</small></span>
          </button>
          <div className={reachable ? 'local-indicator is-online' : 'local-indicator is-offline'}>
            <span className="local-dot" aria-hidden="true" />
            <span className="local-indicator-text">{reachable ? '仅本机运行' : '本机服务未连接'}</span>
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <header className="topbar">
          <div className="crumbs">
            <span>{currentLabel}</span>
            {openPageTitle && <><span className="crumb-separator" aria-hidden="true">/</span><span>{openPageTitle}</span></>}
          </div>
          <div className="topbar-right">
            <SaveIndicator />
            <select
              className="theme-select"
              aria-label="主题"
              title="主题：跟随系统 / 浅色 / 深色"
              value={themePreference}
              onChange={(event) => onThemePreferenceChange(event.target.value as ThemePreference)}
            >
              {THEME_PREFERENCES.map((preference) => (
                <option key={preference} value={preference}>{THEME_LABELS[preference]}</option>
              ))}
            </select>
          </div>
        </header>
        <main id="main-content" className="main-content" tabIndex={-1}>{children}</main>
      </div>

      <ToastHost toasts={toasts} onDismiss={onDismissToast} />
    </div>
  )
}
