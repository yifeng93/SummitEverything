import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { ArrowLeft, ArrowUpRight, Loader2, MessageSquarePlus, Sparkles } from 'lucide-react'
import { api, ApiError, sessionHeaders, type Citation, type IndexStatus, type Page } from '../api/client'
import type { components } from '../api/generated'
import { ConfirmDialog } from './ConfirmDialog'
import { StreamingMarkdown } from './StreamingMarkdown'
import { PageHeader } from './PageHeader'

type Props = { onError: (message: string) => void; onOpenPage: (id: string, hash?: string) => void; onOpenApproval?: () => void; onOpenSettings?: () => void; settingsEpoch?: number; active?: boolean }
type StreamEvent = {
  request_id: string
  seq: number
  type: 'status' | 'citation' | 'delta' | 'completed' | 'error'
  data: Record<string, unknown>
}
type Settings = components['schemas']['SettingsSummary']
type AcceptancePlan = { plan_id: string; scope_sha256: string; request_limit: number }
type PendingQuery = { plan: AcceptancePlan; scope: Record<string, unknown>; body: Record<string, unknown> }
type Conversation = components['schemas']['ConversationDetail']
type Summary = Omit<Conversation, 'messages'>
type QueryState = 'idle' | 'running' | 'completed' | 'error' | 'cancelled' | 'interrupted'
type AnswerMode = 'fact' | 'comparison' | 'plan'
type RetrievalPurpose = 'current' | 'history'
type AnswerRole = components['schemas']['AnswerRole']
type PendingDelete = { kind: 'conversation'; id: string; label: string }

/*
 * 已读过的对话放在内存里：再点同一条先铺上次的内容，再去后端静默刷新。
 * 只缓存本会话看过的（最多 20 段），刷新页面即清空。
 */
const conversationCache = new Map<string, Conversation>()
const CACHE_LIMIT = 20
export function clearConversationCacheForTests() {
  conversationCache.clear()
}

function rememberConversation(next: Conversation) {
  conversationCache.delete(next.conversation_id)
  conversationCache.set(next.conversation_id, next)
  if (conversationCache.size > CACHE_LIMIT) {
    const oldest = conversationCache.keys().next().value
    if (oldest) conversationCache.delete(oldest)
  }
}
const querySetupErrorCodes = new Set([
  'provider_disabled', 'local_model_not_ready', 'local_provider_required', 'legacy_provider_migration_required',
])

function queryProviderGaps(settings: Settings, index: IndexStatus | null): string[] {
  const gaps: string[] = []
  if (settings.mode !== 'real') gaps.push('旧离线配置尚未迁移到真实服务')
  if (settings.legacy_provider_migration_required) gaps.push('旧模型设置已转为真实服务；请检查密钥与本地检索准备状态')
  if (!settings.keychain_available) gaps.push('本机钥匙串不可用')
  if (settings.llm.provider === 'fake') gaps.push('整理与问答模型仍为离线试用')
  else if (!settings.llm.enabled) gaps.push('整理与问答模型未启用')
  else if (!settings.llm.model) gaps.push('整理与问答模型未选定')
  else if (!settings.credential_status?.deepseek) gaps.push('缺少 DeepSeek 本机密钥')
  if (settings.embedding.provider === 'local' && settings.rerank.provider === 'local') {
    if (!settings.embedding.enabled || !settings.rerank.enabled) gaps.push('本地检索尚未启用')
    else if (!settings.embedding.model || !settings.rerank.model) gaps.push('本地检索模型尚未选定')
    else if (settings.local_model?.state !== 'ready') gaps.push('本地检索模型尚未准备')
  } else if (settings.embedding.provider === 'dashscope' || settings.rerank.provider === 'dashscope') {
    gaps.push('旧云端检索设置已停用，请切换到本地检索')
  } else {
    if (settings.embedding.provider === 'fake') gaps.push('知识索引向量化仍为离线试用')
    else if (!settings.embedding.enabled) gaps.push('知识索引向量化未启用')
    else if (!settings.embedding.model) gaps.push('知识索引向量化未选定')
    if (settings.rerank.provider === 'fake') gaps.push('检索结果排序仍为离线试用')
    else if (!settings.rerank.enabled) gaps.push('检索结果排序未启用')
    else if (!settings.rerank.model) gaps.push('检索结果排序未选定')
  }
  if (!index || index.state !== 'ready' || index.vector !== 'real' || index.fingerprint !== settings.embedding_fingerprint) {
    gaps.push('本地索引尚未就绪或待更新')
  } else if (index.current_pages === 0 || index.pages === 0 || index.chunks === 0) {
    gaps.push('还没有可检索的已确认资料')
  }
  return gaps
}
const answerModeLabel: Record<AnswerMode, string> = {
  fact: '事实问答', comparison: '跨材料比较', plan: '工作方案',
}

const stateLabel: Record<QueryState, string> = {
  idle: '尚未提问',
  running: '正在回答',
  completed: '已完成',
  error: '回答失败',
  cancelled: '已取消',
  interrupted: '连接中断',
}

export function AskView({ onError, onOpenPage, onOpenSettings, onOpenApproval, settingsEpoch = 0, active = true }: Props) {
  const [eligiblePages, setEligiblePages] = useState<Page[]>([])
  const [providerSettings, setProviderSettings] = useState<Settings | null>(null)
  const [indexStatus, setIndexStatus] = useState<IndexStatus | null>(null)
  const [providerSettingsError, setProviderSettingsError] = useState('')
  const [providerSettingsLoading, setProviderSettingsLoading] = useState(true)
  const [pendingQuery, setPendingQuery] = useState<PendingQuery | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [citations, setCitations] = useState<Citation[]>([])
  const [streaming, setStreaming] = useState(false)
  const [requestId, setRequestId] = useState('')
  const [conversationId, setConversationId] = useState('')
  const [history, setHistory] = useState<Summary[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)
  const [historyError, setHistoryError] = useState('')
  const [historyCursor, setHistoryCursor] = useState<string | null>(null)
  const [thread, setThread] = useState<Conversation | null>(null)
  const [queryState, setQueryState] = useState<QueryState>('idle')
  const [notice, setNotice] = useState('')
  const [needsModelSetup, setNeedsModelSetup] = useState(false)
  const [needsIndexPreparation, setNeedsIndexPreparation] = useState(false)
  const [answerMode, setAnswerMode] = useState<AnswerMode>('fact')
  const [retrievalPurpose, setRetrievalPurpose] = useState<RetrievalPurpose>('current')
  const [roles, setRoles] = useState<AnswerRole[]>([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [memoryAttestations, setMemoryAttestations] = useState<Record<string, boolean>>({})
  const [answerDetails, setAnswerDetails] = useState<Pick<components['schemas']['Answer'], 'source_statements' | 'inferences' | 'advice' | 'missing_information'> | null>(null)
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const [openingId, setOpeningId] = useState('')
  const [composing, setComposing] = useState(false)
  const openingRef = useRef('')
  const openSeq = useRef(0)
  const revalidating = useRef(new Set<string>())
  const abortController = useRef<AbortController | null>(null)
  const historyCursorRef = useRef<string | null>(null)
  const approvedQuery = useRef<{ planId: string; body: Record<string, unknown> } | null>(null)
  const queryForm = useRef<HTMLFormElement | null>(null)
  const previousSettingsEpoch = useRef(settingsEpoch)
  const settingsReadSequence = useRef(0)

  const loadQueryReadiness = useCallback(async () => {
    const sequence = ++settingsReadSequence.current
    setProviderSettingsLoading(true)
    setProviderSettingsError('')
    try {
      const [settings, index] = await Promise.all([
        api.get<Settings>('/settings'),
        api.get<IndexStatus>('/index/status'),
      ])
      if (settingsReadSequence.current === sequence) {
        setProviderSettings(settings)
        setIndexStatus(index)
      }
    } catch (cause) {
      if (settingsReadSequence.current === sequence) {
        setProviderSettingsError(cause instanceof Error ? cause.message : '无法读取真实服务状态')
      }
    } finally {
      if (settingsReadSequence.current === sequence) setProviderSettingsLoading(false)
    }
  }, [])

  const refreshHistory = useCallback(async (append = false) => {
    setHistoryLoading(true)
    setHistoryError('')
    try {
      const cursor = append ? historyCursorRef.current : null
      const query = new URLSearchParams({ limit: '20' })
      if (cursor) query.set('cursor', cursor)
      const page = await api.get<{ items: Summary[]; next_cursor: string | null }>(`/conversations?${query}`)
      setHistory((current) => append ? [...current, ...page.items] : page.items)
      historyCursorRef.current = page.next_cursor
      setHistoryCursor(page.next_cursor)
      setHistoryError('')
    } catch (cause) {
      setHistoryError(cause instanceof Error ? cause.message : '无法读取问答历史')
      onError(cause instanceof Error ? cause.message : '无法读取问答历史')
    } finally {
      setHistoryLoading(false)
    }
  }, [onError])

  const refreshRoles = useCallback(async () => {
    try {
      setRoles(await api.get<AnswerRole[]>('/roles'))
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法读取问答角色')
    }
  }, [onError])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void api.get<Page[]>('/pages').then(setEligiblePages).catch(() => undefined)
      void refreshHistory()
      void refreshRoles()
    }, 0)
    return () => window.clearTimeout(timer)
  }, [refreshHistory, refreshRoles])

  useEffect(() => {
    if (!active) return
    void loadQueryReadiness()
    return () => { settingsReadSequence.current += 1 }
  }, [active, loadQueryReadiness, settingsEpoch])

  const providerGaps = providerSettings ? queryProviderGaps(providerSettings, indexStatus) : []
  const queryReadinessBlocked = providerSettingsLoading || Boolean(providerSettingsError) || providerGaps.length > 0

  useEffect(() => {
    if (previousSettingsEpoch.current === settingsEpoch) return
    previousSettingsEpoch.current = settingsEpoch
    if (!pendingQuery) return
    approvedQuery.current = null
    setPendingQuery(null)
    setNotice('模型或搜索设置已变化。请重新检查当前问题的发送范围。')
  }, [settingsEpoch, pendingQuery])

  function applyConversation(next: Conversation) {
    setThread(next)
    setConversationId(next.conversation_id)
    setQueryState(next.state)
    const latest = next.messages.at(-1)
    setAnswer(latest?.answer ?? '')
    setCitations(latest?.citations ?? [])
    setAnswerDetails(latest ? {
      source_statements: latest.source_statements ?? [],
      inferences: latest.inferences ?? [], advice: latest.advice ?? [],
      missing_information: latest.missing_information ?? [],
    } : null)
    if (latest?.answer_mode) setAnswerMode(latest.answer_mode)
    setRetrievalPurpose(latest?.purpose === 'history' ? 'history' : 'current')
    setNotice(latest?.state === 'interrupted'
      ? '上次连接中断，已保留收到的部分内容（不会自动重试）。'
      : '')
    setRequestId(latest?.request_id ?? '')
    setQuestion('')
    onError('')
  }

  async function openConversation(id: string) {
    // 打开一段历史要等后端重放，期间必须给反馈，也避免连点重复请求。
    // 用 ref 拦截同一帧内的连续点击（state 更新是异步的）。
    if (openingRef.current) return
    const seq = ++openSeq.current
    const cached = conversationCache.get(id)
    if (cached) {
      // 先铺上次的内容，不显示 loading；随后静默换成最新版本。
      applyConversation(cached)
      if (revalidating.current.has(id)) return
      revalidating.current.add(id)
      void api.post<Conversation>(`/conversations/${id}/reopen`, {}).then((fresh) => {
        rememberConversation(fresh)
        if (openSeq.current === seq) applyConversation(fresh)
      }).catch(() => undefined).finally(() => { revalidating.current.delete(id) })
      return
    }
    openingRef.current = id
    setOpeningId(id)
    try {
      const next = await api.post<Conversation>(`/conversations/${id}/reopen`, {})
      rememberConversation(next)
      if (openSeq.current === seq) applyConversation(next)
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法打开问答历史')
    } finally {
      openingRef.current = ''
      setOpeningId('')
    }
  }

  function startNewConversation() {
    openSeq.current += 1
    setThread(null)
    setConversationId('')
    setRequestId('')
    setQuestion('')
    setAnswer('')
    setCitations([])
    setAnswerDetails(null)
    setQueryState('idle')
    setRetrievalPurpose('current')
    setNotice('')
    setNeedsModelSetup(false)
    setNeedsIndexPreparation(false)
    setAnswerDetails(null)
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    try {
      await api.delete(`/conversations/${pendingDelete.id}`)
      conversationCache.delete(pendingDelete.id)
      setHistory((current) => current.filter((item) => item.conversation_id !== pendingDelete.id))
      if (conversationId === pendingDelete.id) startNewConversation()
      await refreshHistory()
      setPendingDelete(null)
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '无法完成删除')
    }
  }

  async function proposeMemory(message: Conversation['messages'][number]) {
    if (!memoryAttestations[message.request_id]) return
    try {
      await api.post('/memory/candidates', {
        message_id: message.request_id, text: message.question, user_expression: true,
      })
      setMemoryAttestations((current) => ({ ...current, [message.request_id]: false }))
      onError('')
    } catch (cause) {
      onError(cause instanceof Error ? cause.message : '这句内容不能作为记忆候选')
    }
  }

  async function ask(event: FormEvent) {
    event.preventDefault()
    openSeq.current += 1
    if (!question.trim() || streaming) return
    const controller = new AbortController()
    const approved = approvedQuery.current
    const queryId = typeof approved?.body.request_id === 'string' ? approved.body.request_id : crypto.randomUUID()
    let targetConversation = typeof approved?.body.conversation_id === 'string' ? approved.body.conversation_id : conversationId
    abortController.current = controller
    let queryRequestDispatched = false
    let queryResponseAccepted = false
    setNeedsIndexPreparation(false)
    setStreaming(true)
    setQueryState('running')
    setAnswer('')
    setCitations([])
    setAnswerDetails(null)
    setRequestId(queryId)
    if (targetConversation) setConversationId(targetConversation)
    setNotice('')
    setNeedsModelSetup(false)
    onError('')
    try {
      const [settings, index] = await Promise.all([api.get<Settings>('/settings'), api.get<IndexStatus>('/index/status')])
      if (!approved) {
        const gaps = queryProviderGaps(settings, index)
        if (gaps.length) {
          setQueryState('error')
          setNeedsModelSetup(true)
          setNotice(`真实问答暂不可用：${gaps.join('；')}。请到设置检查模型配置与本地检索准备状态；问题仍保留在输入框中。`)
          return
        }
      }
      const body: Record<string, unknown> = approved?.body ?? {
        question,
        ...(targetConversation ? { conversation_id: targetConversation } : {}),
        fingerprint: settings.embedding_fingerprint,
        purpose: retrievalPurpose,
        answer_mode: answerMode,
        ...(selectedRoleId ? { role_id: selectedRoleId } : {}),
        request_id: queryId,
      }
      if (settings.mode === 'real' && !approved) {
        const preview = await api.post<{ plan: AcceptancePlan; scope: Record<string, unknown> }>('/acceptance-plans', {
          operation: 'model.query', scope: body,
        })
        setPendingQuery({ ...preview, body })
        setQueryState('idle')
        setNotice('请先检查将发送的问题、历史、角色/记忆上下文和页面版本，再独立确认。')
        return
      }
      if (approved) body.acceptance_plan_id = approved.planId
      approvedQuery.current = null
      queryRequestDispatched = true
      const response = await fetch('/api/v1/queries', {
        method: 'POST',
        headers: sessionHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body),
        signal: controller.signal,
      })
      if (!response.ok) {
        const failure = await response.json().catch(() => null) as { error?: { code?: string; message?: string } } | null
        setQueryState('error')
        setNotice(failure?.error?.code === 'provider_disabled'
          ? `本次问题尚未发送：${failure.error.message ?? '所需 AI 服务尚未启用。'}`
          : failure?.error?.message ?? '问题未被接受；请检查输入后重试。')
        setNeedsModelSetup(Boolean(failure?.error?.code && querySetupErrorCodes.has(failure.error.code)))
        setNeedsIndexPreparation(failure?.error?.code === 'index_not_ready')
        return
      }
      queryResponseAccepted = true
      if (!response.body) throw new Error('问答服务没有返回内容；请从本机历史确认保存状态后再继续。')
      setQuestion('')
      setComposing(false)
      const responseConversation = response.headers.get('X-Conversation-ID')
      if (responseConversation) {
        if (targetConversation && responseConversation !== targetConversation) {
          throw new Error('问答流返回了不匹配的会话；已保留本机历史。')
        }
        targetConversation = responseConversation
        setConversationId(responseConversation)
      } else if (!targetConversation) {
        throw new Error('问答服务未返回会话编号；请从本机历史确认保存状态后再继续。')
      }
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let accumulated = ''
      let lastSeq = 0
      let sawTerminal = false
      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        let boundary = buffer.indexOf('\n\n')
        while (boundary >= 0) {
          const block = buffer.slice(0, boundary)
          buffer = buffer.slice(boundary + 2)
          const dataLine = block.split('\n').find((line) => line.startsWith('data: '))
          if (dataLine) {
            const message = JSON.parse(dataLine.slice(6)) as StreamEvent
            if (message.request_id !== queryId || message.seq !== lastSeq + 1 || sawTerminal) {
              throw new Error('问答流顺序异常；已保留本机历史，不会自动重发。')
            }
            lastSeq = message.seq
            if (message.type === 'citation') {
              setCitations((current) => [...current, message.data as unknown as Citation])
            } else if (message.type === 'delta') {
              accumulated += String(message.data.text ?? '')
              setAnswer(accumulated)
            } else if (message.type === 'completed') {
              sawTerminal = true
              accumulated = String(message.data.text ?? accumulated)
              setAnswer(accumulated)
              setAnswerDetails({
                source_statements: (message.data.source_statements as string[] | undefined) ?? [],
                inferences: (message.data.inferences as string[] | undefined) ?? [],
                advice: (message.data.advice as string[] | undefined) ?? [],
                missing_information: (message.data.missing_information as string[] | undefined) ?? [],
              })
              setQueryState('completed')
            } else if (message.type === 'error') {
              sawTerminal = true
              const cancelled = message.data.code === 'cancelled'
              setQueryState(cancelled ? 'cancelled' : 'error')
              setNotice(String(message.data.message ?? '问答未能完成。'))
            }
          }
          boundary = buffer.indexOf('\n\n')
        }
      }
      if (!sawTerminal) {
        setQueryState('interrupted')
        setNotice('连接已结束，回答未完整送达。已保留实际收到的部分；不会自动重新发送。可从历史继续提问。')
      }
      if (targetConversation) {
        try {
          const synced = await api.post<Conversation>(`/conversations/${targetConversation}/reopen`, {})
          rememberConversation(synced)
          setThread(synced)
        } catch (cause) {
          const message = cause instanceof Error ? cause.message : '暂时无法读取对话历史'
          setNotice((current) => current
            ? `${current} 历史同步失败：${message}。不会自动重新发送。`
            : `本次问答已结束，但历史同步失败：${message}。当前结果仍保留在页面；不会自动重新发送。`)
        }
      }
      await refreshHistory()
    } catch (cause) {
      if (cause instanceof DOMException && cause.name === 'AbortError') {
        setQueryState('cancelled')
        setNotice('已请求取消。已收到的部分会留在本机历史中，不会自动重发。')
      } else {
        const message = cause instanceof Error ? cause.message : '知识问答请求失败'
        if (cause instanceof ApiError && querySetupErrorCodes.has(cause.code)) {
          setQueryState('error')
          setNeedsModelSetup(true)
          setNotice(`本次问题尚未发送：${message}`)
        } else if (cause instanceof ApiError && cause.code === 'index_not_ready') {
          setQueryState('error')
          setNeedsIndexPreparation(true)
          setNotice(message)
        } else if (!queryRequestDispatched) {
          setQueryState('error')
          setNotice(`本次问题尚未发送：${message}`)
        } else if (!queryResponseAccepted) {
          setQueryState('interrupted')
          setNotice(`无法确认请求是否已被问答服务接收：${message}。请先查看本机历史，再自行决定是否继续；不会自动重发。`)
        } else {
          setQueryState('interrupted')
          setNotice(`${message}。已保留实际收到的部分；不会自动重新发送。可从历史继续提问。`)
        }
      }
      await refreshHistory()
      const existing = targetConversation
        ? await api.post<Conversation>(`/conversations/${targetConversation}/reopen`, {}).catch(() => null)
        : null
      if (existing) { rememberConversation(existing); setThread(existing) }
    } finally {
      setStreaming(false)
      abortController.current = null
    }
  }

  async function confirmQueryPlan() {
    if (!pendingQuery) return
    try {
      await api.post('/acceptance-plans/' + pendingQuery.plan.plan_id + '/confirm', { scope_sha256: pendingQuery.plan.scope_sha256, scope: pendingQuery.scope })
      approvedQuery.current = { planId: pendingQuery.plan.plan_id, body: pendingQuery.body }
      setPendingQuery(null)
      setNotice('已确认；现在只运行刚才审阅的查询快照。')
      queryForm.current?.requestSubmit()
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : '确认失败；尚未发送查询。')
    }
  }

  async function cancelQueryPlan() {
    if (!pendingQuery) return
    try {
      await api.delete('/acceptance-plans/' + pendingQuery.plan.plan_id)
      setPendingQuery(null)
      setNotice('本次查询计划已取消，没有发送问题或上下文。')
    } catch (cause) {
      setNotice(cause instanceof Error ? cause.message : '无法撤销本次查询计划。')
    }
  }

  async function cancel() {
    if (requestId) await api.delete('/queries/' + requestId).catch(() => undefined)
    abortController.current?.abort()
  }

  function openCitation(citation: Citation) {
    if (citation.availability === 'unavailable') {
      setNotice('这条引用对应的页面已删除、待确认或不再具备问答资格，无法作为当前依据打开。')
      return
    }
    if (citation.availability === 'updated') {
      onOpenPage(citation.page_id, citation.content_sha256)
      return
    }
    setNotice('')
    onOpenPage(citation.page_id, citation.content_sha256)
  }

  const renderedMessages = thread?.messages ?? []
  const markdownPages = eligiblePages.map((page) => ({ page_id: page.page_id, content_sha256: page.content_sha256, title: String(page.metadata.title ?? ''), relative_path: page.relative_path }))

  return (
    <section className="content-wrap ask-view">
      <PageHeader
        title="知识问答"
        actions={<button className="button secondary" onClick={startNewConversation}>新建对话</button>}
      />

      {renderedMessages.length > 0 && !composing ? <button type="button" className="query-collapsed" onClick={() => { setComposing(true); requestAnimationFrame(() => queryForm.current?.querySelector('textarea')?.focus()) }}><MessageSquarePlus size={15} strokeWidth={1.75} aria-hidden="true" />继续追问</button> : <form ref={queryForm} className="query-card" onSubmit={ask}>
        <label className="sr-only" htmlFor="knowledge-question">你的问题</label>
        <textarea id="knowledge-question" value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="例如：这个项目已经确认的地点和联系人有哪些？" rows={2} />
        <div className="query-options">
          <div className="query-fields">
            <label className="query-field" htmlFor="retrieval-purpose"><span>资料范围</span>
              <select id="retrieval-purpose" value={retrievalPurpose} onChange={(event) => setRetrievalPurpose(event.target.value as RetrievalPurpose)}>
                <option value="current">当前有效资料</option><option value="history">包含历史版本</option>
              </select>
            </label>
            <label className="query-field" htmlFor="answer-mode"><span>回答方式</span>
              <select id="answer-mode" value={answerMode} onChange={(event) => setAnswerMode(event.target.value as AnswerMode)}>
                <option value="fact">查找事实</option><option value="comparison">跨材料比较</option><option value="plan">提出工作方案</option>
              </select>
            </label>
            <label className="query-field" htmlFor="query-role"><span>本次使用角色</span>
              <select id="query-role" value={selectedRoleId} onChange={(event) => setSelectedRoleId(event.target.value)}>
                <option value="">不使用角色</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
              </select>
            </label>
          </div>
          {retrievalPurpose === 'history' && <p role="note" className="stale-citation-note">历史资料范围会包含已被替代或失效的版本，只供历史参考，不能代表当前规则。</p>}
        </div>
        {providerSettingsLoading
          ? <p className="query-readiness" role="status">正在读取真实问答就绪状态…</p>
          : providerSettingsError
            ? <div className="query-readiness is-error" role="status"><p>暂时无法读取真实问答状态：{providerSettingsError}</p><button type="button" className="button secondary" onClick={() => void loadQueryReadiness()}>重新读取</button></div>
            : providerGaps.length > 0
              ? <div className="query-readiness" role="status"><p>真实问答暂不可用：{providerGaps.join('；')}。当前问题不会发送。</p>{providerGaps.some((gap) => gap.includes('索引') || gap.includes('资料')) && onOpenApproval && <button type="button" className="button secondary" onClick={onOpenApproval}>前往审批检查或建立本地索引</button>}{providerGaps.some((gap) => !gap.includes('索引') && !gap.includes('资料')) && onOpenSettings && <button type="button" className="button secondary" onClick={onOpenSettings}>前往设置完成真实连接</button>}<button type="button" className="button secondary" onClick={() => void loadQueryReadiness()}>重新检查就绪状态</button></div>
              : null}
        <div className="query-actions">
          {streaming ? <button type="button" className="button secondary" onClick={cancel}>停止回答</button> : <button className="button primary" disabled={!question.trim() || queryReadinessBlocked}>开始检索</button>}
        </div>
      </form>}

      {notice && queryState === 'idle' && !pendingQuery && !answer && <p role="status" className="helper-line">{notice}<button type="button" className="text-button" onClick={() => queryForm.current?.querySelector('textarea')?.focus()}>继续提问</button></p>}

      {pendingQuery && <section className="plan-card approval-preview" aria-label="真实问答发送预览">
        <div><strong>请确认本次问答发送范围</strong><span>最多 1 次云端请求：DeepSeek 生成回答；向量化与排序在本机完成。生成上限 {String(pendingQuery.scope.max_output_tokens)} token，思考预算 {String(pendingQuery.scope.reasoning_effort)}。</span></div>
        <p><strong>问题</strong><br />{String(pendingQuery.scope.question ?? '')}</p>
        <p><strong>资料范围</strong><br />{pendingQuery.scope.purpose === 'history' ? '包含历史版本（仅供历史参考）' : '当前有效资料'}</p>
        <p><strong>将检索的合格页面</strong></p>
        <ul>{Object.keys((pendingQuery.scope.source_versions ?? {}) as Record<string, unknown>).map((id) => <li key={id}>{String(eligiblePages.find((page) => page.page_id === id)?.metadata.title ?? '未命名页面')}</li>)}</ul>
        {(() => { const context = (pendingQuery.scope.context ?? {}) as Record<string, unknown>; const prior = context.previous_user_questions as string[] | undefined; const memories = context.user_memories as string[] | undefined; return <>
          <p><strong>角色</strong><br />{String(context.role_name || '不使用角色')}{context.role_instructions ? `：${String(context.role_instructions)}` : ''}</p>
          <p><strong>已确认记忆</strong></p>{memories?.length ? <ul>{memories.map((memory, index) => <li key={index}>{memory}</li>)}</ul> : <p>无</p>}
          <p><strong>历史问题</strong></p>{prior?.length ? <ul>{prior.map((item, index) => <li key={index}>{item}</li>)}</ul> : <p>无</p>}
        </> })()}
        <div className="button-row"><button className="button primary" onClick={() => void confirmQueryPlan()}>确认并发送本次问题</button><button className="button secondary" onClick={() => void cancelQueryPlan()}>取消，不发送</button></div>
      </section>}

      {(answer || citations.length > 0 || queryState !== 'idle') && (!thread?.messages.some((message) => message.request_id === requestId) || streaming) && <section className="answer-panel">
        <div className="answer-heading"><span className="answer-mark" aria-hidden="true"><Sparkles size={14} strokeWidth={1.75} /></span><div><h2>本次回答 <span role="status" className="section-meta">{stateLabel[queryState]}</span></h2><span>{streaming ? '正在读取当前页面…' : queryState !== 'completed' ? '本次查询未完成，尚不能判断资料依据' : citations.length ? '根据已确认资料' : '没有找到可引用的依据'}</span></div></div>
        <StreamingMarkdown className="answer-text" content={answer} complete={!streaming} pageIndex={markdownPages} onOpenPage={onOpenPage} />
        {answerDetails && <AnswerDetails details={answerDetails} />}
        {(notice || (needsModelSetup && onOpenSettings) || (needsIndexPreparation && onOpenApproval)) && <div className="query-recovery">
          {notice && (queryState === 'error'
            ? <p role="status" className="form-error">{notice}</p>
            : <p role="status" className="helper-line">{notice}<button type="button" className="text-button" onClick={() => queryForm.current?.querySelector('textarea')?.focus()}>继续提问</button></p>)}
          {needsModelSetup && onOpenSettings && <button className="button secondary" type="button" onClick={onOpenSettings}>前往设置完成真实连接</button>}
          {needsIndexPreparation && onOpenApproval && <button className="button secondary" type="button" onClick={onOpenApproval}>前往审批建立或更新索引</button>}
        </div>}
        {citations.length > 0 && <CitationList citations={citations} onOpen={openCitation} />}
      </section>}

      {renderedMessages.length === 0 && <section className="recent-asks conversation-history" aria-label="最近的问答">
        <div className="section-head"><h2>最近的问答</h2><span className="section-meta">{history.length ? `${history.length} 段` : ''}</span></div>
        {historyLoading && history.length === 0 ? <p className="empty-row" role="status">正在读取问答历史…</p> : historyError && history.length === 0 ? <p className="empty-row" role="alert">问答历史读取失败：{historyError}</p> : history.length === 0 ? <p className="empty-row">还没有问答历史。问第一个问题吧。</p> : <>{historyError && <p role="status" className="helper-line">问答历史更新失败：{historyError}；保留上次成功读取的内容。</p>}<ul>
          {history.map((item) => <li key={item.conversation_id} className={item.conversation_id === conversationId ? 'selected' : ''}>
            <button className="history-open" disabled={Boolean(openingId)} aria-busy={openingId === item.conversation_id} onClick={() => void openConversation(item.conversation_id)}>
              <strong>{item.title}</strong>{openingId === item.conversation_id
                ? <small className="history-opening"><Loader2 className="spin" size={13} strokeWidth={2} aria-hidden="true" />正在打开这段对话…</small>
                : <small>{new Date(item.updated_at).toLocaleString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })} · {item.message_count} 个问题 · {stateLabel[item.state]}</small>}
            </button>
            <button className="text-button quiet" aria-label={`删除 ${item.title}`} onClick={() => setPendingDelete({ kind: 'conversation', id: item.conversation_id, label: item.title })}>删除</button>
          </li>)}
        </ul></>}
        {historyLoading && history.length > 0 && <p role="status" className="helper-line">正在更新问答历史…</p>}
        {historyCursor && <button className="text-button" disabled={historyLoading} onClick={() => void refreshHistory(true)}>加载更早历史</button>}
      </section>}

      {renderedMessages.length > 0 && <>
        <button type="button" className="text-button back-link" onClick={startNewConversation}><ArrowLeft size={14} strokeWidth={1.75} aria-hidden="true" />返回最近的问答</button>
        <section className="conversation-thread" aria-label="对话内容">
        <div className="section-head"><h2>对话记录</h2><span className="section-meta">{renderedMessages.length} 个问题</span></div>
        {renderedMessages.map((message) => <article className="conversation-turn" key={message.request_id}>
          <div className="user-question"><strong>你</strong><p>{message.question}</p></div>
          <div className="assistant-answer"><strong>回答 · {answerModeLabel[message.answer_mode]} · {stateLabel[message.state]}</strong><StreamingMarkdown className="answer-text" content={message.answer || (message.state === 'running' ? '正在检索与整理…' : '尚无回答内容')} complete={message.state === 'completed'} pageIndex={markdownPages} onOpenPage={onOpenPage} />
            <AnswerDetails details={message} />
            <label className="memory-attestation"><input type="checkbox" checked={memoryAttestations[message.request_id] ?? false} onChange={(event) => setMemoryAttestations((current) => ({ ...current, [message.request_id]: event.target.checked }))} />这是我本人表达的偏好或事实，不是我粘贴、转述的材料或引用</label>
            <button className="text-button" disabled={!memoryAttestations[message.request_id]} onClick={() => void proposeMemory(message)}>创建待确认记忆候选</button>
            {message.error && <p role="status" className="form-error">{message.error}</p>}
            {(message.citations?.length ?? 0) > 0 && <CitationList citations={message.citations ?? []} onOpen={openCitation} />}
          </div>
        </article>)}
        </section>
      </>}



      {pendingDelete && <ConfirmDialog
        title="删除这段问答历史？"
        description={`“${pendingDelete.label}”及其本机对话内容将被删除。`}
        consequence="删除前不会写入任何内容，取消可保留现状。"
        confirmLabel="确认删除" busyLabel="正在删除…" danger
        onCancel={() => setPendingDelete(null)}
        onConfirm={confirmDelete}
      />}
    </section>
  )
}

function AnswerDetails({ details }: { details: Partial<Pick<components['schemas']['Answer'], 'source_statements' | 'inferences' | 'advice' | 'missing_information'>> }) {
  const sections = [
    ['已确认资料中的陈述', details.source_statements],
    ['推断', details.inferences], ['建议', details.advice], ['尚缺资料', details.missing_information],
  ] as const
  return <div className="answer-details">
    {sections.filter(([, items]) => (items?.length ?? 0) > 0).map(([label, items]) => <div key={label}><strong>{label}</strong><ul>{items?.map((item, index) => <li key={`${label}-${index}`}>{item}</li>)}</ul></div>)}
  </div>
}

function CitationList({ citations, onOpen }: { citations: Citation[]; onOpen: (citation: Citation) => void }) {
  return <div className="citation-list">
    <h3>引用依据</h3>
    {citations.map((citation, index) => <button key={`${citation.page_id}:${citation.content_sha256}:${index}`} className="citation-card" onClick={() => onOpen(citation)}>
      <span className="citation-number">{index + 1}</span>
      <span><strong>{citation.heading || '页面内容'}</strong><small>{citation.excerpt}</small><small>{citationStatus(citation)}</small></span>
      <span aria-hidden="true"><ArrowUpRight size={14} strokeWidth={1.75} /></span>
    </button>)}
  </div>
}

function citationStatus(citation: Citation): string {
  const availability = citation.availability === 'updated'
    ? '原引用版本已更新'
    : citation.availability === 'unavailable'
      ? '原引用已不可用'
      : ''
  const validity = citation.validity === 'superseded'
    ? '已被替代的历史版本，仅限历史参考'
    : citation.validity === 'invalid'
      ? '已失效版本，仅限历史参考'
      : '引用版本仍可用'
  return [availability, validity].filter(Boolean).join(' · ')
}
