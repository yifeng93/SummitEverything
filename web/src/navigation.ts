/**
 * 主导航的定义（逐页规格 §0.1、D1）：**恰好 5 项**，顺序固定。
 *
 * 放在非组件模块里，避免「组件文件里混着导出常量」破坏 fast refresh；
 * 守卫 ⑧ 按渲染出的 DOM 顺序断言，不依赖这份常量本身。
 */
export type ShellSection = 'today' | 'approval' | 'projects' | 'ask' | 'settings'

export const NAV_ITEMS: { id: ShellSection; label: string }[] = [
  { id: 'today', label: '今日' },
  { id: 'approval', label: '审批' },
  { id: 'projects', label: '项目' },
  { id: 'ask', label: '知识问答' },
  { id: 'settings', label: '设置' },
]

export function sectionLabel(section: ShellSection): string {
  return NAV_ITEMS.find((item) => item.id === section)?.label ?? '今日'
}
