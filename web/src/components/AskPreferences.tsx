import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { components } from '../api/generated'
import { ConfirmDialog } from './ConfirmDialog'
import '../styles/ask.css'

type AnswerRole = components['schemas']['AnswerRole']
type UserMemory = components['schemas']['UserMemory']
type MemoryCandidate = components['schemas']['MemoryCandidate']
type IndexStatus = { fingerprint: string | null; pages: number; chunks: number; state: 'not_ready' | 'ready' | 'stale'; current_pages: number; stale_pages: number }
type PendingDelete = { kind: 'role' | 'memory'; id: string; label: string }

/*
 * 问答的“系统设置”：索引状态、角色、记忆。
 * 这些不参与提问，也不属于搜索结果，所以从问答页搬到这里，只在设置里出现一次。
 */
export function AskPreferences({ onError, onOpenApproval }: { onError?: (message: string) => void; onOpenApproval?: () => void }) {
  const [status, setStatus] = useState<IndexStatus | null>(null)
  const [roles, setRoles] = useState<AnswerRole[]>([])
  const [selectedRoleId, setSelectedRoleId] = useState('')
  const [roleName, setRoleName] = useState('')
  const [roleInstructions, setRoleInstructions] = useState('')
  const [roleBudget, setRoleBudget] = useState(2000)
  const [memories, setMemories] = useState<UserMemory[]>([])
  const [candidates, setCandidates] = useState<MemoryCandidate[]>([])
  const [loading, setLoading] = useState(true)
  const [readError, setReadError] = useState('')
  const [memoryDrafts, setMemoryDrafts] = useState<Record<string, string>>({})
  const [candidateDrafts, setCandidateDrafts] = useState<Record<string, string>>({})
  const [pendingDelete, setPendingDelete] = useState<PendingDelete | null>(null)
  const [actionError, setActionError] = useState('')
  const report = (message: string) => { setActionError(message); onError?.(message) }

  const refresh = async () => {
    setLoading(true)
    setReadError('')
    try {
      const [indexStatus, roleItems, memoryItems, candidateItems] = await Promise.all([
        api.get<IndexStatus>('/index/status'),
        api.get<AnswerRole[]>('/roles'),
        api.get<UserMemory[]>('/memory'),
        api.get<MemoryCandidate[]>('/memory/candidates'),
      ])
      // 接口异常时不要把非数组/非对象塞进 state，否则渲染会崩。
      setStatus(indexStatus && typeof indexStatus === 'object' && 'state' in indexStatus ? indexStatus : null)
      setRoles(Array.isArray(roleItems) ? roleItems : [])
      setMemories(Array.isArray(memoryItems) ? memoryItems : [])
      setCandidates(Array.isArray(candidateItems) ? candidateItems : [])
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法读取问答设置'
      setReadError(message)
      onError?.(message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0)
    return () => window.clearTimeout(timer)
    // 只在挂载时读一次；后续手动刷新。
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function chooseRole(roleId: string) {
    setSelectedRoleId(roleId)
    const role = roles.find((item) => item.role_id === roleId)
    setRoleName(role?.name ?? '')
    setRoleInstructions(role?.instructions ?? '')
    setRoleBudget(role?.context_budget ?? 2000)
  }

  async function saveRole() {
    const payload = { name: roleName.trim(), instructions: roleInstructions.trim(), context_budget: roleBudget }
    try {
      const role = selectedRoleId
        ? await api.patch<AnswerRole>(`/roles/${selectedRoleId}`, payload)
        : await api.post<AnswerRole>('/roles', payload)
      // 服务端可能只回最小字段：缺什么就保留用户刚填的内容，避免 undefined 进入受控输入。
      setSelectedRoleId(role.role_id ?? selectedRoleId)
      setRoleName(role.name ?? payload.name)
      setRoleInstructions(role.instructions ?? payload.instructions)
      setRoleBudget(role.context_budget ?? payload.context_budget)
      await refresh()
      setActionError('')
    } catch (cause) {
      report(cause instanceof Error ? cause.message : '角色没有保存')
    }
  }

  async function confirmMemory(candidate: MemoryCandidate) {
    try {
      await api.post(`/memory/candidates/${candidate.candidate_id}/confirmations`, { text: candidateDrafts[candidate.candidate_id] ?? candidate.text })
      await refresh()
      setActionError('')
    } catch (cause) {
      report(cause instanceof Error ? cause.message : '记忆没有保存')
    }
  }

  async function saveMemory(memory: UserMemory) {
    try {
      await api.patch(`/memory/${memory.memory_id}`, { text: memoryDrafts[memory.memory_id] ?? memory.text })
      await refresh()
      setActionError('')
    } catch (cause) {
      report(cause instanceof Error ? cause.message : '记忆没有保存修改')
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    try {
      if (pendingDelete.kind === 'role') {
        await api.delete(`/roles/${pendingDelete.id}`)
        setSelectedRoleId('')
        setRoleName('')
        setRoleInstructions('')
        setRoleBudget(2000)
      } else {
        await api.delete(`/memory/${pendingDelete.id}`)
      }
      setPendingDelete(null)
      await refresh()
      setActionError('')
    } catch (cause) {
      report(cause instanceof Error ? cause.message : '删除没有完成')
    }
  }

  const indexState = status?.state === 'ready' ? '已就绪' : status?.state === 'stale' ? '待更新' : '未建立'

  return <div className="ask-preferences">
    {actionError && <p className="form-error" role="alert">{actionError}</p>}
    <section className="ask-pref-block" aria-label="本机索引">
      <div className="ask-pref-head"><h3>本机索引</h3><span className="section-meta">{status ? indexState : '读取中'}</span></div>
      {loading ? <p className="empty-row" role="status">正在读取索引状态…</p> : readError && !status ? <>
        <p className="form-error" role="alert">{readError}</p>
        <button className="button secondary" onClick={() => void refresh()}>重新读取</button>
      </> : status && <>
        <p className="ask-pref-line">
          <span>可索引 {status.current_pages} 页</span><span>已索引 {status.pages} 页</span><span>待更新 {status.stale_pages} 页</span>
        </p>
        <div className="button-row">
          {onOpenApproval && <button className="button secondary" onClick={onOpenApproval}>前往审批处理索引</button>}
          <button className="text-button" onClick={() => void refresh()}>刷新</button>
        </div>
      </>}
    </section>

    <section className="ask-pref-block" aria-label="问答角色">
      <div className="ask-pref-head"><h3>问答角色</h3><span className="section-meta">只调整表达，不改变证据</span></div>
      <div className="role-grid">
        <label className="query-field" htmlFor="answer-role"><span>使用角色</span>
          <select id="answer-role" value={selectedRoleId} onChange={(event) => chooseRole(event.target.value)}>
            <option value="">不使用角色</option>{roles.map((role) => <option key={role.role_id} value={role.role_id}>{role.name}</option>)}
          </select>
        </label>
        <label className="query-field" htmlFor="role-name"><span>角色名称</span>
          <input id="role-name" value={roleName} maxLength={80} onChange={(event) => setRoleName(event.target.value)} placeholder="例如：简明分析" />
        </label>
        <label className="query-field" htmlFor="role-budget"><span>说明预算（字节）</span>
          <input id="role-budget" type="number" min={0} max={6000} value={roleBudget} onChange={(event) => setRoleBudget(Number(event.target.value))} />
        </label>
        <label className="query-field role-wide" htmlFor="role-guidance"><span>表达偏好</span>
          <textarea id="role-guidance" value={roleInstructions} maxLength={4000} onChange={(event) => setRoleInstructions(event.target.value)} placeholder="只调整表达方式；不能改变证据标准或执行权限。" rows={2} />
        </label>
      </div>
      <div className="button-row">
        <button className="button secondary" onClick={() => void saveRole()} disabled={!roleName.trim()}>保存角色</button>
        {selectedRoleId && <button className="text-button quiet" onClick={() => setPendingDelete({ kind: 'role', id: selectedRoleId, label: roleName || '当前角色' })}>删除角色</button>}
      </div>
    </section>

    <section className="ask-pref-block" aria-label="问答记忆">
      <div className="ask-pref-head"><h3>问答记忆</h3><span className="section-meta">从你的提问里提炼，确认后才生效</span></div>
      <h4 className="ask-pref-sub">待确认记忆</h4>
      {candidates.length === 0 ? <p className="empty-row">没有待确认记忆。</p> : candidates.map((candidate) => <div key={candidate.candidate_id} className="memory-item">
        <textarea aria-label="编辑记忆候选" value={candidateDrafts[candidate.candidate_id] ?? candidate.text} onChange={(event) => setCandidateDrafts((current) => ({ ...current, [candidate.candidate_id]: event.target.value }))} />
        <small>来自本机历史中的本人问题；确认后才会用于回答。</small>
        <button className="button secondary" onClick={() => void confirmMemory(candidate)}>确认并保存</button>
      </div>)}
      <h4 className="ask-pref-sub">已确认记忆</h4>
      {memories.length === 0 ? <p className="empty-row">目前没有已确认记忆。</p> : memories.map((memory) => <div key={memory.memory_id} className="memory-item">
        <textarea aria-label="编辑已确认记忆" value={memoryDrafts[memory.memory_id] ?? memory.text} onChange={(event) => setMemoryDrafts((current) => ({ ...current, [memory.memory_id]: event.target.value }))} />
        <small>来源于已确认的本人问题</small>
        <div className="button-row">
          <button className="text-button" onClick={() => void saveMemory(memory)}>保存修改</button>
          <button className="text-button quiet" onClick={() => setPendingDelete({ kind: 'memory', id: memory.memory_id, label: '这条已确认记忆' })}>删除记忆</button>
        </div>
      </div>)}
    </section>

    {pendingDelete && <ConfirmDialog
      title={pendingDelete.kind === 'role' ? '删除这个问答角色？' : '删除这条已确认记忆？'}
      description={pendingDelete.kind === 'role' ? `“${pendingDelete.label}”将从本机问答偏好中删除。` : '这条记忆将从本机偏好中删除。'}
      consequence="删除前不会写入任何内容，取消可保留现状。"
      confirmLabel="确认删除" busyLabel="正在删除…" danger
      onCancel={() => setPendingDelete(null)} onConfirm={confirmDelete}
    />}
  </div>
}
