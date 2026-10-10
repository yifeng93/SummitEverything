import { useMemo, useRef, useState } from 'react'
import { api, indexUpdateMessage, newOperationId, type Draft, type MutationResult, type Page, type SourceDetail } from '../api/client'

type Conflict = { id: string; question: string; alternatives: string[] }
type Props = {
  draft: Draft
  pages: Page[]
  onError: (message: string) => void
  onConfirmed: (indexStatus: string) => Promise<void>
  onUpdated: () => Promise<void>
}

export function DraftReview({ draft, pages, onError, onConfirmed, onUpdated }: Props) {
  const conflicts = (draft.important_conflicts ?? []) as Conflict[]
  const [title, setTitle] = useState(String(draft.metadata.title ?? ''))
  const [body, setBody] = useState(draft.body)
  const [targetId, setTargetId] = useState(draft.target_page_id ?? '')
  const [baseHash, setBaseHash] = useState(draft.expected_base_sha256 ?? '')
  const [version, setVersion] = useState(draft.version)
  const [resolutions, setResolutions] = useState<Record<string, string>>(draft.conflict_resolutions ?? {})
  const [busy, setBusy] = useState(false)
  const [source, setSource] = useState<SourceDetail | null>(null)
  const [indexNotice, setIndexNotice] = useState('')
  const operationIds = useRef<Record<string, string>>({})
  const target = pages.find((page) => page.page_id === targetId)
  const staleBase = Boolean(target && target.content_sha256 !== baseHash)
  const targetNeedsConfirmation = Boolean(target && target.approval_state !== 'confirmed')
  const candidates = useMemo(
    () => pages.filter((page) =>
      (page.approval_state === 'confirmed' || page.page_id === targetId)
      && String(page.metadata.project_id ?? '') === String(draft.metadata.project_id ?? ''),
    ),
    [pages, draft.metadata.project_id, targetId],
  )
  const dirty = title !== String(draft.metadata.title ?? '') || body !== draft.body
    || targetId !== (draft.target_page_id ?? '') || baseHash !== (draft.expected_base_sha256 ?? '')

  function op(key: string) {
    operationIds.current[key] ??= newOperationId()
    return operationIds.current[key]
  }

  async function saveDraft() {
    const key = ['save', draft.draft_id, version, title, body, targetId, baseHash].join(':')
    const updated = await api.patch<Draft>('/drafts/' + draft.draft_id, {
      expected_version: version,
      title,
      body,
      target_page_id: targetId || null,
      expected_base_sha256: baseHash || null,
    })
    delete operationIds.current[key]
    setVersion(updated.version)
    await onUpdated()
    return updated
  }

  async function selectTarget(pageId: string) {
    setTargetId(pageId)
    const page = pages.find((item) => item.page_id === pageId)
    setBaseHash(page?.content_sha256 ?? '')
  }

  async function confirmDraft() {
    if (conflicts.some((conflict) => !resolutions[conflict.id])) {
      onError('请逐项选择采用的依据，或明确标记为未解决。')
      return
    }
    setBusy(true)
    const key = ['confirm', draft.draft_id, version, title, body, targetId, JSON.stringify(resolutions)].join(':')
    try {
      const current = dirty ? await saveDraft() : draft
      const expectedVersion = dirty ? current.version : version
      const result = await api.post<MutationResult>('/drafts/' + draft.draft_id + '/confirmations', {
        expected_version: expectedVersion,
        confirmation_id: op(key + ':confirmation'),
        operation_id: op(key),
        conflict_resolutions: resolutions,
      })
      setIndexNotice(indexUpdateMessage(result.index_update) ?? '')
      delete operationIds.current[key]
      delete operationIds.current[key + ':confirmation']
      onError('')
      await onConfirmed(indexUpdateMessage(result.index_update) ?? '')
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : '无法确认稿件'
      if (message.includes('页面已变化') || message.includes('changed since it was reviewed')) {
        await onUpdated()
      }
      onError(message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="draft-review" aria-label="审核稿编辑">
      {indexNotice && <p role="status" className={indexNotice.includes('索引更新未完成') ? 'form-error' : 'success-note'}>{indexNotice}</p>}
      <div className="review-topline"><span>完整审核稿</span><span>{draft.source_ids.length} 个原始来源</span></div>
      <label className="field"><span>页面标题</span><input value={title} onChange={(event) => setTitle(event.target.value)} /></label>
      <label className="compact-field target-select"><span>整理到</span>
        <select value={targetId} onChange={(event) => void selectTarget(event.target.value)}>
          <option value="">新建知识页</option>
          {candidates.map((page) => <option key={page.page_id} value={page.page_id}>
            {String(page.metadata.title ?? '未命名页面')}{page.approval_state === 'invalid' ? ' · 需要重新确认' : ''}
          </option>)}
        </select>
      </label>
      {target && (
        <>
          {(staleBase || targetNeedsConfirmation) && (
            <div className="form-error" role="status">
              <p>目标页面已变化或需要重新确认。当前正文尚未被覆盖，请检查下方版本对比。</p>
              {staleBase ? (
                <button className="text-button" disabled={busy} onClick={() => setBaseHash(target.content_sha256)}>
                  采用当前页面作为比较基准
                </button>
              ) : <span>当前正文已作为比较基准；确认时仍会检查是否再次发生变化。</span>}
            </div>
          )}
          <div className="diff-view">
            <div><span>当前版本</span><pre>{target.body}</pre></div>
            <div><span>审核稿</span><pre>{body}</pre></div>
          </div>
        </>
      )}
      <label className="field"><span>正文</span><textarea value={body} rows={9} onChange={(event) => setBody(event.target.value)} /></label>
      <div className="source-reference">
        <span>来源</span>
        {draft.source_ids.map((sourceId) => <button key={sourceId} className="source-chip" onClick={() => api.get<SourceDetail>('/sources/' + sourceId).then(setSource).catch((cause) => onError(cause instanceof Error ? cause.message : '无法读取来源'))}>{sourceId.slice(0, 8)}</button>)}
      </div>
      {source && <section className="original-source"><div><strong>{source.source.filename}</strong><button className="text-button" onClick={() => setSource(null)}>收起</button></div><pre>{source.text}</pre></section>}
      {conflicts.length > 0 && (
        <div className="conflict-list">
          <h3>需要你判断的冲突</h3>
          {conflicts.map((conflict) => (
            <fieldset className="conflict-item" key={conflict.id}>
              <legend>{conflict.question}</legend>
              {conflict.alternatives.map((alternative) => (
                <label key={alternative}><input type="radio" name={conflict.id} checked={resolutions[conflict.id] === alternative} onChange={() => setResolutions((current) => ({ ...current, [conflict.id]: alternative }))} /> 采用：{alternative}</label>
              ))}
              <label><input type="radio" name={conflict.id} checked={resolutions[conflict.id] === 'unresolved'} onChange={() => setResolutions((current) => ({ ...current, [conflict.id]: 'unresolved' }))} /> 暂时未决</label>
            </fieldset>
          ))}
          {conflicts.some((conflict) => resolutions[conflict.id]) && (
            <div className="conflict-outcome-preview" aria-label="确认结果预览">
              <strong>确认后正文会记录</strong>
              <ul>{conflicts.filter((conflict) => resolutions[conflict.id]).map((conflict) => (
                <li key={conflict.id}>
                  {conflict.question}：{resolutions[conflict.id] === 'unresolved'
                    ? '暂时未决，尚未作为确定事实'
                    : `用户选择采用：${resolutions[conflict.id]}`}
                </li>
              ))}</ul>
            </div>
          )}
        </div>
      )}
      <div className="review-actions">
        <span>{dirty ? '有尚未保存的修改' : '来源与稿件保持关联'}</span>
        <div className="button-row">
          <button className="button secondary" disabled={!dirty || busy} onClick={() => void saveDraft().catch((cause) => onError(cause instanceof Error ? cause.message : '无法保存稿件'))}>保存修改</button>
          <button className="button primary" disabled={busy || staleBase} onClick={confirmDraft}>{busy ? '正在保存…' : '确认并写入知识库'}</button>
        </div>
      </div>
    </section>
  )
}
