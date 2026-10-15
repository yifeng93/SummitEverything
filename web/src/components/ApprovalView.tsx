import type { Draft, IntakeItem } from '../api/client'
import { draftStateLabel, intakeStateLabel, pendingDrafts, pendingIntakeItems } from '../approval-summary'

/**
 * 审批页 · 最小可用版（逐页规格 §3、FRONTEND-GUIDE §14 的 P1/P3 边界）。
 *
 * 本切片实现的部分：
 * - 页头（eyebrow + h1 + `.lede`，文案照 §4.1）；
 * - 顶部状态行：待处理总数 + 分组数；
 * - 分组 1「待整理的来源」与分组 2「待复核的稿件」：用**现有端点**
 *   （`/intake/items`、`/drafts`，由 App.tsx 读取后传进来）列出真实条目与数量，
 *   每个分组有自己的加载态、空态和错误态。
 *
 * 明确留给 P3 · 信息架构切片的部分（本轮**不**做占位按钮、不写「即将推出」）：
 * - 分组 3/4/5：待确认的正式内容、待确认的索引更新、待确认的外部动作；
 * - 工具栏的「检查并应用」主操作与视图筛选（全部 / 待处理 / 已完成）；
 * - 「怎么读这一页」固定段落、分组 2 的稿件复核区（Markdown 正文、差异与冲突选择）、
 *   分组 1 的整理动作（本轮仍在今日页，迁移属 P3）。
 * 也就是说：这一版只回答「现在有哪些东西等着我」，不假装能在这里处理它们。
 */
type Props = {
  items: IntakeItem[]
  drafts: Draft[]
  loading: boolean
  error: string
  onRetry: () => void
}

export function ApprovalView({ items, drafts, loading, error, onRetry }: Props) {
  const pendingItems = pendingIntakeItems(items)
  const reviews = pendingDrafts(drafts)
  const pendingTotal = pendingItems.length + reviews.length

  return (
    <section className="content-wrap approval-view">
      <div className="page-heading">
        <div>
          <div className="eyebrow">需要你点一下才算数</div>
          <h1>审批</h1>
          <p className="lede">需要你点一下才算数的都在这里——先整理来源，再复核稿件，最后确认正式内容。</p>
        </div>
      </div>

      <div className="approval-toolbar">
        <p className="hint" role="status">
          {loading
            ? '正在读取待处理的来源和稿件…'
            : error
              ? '这次没有读到待处理的清单。'
              : `待处理 ${pendingTotal} 项 · 共 2 类。数量统计的是还没处理完的来源和稿件。`}
        </p>
        <button type="button" className="button secondary" onClick={onRetry} disabled={loading}>
          {loading ? '正在刷新…' : '刷新清单'}
        </button>
      </div>

      {error && (
        <div className="notice-block" role="alert">
          <p>{error}</p>
          <button type="button" className="button secondary" onClick={onRetry}>重试</button>
        </div>
      )}

      <section className="panel approval-group" aria-labelledby="approval-intake-heading">
        <div className="panel-heading">
          <div>
            <h2 id="approval-intake-heading">待整理的来源</h2>
            <p>原件先留在本机；每条要你确认后才会生成待审核稿。这里不列出已经处理完的来源。</p>
          </div>
          {!loading && !error && <span className="count-badge">{pendingItems.length}</span>}
        </div>
        {loading ? (
          <p className="quiet-empty" role="status">正在读取…</p>
        ) : error ? (
          <p className="quiet-empty">这一类这次没有读到；点上面的「重试」再看。</p>
        ) : pendingItems.length === 0 ? (
          <div className="empty-state"><strong>没有待整理的来源</strong><span>导入的材料会先出现在这里。</span></div>
        ) : (
          <ul className="source-list">
            {pendingItems.map((item) => (
              <li key={item.item_id}>
                <div className="approval-row">
                  <span className="file-glyph" aria-hidden="true">文</span>
                  <span className="source-title">
                    <strong>{item.title}</strong>
                    <small>{item.filename} · {new Date(item.created_at).toLocaleDateString('zh-CN')}</small>
                  </span>
                  <span className="status-label">{intakeStateLabel(item.state)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="panel approval-group" aria-labelledby="approval-draft-heading">
        <div className="panel-heading">
          <div>
            <h2 id="approval-draft-heading">待复核的稿件</h2>
            <p>整理出来的稿件要你确认当前版本才会成为正式内容。</p>
          </div>
          {!loading && !error && <span className="count-badge">{reviews.length}</span>}
        </div>
        {loading ? (
          <p className="quiet-empty" role="status">正在读取…</p>
        ) : error ? (
          <p className="quiet-empty">这一类这次没有读到；点上面的「重试」再看。</p>
        ) : reviews.length === 0 ? (
          <div className="empty-state"><strong>没有待复核的稿件</strong><span>整理来源后会先在这里等你确认。</span></div>
        ) : (
          <ul className="draft-list">
            {reviews.map((draft) => (
              <li key={draft.draft_id}>
                <div className="approval-row">
                  <span className="draft-marker" aria-hidden="true" />
                  <span className="source-title">
                    <strong>{String(draft.metadata.title ?? '未命名稿件')}</strong>
                    <small>{draft.source_ids.length} 个来源 · {draft.important_conflicts?.length ?? 0} 项重要冲突</small>
                  </span>
                  <span className="status-label">{draftStateLabel(draft.state)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </section>
  )
}
