import { smokeChecks, type SmokeCheckKey, type SmokeStatus } from './settingsBadges'
import { ConfirmDialog } from './ConfirmDialog'

/**
 * 连接检查的本次范围确认面板：设置页卡片与首次配置向导共用同一份文案，
 * 避免两处语义漂移。确认前不得发出任何请求。
 */
export function SmokeCheckConfirm({ check, smokeStatus, busy, onConfirm, onCancel }: {
  check: SmokeCheckKey
  smokeStatus: SmokeStatus | null
  busy: boolean
  onConfirm: () => void
  onCancel: () => void
}) {
  return <ConfirmDialog
    title={`确认本次连接检查：${smokeChecks[check].operation}`}
    description="会向所选服务发送一次固定的合成检查，不会发送工作库材料。"
    consequence={`本次占用 1 次；累计已用 ${smokeStatus?.counts?.[check] ?? '…'}/${smokeStatus?.limits?.[check] ?? 1}（跨运行不重置）。失败、超时与结果未知同样计数，不会自动重发。`}
    confirmLabel="确认发送本次检查"
    busyLabel="正在检查…"
    busy={busy}
    onConfirm={onConfirm}
    onCancel={onCancel}
  />
}
