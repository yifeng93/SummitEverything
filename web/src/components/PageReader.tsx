import { useEffect, useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { api, indexUpdateMessage, newOperationId, type MutationResult, type Page, type PageDirectoryEntry, type Project } from '../api/client'
import { ConfirmDialog } from './ConfirmDialog'
import { Drawer } from './Drawer'
import { MarkdownText, withoutDuplicateTitle, type MarkdownPage } from './MarkdownText'
import { PageTree } from './PageTree'
import { buildPageTree, findPageTrail } from '../page-groups'

type Props = {
  page: Page
  onClose: () => void
  onReload: () => Promise<void>
  onOpenPage: (id: string, hash: string) => void
  returnLabel?: string
  directoryRevision?: number
  synchronizing?: boolean
  /** 嵌在项目页右侧时传入：用外部数据、不渲染自己的左目录与返回行。 */
  pane?: { projects: Project[]; pages: PageDirectoryEntry[] }
}

/**
 * 页面阅读：左目录、右正文。`pane` 模式下嵌在项目页右侧，只渲染正文本身。
 *
 * 这里**只读**：不编辑、不新增正文。内容由外部来源写入，本应用负责发现变化、
 * 让用户确认当前版本、决定是否索引。唯一的写操作是「移动到其他项目」——
 * 它只改归属，不动正文。待确认页也只提供「确认当前版本」，没有编辑器。
 */
export function PageReader({ page, onClose, onReload, onOpenPage, returnLabel = '知识', pane, directoryRevision = 0, synchronizing = false }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [receipt, setReceipt] = useState<{ contentHash: string; message: string } | null>(null)
  const [loadedProjects, setLoadedProjects] = useState<Project[]>([])
  const [linkIndex, setLinkIndex] = useState<MarkdownPage[]>([])
  const [loadedPages, setLoadedPages] = useState<Page[]>([])
  const projects = pane?.projects ?? loadedProjects
  const allPages = pane?.pages ?? loadedPages
  const [loadingTree, setLoadingTree] = useState(!pane)
  const [moveProject, setMoveProject] = useState('')
  const [moveConfirmation, setMoveConfirmation] = useState<Project | null>(null)
  const [opsOpen, setOpsOpen] = useState(false)
  const [navigatorOpen, setNavigatorOpen] = useState(false)
  const needsConfirmation = page.approval_state !== 'confirmed'
  const projectId = String(page.metadata.project_id ?? '')
  const projectName = projects.find((project) => project.id === projectId)?.name
  const treePages = projectId ? allPages.filter((candidate) => String(candidate.metadata.project_id ?? '') === projectId) : allPages
  // 面包屑与翻页都按真实目录层级走：`官方文档 / 使用 / develop / basic`，不是压平的最后一段。
  const pageTree = buildPageTree(treePages)
  const trail = findPageTrail(pageTree, page.page_id) ?? []
  const location = trail.map((node) => node.label).join(' / ')
  // 同目录的相邻页：宽度不够、目录被收起来时，用上一篇/下一篇继续读，不必回列表。
  const siblings = [...(trail.at(-1)?.pages ?? [])].sort((a, b) => a.relative_path.localeCompare(b.relative_path, 'zh-CN'))
  const siblingIndex = siblings.findIndex((candidate) => candidate.page_id === page.page_id)
  const previousPage = siblingIndex > 0 ? siblings[siblingIndex - 1] : null
  const nextPage = siblingIndex >= 0 && siblingIndex < siblings.length - 1 ? siblings[siblingIndex + 1] : null
  /** 从目录或翻页跳转时先收起目录抽屉，否则用户仍对着抽屉，看不到刚打开的那篇。 */
  const openSibling = (id: string, hash: string) => { setNavigatorOpen(false); onOpenPage(id, hash) }
  const historicalValidity = page.validity === 'superseded'
    ? { label: '已被替代', description: '此页标记为已被替代，仅供历史参考，不作为当前问答依据。' }
    : page.validity === 'invalid'
      ? { label: '已失效', description: '此页标记为已失效，仅供历史参考，不作为当前问答依据。' }
      : null

  useEffect(() => {
    if (pane) {
      setLinkIndex(pane.pages.map((candidate) => ({ page_id: candidate.page_id, content_sha256: candidate.content_sha256, title: String(candidate.metadata.title ?? ''), relative_path: candidate.relative_path })))
      return
    }
    let cancelled = false
    void Promise.all([api.get<Project[]>('/projects'), api.get<Page[]>('/pages')]).then(([nextProjects, nextPages]) => {
      if (cancelled) return
      setLoadedProjects(nextProjects.filter((project) => !project.archived))
      setLinkIndex(nextPages.map((candidate) => ({ page_id: candidate.page_id, content_sha256: candidate.content_sha256, title: String(candidate.metadata.title ?? ''), relative_path: candidate.relative_path })))
      setLoadedPages(nextPages.filter((candidate) => candidate.storage_area === 'formal'))
      setLoadingTree(false)
    }).catch((cause) => {
      if (cancelled) return
      setLoadingTree(false)
      setError(cause instanceof Error ? cause.message : '无法加载页面操作')
    })
    return () => { cancelled = true }
  }, [page.page_id, pane, directoryRevision])

  async function confirmCurrentVersion() {
    setBusy(true)
    setError('')
    try {
      const result = await api.post<MutationResult>('/pages/' + page.page_id + '/confirmations', {
        metadata: page.metadata,
        body: page.body,
        confirmation_id: newOperationId(),
        operation_id: newOperationId(),
        expected_base_sha256: page.content_sha256,
      })
      setReceipt({
        contentHash: result.page_versions[page.page_id] ?? page.content_sha256,
        message: indexUpdateMessage(result.index_update) ?? '当前版本已确认并保存。',
      })
      await onReload()
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法确认此页面'
      setError(message.includes('changed since it was reviewed')
        ? '页面确认期间又发生了变化。请重新读取当前正文，检查后再确认。'
        : message)
    } finally {
      setBusy(false)
    }
  }

  async function moveToProject(destination: Project | null = moveConfirmation) {
    if (!destination) return
    setBusy(true)
    setError('')
    try {
      await api.post(`/pages/${page.page_id}/moves`, {
        destination_relative_path: `${destination.directory}/${page.relative_path.split('/').at(-1)}`,
        operation_id: newOperationId(),
        ...(destination.id !== projectId ? { structure_confirmation_id: newOperationId() } : {}),
      })
      setMoveConfirmation(null)
      setOpsOpen(false)
      await onReload()
      onClose()
    } catch (cause) { setError(cause instanceof Error ? cause.message : '无法移动页面') }
    finally { setBusy(false) }
  }

  const tree = <PageTree
    pages={treePages}
    currentPageId={page.page_id}
    heading={projectName ?? '知识目录'}
    loading={loadingTree}
    onOpenPage={openSibling}
  />

  // 文档自带的 H1 与页面标题相同时去掉，避免标题出现两次（待确认页保留，帮助核对原文）。
  const displayBody = needsConfirmation ? page.body : withoutDuplicateTitle(page.body, String(page.metadata.title ?? ''))
  const statusClass = needsConfirmation ? 'page-status-invalid' : historicalValidity ? 'page-status-historical' : ''
  const statusText = needsConfirmation
    ? historicalValidity ? `待确认 · ${historicalValidity.label}` : '待确认'
    : historicalValidity ? `已确认 · ${historicalValidity.label}` : '已确认知识'

  return <>
    <div className={pane ? 'page-reader-pane' : 'page-reader-layout'}>
      {!pane && <aside className="page-reader-side">{tree}</aside>}
      <article className="page-reader">
        {pane
          ? <div className="page-reader-topline">
            <div className="page-meta"><span className={statusClass}>{statusText}</span></div>
            <div className="page-reader-tools">
              {!needsConfirmation && <button className="text-button quiet" onClick={() => setOpsOpen(true)}>页面操作</button>}
            </div>
          </div>
          : <>
            <div className="page-reader-topline">
              <button className="back-link" onClick={onClose}><ArrowLeft size={15} strokeWidth={1.75} aria-hidden="true" />{returnLabel === '知识问答' ? '返回知识问答' : returnLabel === '项目' ? '返回项目' : '返回知识'}</button>
              <div className="page-reader-tools">
                <button className="text-button tree-toggle" onClick={() => setNavigatorOpen(true)}>目录</button>
                {!needsConfirmation && !synchronizing && <button className="text-button" onClick={() => setOpsOpen(true)}>页面操作</button>}
              </div>
            </div>
            <nav className="page-breadcrumb" aria-label="当前位置">{projectName ? `${projectName} / ${location}` : location}</nav>
            <div className="page-meta"><span className={statusClass}>{statusText}</span></div>
          </>}
        <h1>{needsConfirmation ? '检查页面当前版本' : String(page.metadata.title ?? '未命名页面')}</h1>
        {historicalValidity && <p role="status" className="page-validity-note">{historicalValidity.description}</p>}
        {synchronizing && <p role="status" className="helper-line">正在读取新版本；当前正文暂不能确认或操作。</p>}
        {needsConfirmation ? (
          <section className="page-reconfirmation" aria-label="重新确认当前页面">
            <p role="status">此页面自上次确认后已有变化，目前不会用于知识问答。请核对当前正文；只有点击确认后，新版本才会恢复检索资格。</p>
            <p className="helper-line">正文由外部来源写入，这里只读；需要改动请到来源文件，保存后回来重新确认。</p>
            {error && <p role="alert" className="form-error">{error}</p>}
            {error && <button className="text-button" onClick={() => void onReload()}>重新读取当前版本</button>}
            <MarkdownText className="page-body" content={displayBody} sourcePath={page.relative_path} pageIndex={linkIndex} onOpenPage={onOpenPage} />
            <div className="button-row">
              <button className="button primary" disabled={busy || synchronizing} onClick={() => void confirmCurrentVersion()}>
                {busy ? '正在确认…' : '确认当前版本'}
              </button>
            </div>
          </section>
        ) : <>
          {error && <p role="alert" className="form-error">{error}</p>}
          {receipt && <p role="status" className={receipt.message.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{receipt.contentHash === page.content_sha256 ? receipt.message : '先前版本已确认；页面内容已变化，当前版本需要重新确认。'}</p>}
          <MarkdownText className="page-body" content={displayBody} sourcePath={page.relative_path} pageIndex={linkIndex} onOpenPage={onOpenPage} />
          {(previousPage || nextPage) && <nav className="page-pager" aria-label="同分类翻页">
            <div>
              {previousPage && <button onClick={() => openSibling(previousPage.page_id, previousPage.content_sha256)}>
                <span>上一篇</span>
                <strong>{String(previousPage.metadata.title ?? '未命名页面')}</strong>
              </button>}
            </div>
            <div className="next">
              {nextPage && <button onClick={() => openSibling(nextPage.page_id, nextPage.content_sha256)}>
                <span>下一篇</span>
                <strong>{String(nextPage.metadata.title ?? '未命名页面')}</strong>
              </button>}
            </div>
          </nav>}
        </>}
      </article>
    </div>
    {navigatorOpen && <Drawer title="目录" description={projectName ? `${projectName} 的页面` : '知识库页面'} onClose={() => setNavigatorOpen(false)}>{tree}</Drawer>}
    {opsOpen && <Drawer
      title="页面操作"
      description="只调整归属；正文由外部来源写入，这里不编辑。"
      paused={Boolean(moveConfirmation)}
      onClose={() => setOpsOpen(false)}
    >
      <section className="drawer-section">
        <h3>归属</h3>
        <p className="drawer-note">当前在 {projectName ?? '未归属项目'}{location ? ` · ${location}` : ''}。移动只改变页面的主归属，正文和确认状态不变。</p>
        <label className="field"><span>移动到项目</span><select aria-label="移动到项目" value={moveProject} onChange={(event) => setMoveProject(event.target.value)}><option value="">选择项目</option>{projects.filter((project) => project.id !== projectId).map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}</select></label>
        <div className="drawer-actions"><button className="button primary" disabled={busy || !moveProject} onClick={() => setMoveConfirmation(projects.find((project) => project.id === moveProject) ?? null)}>移动页面</button></div>
      </section>
    </Drawer>}
    {moveConfirmation && <ConfirmDialog title={`将页面移动到“${moveConfirmation.name}”？`} description="页面会更改所属项目，正文和当前版本不会改变。" consequence="请确认目标项目正确后再继续。取消不会写入。" confirmLabel="确认移动页面" busyLabel="正在移动…" busy={busy} onCancel={() => setMoveConfirmation(null)} onConfirm={() => moveToProject(moveConfirmation)} />}
  </>
}
