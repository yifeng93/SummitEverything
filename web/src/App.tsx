import { useCallback, useEffect, useState } from 'react'
import { api, ApiError, type Page, type Workspace } from './api/client'
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
import { firstUseProgressKey, readFirstUseProgress } from './components/firstUseProgress'
import './App.css'

/**
 * 外壳状态机（逐页规格 §0「三态」）。
 * `connecting` / `unreachable` / `no-workspace` 必须分开：
 * 只有后端明确回答「还没有工作库」（409 `workspace_not_open`）才进首次配置向导；
 * 连不上或服务报错时显示就地提示，绝不冒充「还没有工作库」。
 */
type Connection = 'connecting' | 'ready' | 'no-workspace' | 'unreachable'
type FirstUseStep = 2 | 3 | 4 | 5

export default function App() {
  const [connection, setConnection] = useState<Connection>('connecting')
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [section, setSection] = useState<ShellSection>('today')
  const [firstUse, setFirstUse] = useState<{ open: boolean; step: FirstUseStep; returnSection: ShellSection }>({ open: false, step: 2, returnSection: 'today' })
  const [page, setPage] = useState<Page | null>(null)
  const [profileDir, setProfileDir] = useState<string | undefined>(undefined)
  const [approvalCount, setApprovalCount] = useState(0)
  const [approvalRefreshEpoch, setApprovalRefreshEpoch] = useState(0)
  const [todayCacheEpoch, setTodayCacheEpoch] = useState(0)
  const [themePreference, setThemePreference] = useThemePreference()
  const { toasts, notify, dismiss } = useToasts()
  const resetApproval = useCallback(() => setApprovalCount(0), [])

  const connect = useCallback(async () => {
    setConnection('connecting')
    // 换库/重连时先清空审批清单，避免把上一个工作库的数量留在徽章上（§5.6 真实性）。
    resetApproval()

    try {
      const current = await api.get<Workspace>('/workspaces/current')
      setWorkspace(current)
      if (current.local_profile_dir) setProfileDir(current.local_profile_dir)
      if (current.local_profile_dir && current.workspace_id) {
        const progress = readFirstUseProgress(firstUseProgressKey(current.local_profile_dir, current.workspace_id))
        if (progress?.open && !progress.completed) {
          setSection('settings')
          setFirstUse({ open: true, step: progress.step, returnSection: 'today' })
        }
      }
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
  const refreshApprovalAfterIntake = useCallback(() => setApprovalRefreshEpoch((value) => value + 1), [])
  const invalidateTodayAfterAuthorizationChange = useCallback(() => setTodayCacheEpoch((value) => value + 1), [])

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
    setFirstUse((current) => ({ ...current, open: false }))
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
      setPage(null)
      setSection('settings')
      setFirstUse({ open: true, step: 2, returnSection: 'today' })
      setConnection('ready')
    }} />
  }

  return (
    <AppShell
      section={section}
      onSelect={(next) => { setPage(null); setSection(next) }}
      workspaceName={workspace.name}
      onSwitchWorkspace={switchWorkspace}
      approvalCount={approvalCount}
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
        null
      ) : section === 'approval' ? (
        null
      ) : section === 'projects' ? (
        <ProjectsView onError={report} onOpenPage={openPage} />
      ) : section === 'ask' ? (
        <AskView onError={report} onOpenPage={openPage} />
      ) : (
        <SettingsView
          workspaceName={workspace.name}
          workspaceId={workspace.workspace_id}
          profileId={workspace.local_profile_dir ?? profileDir ?? 'default'}
          onSwitchWorkspace={switchWorkspace}
        wizardOnly={firstUse.open}
        initialWizardStep={firstUse.step}
        onRequestWizard={(step) => setFirstUse({ open: true, step, returnSection: section })}
        onWizardStepChange={(step) => setFirstUse((current) => ({ ...current, step }))}
        onWizardClose={() => { setFirstUse((current) => ({ ...current, open: false })); setPage(null); setSection(firstUse.returnSection) }}
        onFinishFirstUse={() => { setFirstUse((current) => ({ ...current, open: false })); setPage(null); setSection('today') }}
        onAuthorizationChanged={invalidateTodayAfterAuthorizationChange}
        />
      )}
      <div hidden={Boolean(page) || section !== 'today'}><TodayView key={`${profileDir ?? ''}:${workspace.workspace_id}:${todayCacheEpoch}`} onError={report} onOpenPage={(id) => void openPage(id)} onOpenApproval={() => setSection('approval')} onInboxChanged={refreshApprovalAfterIntake} onAuthorizationChanged={invalidateTodayAfterAuthorizationChange} /></div>
      <div hidden={Boolean(page) || section !== 'approval'}><ApprovalView key={`${workspace.workspace_id}:${approvalRefreshEpoch}`} onPendingCount={setApprovalCount} onError={report} onOpenPage={(title) => {
        void api.get<Page[]>('/pages').then((pages) => {
          const match = pages.find((candidate) => String(candidate.metadata.title ?? '') === title)
          if (match) void openPage(match.page_id)
          else report('找不到这条页面链接，请从项目目录中打开页面。', 'neutral')
        }).catch(() => report('无法读取页面目录'))
      }} /></div>
    </AppShell>
  )
}
