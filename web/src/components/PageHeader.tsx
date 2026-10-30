import type { ReactNode } from 'react'

/**
 * 每页唯一的页头：标题 + 右侧一个主操作或日期。
 *
 * 刻意不提供 `description`：页面用标题和内容本身说明功能，不再在 h1 下面
 * 放一句解释性副标题。需要解释时，把话说在具体控件旁边。
 */
export function PageHeader({ title, meta, actions }: {
  title: string
  meta?: ReactNode
  actions?: ReactNode
}) {
  return <div className="page-heading">
    <div className="page-heading-copy">
      <h1>{title}</h1>
    </div>
    {(meta || actions) && <div className="page-heading-side">{meta}{actions}</div>}
  </div>
}
