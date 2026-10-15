import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError, type Draft, type IntakeItem, type Page, type Workspace } from './api/client'
import { approvalPendingCount } from './approval-summary'
import { AppShell } from './components/AppShell'
import { ApprovalView } from './components/ApprovalView'
import { AskView } from './components/AskView'
import { PageReader } from './components/PageReader'
import { ProjectsView } from './components/ProjectsView'
import { ServiceUnreachableScreen, ConnectingScreen } from './components/ServiceStatus'
import { SettingsView } from './components/SettingsView'
import { TodayView } from './components/TodayView'
import { WorkspaceGate } from './components/WorkspaceGate'
import type { ShellSection } from './navigation'
import { useThemePreference } from './theme'
import { useToasts, type ToastKind } from './toast'
import './App.css'

/**
 * 外壳状态机（逐页规格 §0「三态」）。
 * `connecting` / `unreachable` / `no-workspace` 必须分开：
 * 只有后端明确回答「还没有工作库」（409 `workspace_not_open`）才进首次配置向导；
 * 连不上或服务报错时显示就地提示，绝不冒充「还没有工作库」。
 */
type Connection = 'connecting' | 'ready' | 'no-workspace' | 'unreachable'

export default function App() {
  const [connection, setConnection] = useState<Connection>('connecting')
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [section, setSection] = useState<ShellSection>('today')
  const [page, setPage] = useState<Page | null>(null)
  const [profileDir, setProfileDir] = useState<string | undefined>(undefined)
  const [approval, setApproval] = useState<{ items: IntakeItem[]; drafts: Draft[]; loading: boolean; error: string }>({
    items: [],
    drafts: [],
    loading: true,
    error: '',
  })
  const [themePreference, setThemePreference] = useThemePreference()
  const { toasts, notify, dismiss } = useToasts()
  const loadedSection = useRef<ShellSection | null>(null)

  const resetApproval = useCallback(() => {
    setApproval({ items: [], drafts: [], loading: true, error: '' })
  }, [])

  const connect = useCallback(async () => {
    setConnection('connecting')
    // 换库/重连时先清空审批清单，避免把上一个工作库的数量留在徽章上（§5.6 真实性）。
    resetApproval()

    try {
      const current = await api.get<Workspace>('/workspaces/current')
      setWorkspace(current)
      if (current.local_profile_dir) setProfileDir(current.local_profile_dir)
      setConnection('ready')
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'workspace_not_open') {
        setConnection('no-workspace')
        return
      }
      setConnection('unreachable')
    }
  }, [resetApproval])

  useEffect(() => { void connect() }, [connect])

  /** 视图的全局提示入口：默认失败色；取消/中性信息由调用方显式传 'neutral'。 */
  const report = useCallback((message: string, kind: ToastKind = 'danger') => {
    notify(message, kind)
  }, [notify])

  /** 侧栏徽章与审批页共用同一份清单，避免两处数字不一致。 */
  const refreshApproval = useCallback(async () => {
    setApproval((current) => ({ ...current, loading: true }))
    try {
      const [items, drafts] = await Promise.all([
        api.get<IntakeItem[]>('/intake/items'),
        api.get<Draft[]>('/drafts'),
      ])
      setApproval({ items, drafts, loading: false, error: '' })
    } catch {
      // 这里只做本机读取；失败文案保持白话，不外泄原始错误（§4.3、§13.4）。
      setApproval((current) => ({ ...current, loading: false, error: '现在读不出待处理的清单。本机服务可能刚刚重启。' }))
    }
  }, [])

  useEffect(() => {
    if (connection !== 'ready') {
      loadedSection.current = null
      return
    }
    const enteringApproval = section === 'approval' && loadedSection.current !== 'approval'
    if (loadedSection.current === null || enteringApproval) {
      loadedSection.current = section
      void refreshApproval()
    }
  }, [connection, section, refreshApproval])

  async function openPage(pageId: string, expectedHash?: string) {
    try {
      const query = expectedHash ? '?expected_content_sha256=' + expectedHash : ''
      setPage(await api.get<Page>('/pages/' + pageId + query))
    } catch (cause) {
      if (expectedHash && cause instanceof ApiError && cause.code === 'version_conflict') {
        try {
          setPage(await api.get<Page>('/pages/' + pageId))
          report('引用保存的是回答当时的页面版本；该页面已更新。当前显示的是新版本，不能替代原回答依据。')
          return
        } catch {
          setPage(null)
        }
      } else {
        setPage(null)
      }
      report(cause instanceof Error ? cause.message : '无法打开页面')
    }
  }

  function switchWorkspace() {
    setPage(null)
    setSection('today')
    setWorkspace(null)
    resetApproval()
    setConnection('no-workspace')
  }

  if (connection === 'connecting') return <ConnectingScreen />
  if (connection === 'unreachable') {
    return <ServiceUnreachableScreen onRetry={() => void connect()} profileDir={profileDir} />
  }
  if (connection === 'no-workspace' || !workspace) {
    return <WorkspaceGate onOpened={(opened) => {
      resetApproval()
      setWorkspace(opened)
      if (opened.local_profile_dir) setProfileDir(opened.local_profile_dir)
      setConnection('ready')
    }} />
  }

  return (
    <AppShell
      section={section}
      onSelect={(next) => { setPage(null); setSection(next) }}
      workspaceName={workspace.name}
      onSwitchWorkspace={switchWorkspace}
      approvalCount={approvalPendingCount(approval.items, approval.drafts)}
      openPageTitle={page ? String(page.metadata.title ?? '未命名页面') : null}
      themePreference={themePreference}
      onThemePreferenceChange={setThemePreference}
      toasts={toasts}
      onDismissToast={dismiss}
    >
      {page ? (
        <PageReader
          key={`${page.page_id}:${page.content_sha256}`}
          page={page}
          onClose={() => setPage(null)}
          onReload={() => void openPage(page.page_id)}
        />
      ) : section === 'today' ? (
        <TodayView onError={report} />
      ) : section === 'approval' ? (
        <ApprovalView
          items={approval.items}
          drafts={approval.drafts}
          loading={approval.loading}
          error={approval.error}
          onRetry={() => void refreshApproval()}
        />
      ) : section === 'projects' ? (
        <ProjectsView onError={report} onOpenPage={openPage} />
      ) : section === 'ask' ? (
        <AskView onError={report} onOpenPage={openPage} />
      ) : (
        <SettingsView
          workspaceName={workspace.name}
          onSwitchWorkspace={switchWorkspace}
          onOpenFeishuDaily={() => { setPage(null); setSection('today') }}
        />
      )}
    </AppShell>
  )
}
