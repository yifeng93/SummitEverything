import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { api, ApiError, type Page, type Project, type Workspace } from './api/client'
import type { components } from './api/generated'
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
import type { ApprovalTarget } from './approvalTarget'
import { useThemePreference } from './theme'
import { useToasts, type ToastKind } from './toast'
import {
  firstUseProgressKey, resolveFirstUseProgress, saveFirstUseProgress, type FirstUseProgress,
} from './components/firstUseProgress'

/**
 * 外壳状态机（逐页规格 §0「三态」）。
 * `connecting` / `unreachable` / `no-workspace` 必须分开：
 * 只有后端明确回答「还没有工作库」（409 `workspace_not_open`）才进首次配置向导；
 * 连不上或服务报错时显示就地提示，绝不冒充「还没有工作库」。
 */
type Connection = 'connecting' | 'ready' | 'no-workspace' | 'unreachable'
type FirstUseStep = 2 | 3 | 4 | 5
type FirstUseState = { open: boolean; step: FirstUseStep; returnSection: ShellSection; completed: boolean }

export default function App() {
  const [connection, setConnection] = useState<Connection>('connecting')
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [section, setSection] = useState<ShellSection>('today')
  const [visitedSections, setVisitedSections] = useState<Set<ShellSection>>(() => new Set(['today', 'approval']))
  const [firstUse, setFirstUse] = useState<FirstUseState>({ open: false, step: 2, returnSection: 'today', completed: false })
  const [page, setPage] = useState<Page | null>(null)
  const [readerUnavailable, setReaderUnavailable] = useState(false)
  const [readerRefreshing, setReaderRefreshing] = useState(false)
  const readerFocusReturn = useRef<HTMLElement | null>(null)
  const readerOriginScroll = useRef(0)
  const [profileDir, setProfileDir] = useState<string | undefined>(undefined)
  const [approvalCount, setApprovalCount] = useState(0)
  const [approvalRefreshEpoch, setApprovalRefreshEpoch] = useState(0)
  const [externalPagesRevision, setExternalPagesRevision] = useState(0)
  const [externalWatchError, setExternalWatchError] = useState(false)
  const [readerRetryEpoch, setReaderRetryEpoch] = useState(0)
  const [readerRetryCount, setReaderRetryCount] = useState(0)
  const pageLoadRequest = useRef(0)
  const workspaceIdRef = useRef('')
  const pageIdRef = useRef('')
  const [runtimeSettingsEpoch, setRuntimeSettingsEpoch] = useState(0)
  const [approvalTarget, setApprovalTarget] = useState<ApprovalTarget | null>(null)
  const [approvalDirty, setApprovalDirty] = useState(false)
  const [approvalDiscardEpoch, setApprovalDiscardEpoch] = useState(0)
  const [todayCacheEpoch, setTodayCacheEpoch] = useState(0)
  /** 侧栏「项目」二级入口的数据源；只保留未归档项目。 */
  const [projects, setProjects] = useState<{ id: string; name: string }[]>([])
  const [projectsEpoch, setProjectsEpoch] = useState(0)
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null)
  const [projectTarget, setProjectTarget] = useState<{ id: string; nonce: number } | null>(null)
  const projectsHandle = useRef<{ showList: () => void } | null>(null)
  const projectNonce = useRef(0)
  const [themePreference, setThemePreference] = useThemePreference()
  useLayoutEffect(() => {
    workspaceIdRef.current = workspace?.workspace_id ?? ''
    pageIdRef.current = page?.page_id ?? ''
  }, [workspace?.workspace_id, page?.page_id])
  const { toasts, notify, dismiss } = useToasts()
  const resetApproval = useCallback(() => setApprovalCount(0), [])

  useEffect(() => {
    if (!approvalDirty) return
    const protectUnsavedDraft = (event: BeforeUnloadEvent) => {
      event.preventDefault()
      event.returnValue = ''
    }
    window.addEventListener('beforeunload', protectUnsavedDraft)
    return () => window.removeEventListener('beforeunload', protectUnsavedDraft)
  }, [approvalDirty])

  /** 视图的全局提示入口：默认失败色；取消/中性信息由调用方显式传 'neutral'。 */
  const report = useCallback((message: string, kind: ToastKind = 'danger') => {
    notify(message, kind)
  }, [notify])

  /**
   * 把本机记录翻译成外壳状态：
   * - 已完成：直接进今日，不再打扰；
   * - 未完成且向导还开着：恢复到保存的那一步；
   * - 用户明确关闭过：不自动出现，设置里仍能手动续接；
   * - 本机没有记录：新建工作库是首次使用，从第 2 步开始；但「打开已有」的
   *   工作库（例如旧版本配好的库）不猜已完成，也不把用户挡在向导后面——
   *   落到今日并用非阻塞提示指向设置（QA D-1）。
   * 这里绝不按「有凭据」推断首次配置已完成。
   */
  const applyResolvedFirstUse = useCallback(
    (progress: FirstUseProgress | null, mode: 'create' | 'open') => {
      if (progress === null) {
        const firstUse = mode === 'create'
        setSection(firstUse ? 'settings' : 'today')
        setFirstUse({ open: firstUse, step: 2, returnSection: 'today', completed: false })
        return
      }
      const resume = progress.open && !progress.completed
      setSection(resume ? 'settings' : 'today')
      setFirstUse({ open: resume, step: progress.step, returnSection: 'today', completed: progress.completed })
    },
    [],
  )

  /** 读本机进度（含旧浏览器副本的一次性迁移）。读不出来时不猜结果，只留在今日并说明。 */
  const resolveFirstUse = useCallback(async (current: Workspace, mode: 'create' | 'open') => {
    const key = firstUseProgressKey(current.local_profile_dir ?? 'default', current.workspace_id)
    try {
      const progress = await resolveFirstUseProgress(key)
      applyResolvedFirstUse(progress, mode)
      if (progress === null && mode === 'open') {
        report('这个工作库在本机还没有首次配置记录。需要配置真实模型或飞书时，可从设置里打开连接向导。', 'neutral')
      }
    } catch (cause) {
      report('无法读取首次配置进度：' + (cause instanceof Error ? cause.message : '本机没有返回结果') + ' 已留在今日，可在设置里重新打开向导。')
      applyResolvedFirstUse({ step: 2, completed: false, open: false }, mode)
    }
  }, [applyResolvedFirstUse, report])

  /** 向导的每次状态变化都先写本机；只有确认落地才更新外壳状态。 */
  const persistFirstUseProgress = useCallback(async (progress: FirstUseProgress) => {
    try {
      await saveFirstUseProgress(progress)
    } catch {
      return false
    }
    setFirstUse((current) => ({ ...current, step: progress.step, completed: progress.completed }))
    return true
  }, [])

  const connect = useCallback(async () => {
    setConnection('connecting')
    // 换库/重连时先清空审批清单，避免把上一个工作库的数量留在徽章上（§5.6 真实性）。
    resetApproval()

    try {
      const current = await api.get<Workspace>('/workspaces/current')
      setWorkspace(current)
      if (current.local_profile_dir) setProfileDir(current.local_profile_dir)
      // 页面重载时工作库已经开着；没有记录也不当成首次使用（见 QA D-1）。
      await resolveFirstUse(current, 'open')
      setConnection('ready')
    } catch (cause) {
      if (cause instanceof ApiError && cause.code === 'workspace_not_open') {
        setConnection('no-workspace')
        return
      }
      setConnection('unreachable')
    }
  }, [resetApproval, resolveFirstUse])

  useEffect(() => { void connect() }, [connect])

  const activeReaderPageId = page?.page_id
  const activeWorkspaceId = workspace?.workspace_id
  useEffect(() => {
    if (!activeReaderPageId || externalPagesRevision === 0 || !activeWorkspaceId) return
    const pageId = activeReaderPageId
    const workspaceId = activeWorkspaceId
    const controller = new AbortController()
    const deadline = window.setTimeout(() => controller.abort(), 5000)
    let cancelled = false
    setReaderRefreshing(true)
    void api.get<Page>(`/pages/${pageId}`, { signal: controller.signal }).then((latest) => {
      if (!controller.signal.aborted && workspaceIdRef.current === workspaceId && pageIdRef.current === pageId) {
        setPage(latest)
        setReaderUnavailable(false)
        setReaderRefreshing(false)
        setReaderRetryCount(0)
      }
    }).catch(() => {
      if (!cancelled && workspaceIdRef.current === workspaceId && pageIdRef.current === pageId) {
        setReaderUnavailable(true)
        setReaderRefreshing(false)
      }
    }).finally(() => window.clearTimeout(deadline))
    return () => { cancelled = true; controller.abort(); window.clearTimeout(deadline) }
  }, [activeReaderPageId, activeWorkspaceId, externalPagesRevision, readerRetryEpoch])

  useEffect(() => {
    if (!readerUnavailable || readerRetryCount >= 2) return
    const retry = window.setTimeout(() => {
      setReaderRetryCount((value) => value + 1)
      setReaderRetryEpoch((value) => value + 1)
    }, 1500)
    return () => window.clearTimeout(retry)
  }, [readerUnavailable, readerRetryEpoch, readerRetryCount])

  // Poll directory metadata sequentially; each successful revision change triggers one targeted refresh.
  useEffect(() => {
    if (!workspace) return
    let baseline: string | null = null
    let active = true
    let timer = 0
    let inFlight: AbortController | null = null
    let hadFailure = false
    let pendingRefresh = 0
    const scheduleRefresh = () => {
      if (!pendingRefresh) pendingRefresh = window.setTimeout(() => {
        pendingRefresh = 0
        setExternalPagesRevision((value) => value + 1)
      }, 300)
    }
    const poll = async () => {
      const controller = new AbortController()
      inFlight = controller
      const deadline = window.setTimeout(() => controller.abort(), 3000)
      try {
        const result = await api.get<components['schemas']['WorkspacePagesRevision']>('/pages/revision', {
          signal: controller.signal, cache: 'no-store', headers: { 'X-Summit-Workspace-Id': workspace.workspace_id },
        })
        if (!active) return
        if (result.workspace_id !== workspace.workspace_id) throw new Error('workspace changed')
        setExternalWatchError(false)
        if (baseline === null) {
          baseline = result.revision
          scheduleRefresh()
        }
        else if (result.revision !== baseline) {
          baseline = result.revision
          scheduleRefresh()
        }
        if (hadFailure) scheduleRefresh()
        hadFailure = false
      } catch {
        if (!active) return
        hadFailure = true
        setExternalWatchError(true)
      } finally {
        window.clearTimeout(deadline)
        if (inFlight === controller) inFlight = null
        if (active) timer = window.setTimeout(() => { void poll() }, 1500)
      }
    }
    void poll()
    return () => {
      active = false
      window.clearTimeout(timer)
      window.clearTimeout(pendingRefresh)
      inFlight?.abort()
    }
  }, [workspace?.workspace_id, profileDir])

  /** 侧栏二级入口只依赖项目名与 id；失败时留空，不冒充「没有项目」。 */
  useEffect(() => {
    if (connection !== 'ready') return
    let cancelled = false
    void api.get<Project[]>('/projects').then((rows) => {
      if (!cancelled) setProjects(rows.filter((project) => !project.archived).map((project) => ({ id: project.id, name: project.name })))
    }).catch(() => { if (!cancelled) setProjects([]) })
    return () => { cancelled = true }
  }, [connection, projectsEpoch, workspace?.workspace_id])

  const refreshSidebarProjects = useCallback(() => setProjectsEpoch((value) => value + 1), [])

  /** 侧栏点项目：和点导航一样先处理未保存稿件，再直接落到那个项目的详情。 */
  const openProjectShortcut = useCallback((projectId: string) => {
    if (section === 'approval' && approvalDirty) {
      if (!window.confirm('稿件有未保存的修改。离开审批会放弃这些修改，是否继续？')) return
      setApprovalDirty(false)
      setApprovalDiscardEpoch((value) => value + 1)
    }
    projectNonce.current += 1
    pageLoadRequest.current += 1
    setPage(null)
    setProjectTarget({ id: projectId, nonce: projectNonce.current })
    setSection('projects')
    setVisitedSections((current) => new Set(current).add('projects'))
  }, [section, approvalDirty])

  /**
   * 打开工作库：先解析本机进度再决定落点，避免先闪一下今日又弹向导。
   * 不自动打开上次的工作库，也不按凭据猜测首次配置是否完成。
   */
  const openWorkspace = useCallback(async (opened: Workspace, mode: 'create' | 'open') => {
    resetApproval()
    setWorkspace(opened)
    if (opened.local_profile_dir) setProfileDir(opened.local_profile_dir)
    pageLoadRequest.current += 1
    setPage(null)
    setApprovalTarget(null)
    setProjectTarget(null)
    setActiveProjectId(null)
    setConnection('connecting')
    await resolveFirstUse(opened, mode)
    setConnection('ready')
  }, [resetApproval, resolveFirstUse])

  const refreshApprovalAfterIntake = useCallback(() => setApprovalRefreshEpoch((value) => value + 1), [])
  const refreshApprovalAfterSettingsChange = useCallback(() => {
    setApprovalRefreshEpoch((value) => value + 1)
    setRuntimeSettingsEpoch((value) => value + 1)
  }, [])
  const clearProjectTarget = useCallback(() => setProjectTarget(null), [])
  const openApproval = useCallback((target?: ApprovalTarget) => {
    setApprovalTarget(target ?? null)
    setSection('approval')
    setVisitedSections((current) => new Set(current).add('approval'))
  }, [])
  const clearApprovalTarget = useCallback(() => setApprovalTarget(null), [])
  const invalidateTodayAfterAuthorizationChange = useCallback(() => setTodayCacheEpoch((value) => value + 1), [])

  /** 换页（阅读页里点目录/上一篇）总是回到正文顶部；关闭阅读时再还原原来的列表位置。 */
  function showPage(next: Page) {
    setPage(next)
    setReaderUnavailable(false)
    setReaderRefreshing(false)
    setReaderRetryCount(0)
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
  }

  async function openPage(pageId: string, expectedHash?: string) {
    const request = ++pageLoadRequest.current
    const requestedWorkspaceId = workspaceIdRef.current
    if (section === 'approval' && approvalDirty) {
      if (!window.confirm('稿件有未保存的修改。离开审批会放弃这些修改，是否继续？')) return
      setApprovalDirty(false)
      setApprovalDiscardEpoch((value) => value + 1)
    }
    if (!page) {
      readerFocusReturn.current = document.activeElement instanceof HTMLElement ? document.activeElement : null
      readerOriginScroll.current = window.scrollY || document.documentElement.scrollTop
    }
    const controller = new AbortController()
    const deadline = window.setTimeout(() => controller.abort(), 5000)
    try {
      const query = expectedHash ? '?expected_content_sha256=' + expectedHash : ''
      const loadedPage = await api.get<Page>('/pages/' + pageId + query, { signal: controller.signal })
      if (request === pageLoadRequest.current && workspaceIdRef.current === requestedWorkspaceId) showPage(loadedPage)
    } catch (cause) {
      if (request !== pageLoadRequest.current || workspaceIdRef.current !== requestedWorkspaceId) return
      if (expectedHash && cause instanceof ApiError && cause.code === 'version_conflict') {
        try {
          const latestPage = await api.get<Page>('/pages/' + pageId, { signal: controller.signal })
          if (request !== pageLoadRequest.current || workspaceIdRef.current !== requestedWorkspaceId) return
          showPage(latestPage)
          report('引用保存的是回答当时的页面版本；该页面已更新。当前显示的是新版本，不能替代原回答依据。')
          return
        } catch {
          if (request !== pageLoadRequest.current || workspaceIdRef.current !== requestedWorkspaceId) return
          setPage(null)
        }
      } else {
        setPage(null)
      }
      report(cause instanceof Error ? cause.message : '无法打开页面')
    } finally {
      window.clearTimeout(deadline)
    }
  }

  function closeReader() {
    pageLoadRequest.current += 1
    setPage(null)
    setReaderUnavailable(false)
    setReaderRefreshing(false)
    requestAnimationFrame(() => {
      document.documentElement.scrollTop = readerOriginScroll.current
      document.body.scrollTop = readerOriginScroll.current
      readerFocusReturn.current?.focus({ preventScroll: true })
    })
  }

  function switchWorkspace() {
    if (section === 'approval' && approvalDirty) {
      if (!window.confirm('稿件有未保存的修改。切换工作库会放弃这些修改，是否继续？')) return
      setApprovalDirty(false)
    }
    setFirstUse((current) => ({ ...current, open: false }))
    pageLoadRequest.current += 1
    setPage(null)
    setApprovalTarget(null)
    setProjectTarget(null)
    setActiveProjectId(null)
    setProjects([])
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
    return <WorkspaceGate onOpened={(opened, mode) => void openWorkspace(opened, mode)} />
  }

  return (
    <AppShell
      section={section}
      onSelect={(next) => {
        if (section === 'approval' && next !== 'approval' && approvalDirty) {
          if (!window.confirm('稿件有未保存的修改。离开审批会放弃这些修改，是否继续？')) return
          setApprovalDirty(false)
          setApprovalDiscardEpoch((value) => value + 1)
        }
        pageLoadRequest.current += 1
        setPage(null); setSection(next); setVisitedSections((current) => new Set(current).add(next))
        // 点一级导航「项目」永远回到项目列表。
        if (next === 'projects') projectsHandle.current?.showList()
      }}
      workspaceName={workspace.name}
      onSwitchWorkspace={switchWorkspace}
      approvalCount={approvalCount}
      projects={projects}
      activeProjectId={activeProjectId}
      onOpenProject={openProjectShortcut}
      themePreference={themePreference}
      onThemePreferenceChange={setThemePreference}
      toasts={toasts}
      onDismissToast={dismiss}
    >
      {externalWatchError && <p className="content-wrap" role="status">自动检查暂时不可用，当前内容可能不是最新版本；连接恢复后会继续检查。</p>}
      {page ? readerUnavailable ? (
        <div className="content-wrap" role="alert"><h1>{String(page.metadata.title ?? '页面')}</h1><p>这个页面已删除或暂时无法读取。修复文件后会自动恢复显示。</p><button className="button secondary" onClick={() => void openPage(page.page_id)}>重新读取</button><button className="text-button" onClick={closeReader}>返回</button></div>
      ) : (
        <PageReader
          key={page.page_id}
          page={page}
          directoryRevision={externalPagesRevision}
          synchronizing={readerRefreshing}
          onClose={closeReader}
          onReload={() => void openPage(page.page_id)}
          onOpenPage={(id, expectedHash) => void openPage(id, expectedHash)}
          returnLabel={section === 'ask' ? '知识问答' : section === 'projects' ? '项目' : '知识'}
        />
      ) : section === 'today' ? (
        null
      ) : section === 'approval' ? (
        null
      ) : section === 'settings' ? (
        <SettingsView
          workspaceName={workspace.name}
          workspaceId={workspace.workspace_id}
          profileId={workspace.local_profile_dir ?? profileDir ?? 'default'}
          onSwitchWorkspace={switchWorkspace}
          onOpenApproval={openApproval}
          onError={report}
        wizardOnly={firstUse.open}
        initialWizardStep={firstUse.step}
        resumeWizardStep={firstUse.step}
        initialWizardCompleted={firstUse.completed}
        persistWizardProgress={persistFirstUseProgress}
        onRequestWizard={(step) => setFirstUse((current) => ({ ...current, open: true, step, returnSection: section }))}
        onWizardStepChange={(step) => setFirstUse((current) => ({ ...current, step }))}
        onWizardClose={() => { setFirstUse((current) => ({ ...current, open: false })); setPage(null); setSection(firstUse.returnSection) }}
        onFinishFirstUse={() => { setFirstUse((current) => ({ ...current, open: false })); setPage(null); setSection('today') }}
        onAuthorizationChanged={invalidateTodayAfterAuthorizationChange}
        onRuntimeSettingsChanged={refreshApprovalAfterSettingsChange}
        />
      ) : null}
      <div hidden={Boolean(page) || section !== 'projects'}>{visitedSections.has('projects') && <ProjectsView key={workspace.workspace_id} externalPagesRevision={externalPagesRevision} handleRef={projectsHandle} onError={report} onOpenPage={(id, expectedHash) => void openPage(id, expectedHash)} target={projectTarget} onTargetHandled={clearProjectTarget} onActiveProjectChange={setActiveProjectId} onProjectsChanged={refreshSidebarProjects} />}</div>
      <div hidden={Boolean(page) || section !== 'ask'}>{visitedSections.has('ask') && <AskView key={workspace.workspace_id} active={!page && section === 'ask'} settingsEpoch={runtimeSettingsEpoch} onError={report} onOpenPage={(id, expectedHash) => void openPage(id, expectedHash)} onOpenApproval={openApproval} onOpenSettings={() => { setPage(null); setSection('settings'); setVisitedSections((current) => new Set(current).add('settings')) }} />}</div>
      <div hidden={Boolean(page) || section !== 'today'}><TodayView key={`${profileDir ?? ''}:${workspace.workspace_id}:${todayCacheEpoch}`} calendarDedupeScope={`${profileDir ?? ''}:${workspace.workspace_id}`} onError={report} onOpenPage={(id) => void openPage(id)} onOpenApproval={openApproval} onInboxChanged={refreshApprovalAfterIntake} onAuthorizationChanged={invalidateTodayAfterAuthorizationChange} onOpenConnectionWizard={() => { setFirstUse((current) => ({ ...current, open: true, step: 4, returnSection: 'today' })); setSection('settings'); setVisitedSections((current) => new Set(current).add('settings')) }} /></div>
      <div hidden={Boolean(page) || section !== 'approval'}><ApprovalView key={workspace.workspace_id} externalPagesRevision={externalPagesRevision} refreshEpoch={approvalRefreshEpoch} target={approvalTarget} onTargetHandled={clearApprovalTarget} onPendingCount={setApprovalCount} onDirtyChange={setApprovalDirty} discardEpoch={approvalDiscardEpoch} onError={report} onOpenPage={(pageId, expectedHash) => void openPage(pageId, expectedHash)} /></div>
    </AppShell>
  )
}
