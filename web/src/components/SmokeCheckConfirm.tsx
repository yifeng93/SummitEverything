import { smokeChecks, type SmokeCheckKey, type SmokeStatus } from './settingsBadges'

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
  return <div className="settings-confirm" role="dialog" aria-label="确认本次连接检查">
    <strong>确认本次连接检查：{smokeChecks[check].operation}</strong>
    <ul>
      <li>只发送固定短合成 payload，不发送工作库材料。</li>
      <li>本次占用 1 次；累计已用 {smokeStatus?.counts?.[check] ?? '…'}/{smokeStatus?.limits?.[check] ?? 1}（跨运行不重置）。</li>
      <li>失败、超时与结果未知同样计数，不会自动重发。</li>
    </ul>
    <div className="button-row">
      <button className="button primary" type="button" disabled={busy} onClick={onConfirm}>确认发送本次检查</button>
      <button className="button secondary" type="button" disabled={busy} onClick={onCancel}>取消</button>
    </div>
  </div>
}
