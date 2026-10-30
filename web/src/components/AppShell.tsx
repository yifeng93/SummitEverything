import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { ArrowLeftRight, Check, ChevronsUpDown, ClipboardCheck, FolderKanban, MessageCircleQuestion, Monitor, Moon, Palette, Settings, Sun, type LucideIcon } from 'lucide-react'
import { THEME_LABELS, THEME_PREFERENCES, type ThemePreference } from '../theme'
import { useSaveStatus } from '../save-status'
import { NAV_ITEMS, type ShellSection } from '../navigation'
import type { Toast } from '../toast'
import { ToastHost } from './ToastHost'

const NAV_ICONS: Record<ShellSection, LucideIcon> = {
  today: Sun,
  approval: ClipboardCheck,
  projects: FolderKanban,
  ask: MessageCircleQuestion,
  settings: Settings,
}

const THEME_ICONS = { system: Monitor, light: Sun, dark: Moon } as const

/**
 * 应用外壳（逐页规格 §0）。壳不承载业务，只回答两件事：
 * 我在哪（侧栏当前项）、怎么换工作库。
 *
 * 硬规格：
 * - 左侧栏 200px，主导航**恰好 5 项**、顺序固定：今日 / 审批 / 项目 / 知识问答 / 设置；
 *   当前项 `aria-current="page"` + 左侧 3px 强调条；审批项带待处理数量徽章（0 时不显示）。
 * - 「项目」下面挂二级快捷入口（未归档项目的名字），点一下直接进那个项目的详情。
 *   二级项不是第 6 个导航目的地，不计入 5 项；≤800px 图标栏与 ≤560px 底栏不显示。
 * - **没有顶栏**：页名由各页自己的 h1 承担，不再用一条 62px 的条重复一遍。
 * - 侧栏底部：保存三态（仅在有状态时出现）+ 紧凑工作库选择器 + 「外观」入口。
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
  /** 「项目」下的二级快捷入口；只传未归档项目。 */
  projects?: { id: string; name: string }[]
  /** 当前正在看的项目；用于二级项高亮。 */
  activeProjectId?: string | null
  onOpenProject?: (projectId: string) => void
  themePreference: ThemePreference
  onThemePreferenceChange: (preference: ThemePreference) => void
  toasts: Toast[]
  onDismissToast: (id: number) => void
  children: ReactNode
}

/** 导航图标统一走 Lucide，尺寸与描边由这里固定，避免各页手绘几何错位。 */
function NavIcon({ section }: { section: ShellSection }) {
  const Icon = NAV_ICONS[section]
  return <Icon className="nav-icon" size={18} strokeWidth={1.75} aria-hidden="true" />
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
  projects = [],
  activeProjectId = null,
  onOpenProject,
  themePreference,
  onThemePreferenceChange,
  toasts,
  onDismissToast,
  children,
}: Props) {
  const [menu, setMenu] = useState<'workspace' | 'theme' | null>(null)
  const workspaceButton = useRef<HTMLButtonElement>(null)
  const workspacePanel = useRef<HTMLDivElement>(null)
  const themeButton = useRef<HTMLButtonElement>(null)
  const themePanel = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!menu) return
    const closeOnOutside = (event: PointerEvent) => {
      const target = event.target as Node
      const inside = [workspaceButton, workspacePanel, themeButton, themePanel]
        .some((ref) => ref.current?.contains(target))
      if (inside) return
      setMenu(null)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setMenu(null)
      ;(menu === 'workspace' ? workspaceButton : themeButton).current?.focus()
    }
    document.addEventListener('pointerdown', closeOnOutside)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('pointerdown', closeOnOutside)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [menu])

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
              <Fragment key={item.id}>
                <button
                  className={section === item.id ? 'nav-item active' : 'nav-item'}
                  aria-current={section === item.id ? 'page' : undefined}
                  aria-label={badge > 0 ? `${item.label}，${badge} 项待处理` : item.label}
                  title={item.label}
                  onClick={() => onSelect(item.id)}
                >
                  <NavIcon section={item.id} />
                  <span className="nav-label">{item.label}</span>
                  {badge > 0 && <span className="nav-badge">{badge > 99 ? '99+' : badge}</span>}
                </button>
                {item.id === 'projects' && projects.length > 0 && (
                  <ul className="nav-submenu" aria-label="项目快捷入口">
                    {projects.map((project) => {
                      const current = activeProjectId === project.id
                      return <li key={project.id}>
                        <button
                          className={current ? 'nav-subitem active' : 'nav-subitem'}
                          aria-current={current ? 'page' : undefined}
                          title={project.name}
                          onClick={() => { setMenu(null); onOpenProject?.(project.id) }}
                        >{project.name}</button>
                      </li>
                    })}
                  </ul>
                )}
              </Fragment>
            )
          })}
        </nav>

        <div className="sidebar-bottom">
          {/* 保存三态从顶栏搬到侧栏底部：没有顶栏之后，这是唯一常驻的外壳状态位。 */}
          <SaveIndicator />
          <div className="sidebar-menu-anchor">
            <button
              ref={workspaceButton}
              type="button"
              className="workspace-switcher"
              aria-label={`工作库：${workspaceName}，打开菜单`}
              aria-haspopup="dialog"
              aria-expanded={menu === 'workspace'}
              title="切换工作库"
              onClick={() => setMenu(menu === 'workspace' ? null : 'workspace')}
            >
              <span className="workspace-avatar" aria-hidden="true">{workspaceName.slice(0, 1)}</span>
              <span className="workspace-switcher-name">{workspaceName}</span>
              <ChevronsUpDown className="workspace-switcher-chevron" size={14} strokeWidth={1.75} aria-hidden="true" />
            </button>
            {menu === 'workspace' && <div ref={workspacePanel} className="sidebar-popover workspace-popover" role="dialog" aria-label="工作库菜单">
              <p className="sidebar-popover-title">工作库</p>
              <button type="button" className="sidebar-popover-action" onClick={() => { setMenu(null); onSwitchWorkspace() }}>
                <ArrowLeftRight size={15} strokeWidth={1.75} aria-hidden="true" />
                <span>切换工作库</span>
              </button>
            </div>}
          </div>
          <div className="sidebar-menu-anchor">
            <button
              ref={themeButton}
              type="button"
              className="sidebar-theme"
              aria-label="外观与主题"
              aria-haspopup="dialog"
              aria-expanded={menu === 'theme'}
              title="外观与主题"
              onClick={() => setMenu(menu === 'theme' ? null : 'theme')}
            >
              <Palette size={16} strokeWidth={1.75} aria-hidden="true" />
              <span className="sidebar-theme-label">外观</span>
            </button>
            {menu === 'theme' && <div ref={themePanel} className="sidebar-popover theme-popover" role="dialog" aria-label="外观与主题">
              <p className="sidebar-popover-title">外观</p>
              {THEME_PREFERENCES.map((preference) => {
                const Icon = THEME_ICONS[preference]
                const selected = themePreference === preference
                return <button
                  key={preference}
                  type="button"
                  className={selected ? 'theme-option selected' : 'theme-option'}
                  aria-pressed={selected}
                  onClick={() => { onThemePreferenceChange(preference); setMenu(null) }}
                >
                  <Icon size={15} strokeWidth={1.75} aria-hidden="true" />
                  <span>{THEME_LABELS[preference]}</span>
                  {selected && <Check className="theme-check" size={14} strokeWidth={2} aria-hidden="true" />}
                </button>
              })}
            </div>}
          </div>
        </div>
      </aside>

      <div className="main-shell">
        <main id="main-content" className="main-content" tabIndex={-1}>{children}</main>
      </div>

      <ToastHost toasts={toasts} onDismiss={onDismissToast} />
    </div>
  )
}
