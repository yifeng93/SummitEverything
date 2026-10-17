/**
 * 设置卡片的纯映射：状态徽章、业务语言与技术码的对应关系。
 *
 * 单独成文件有两个原因：这些映射必须能脱离 React 直接固定（测试与
 * React Fast Refresh 都需要），并且技术码到「下一步做什么」的翻译
 * 不应与渲染细节混在一起。
 */
import type { components } from '../api/generated'

export type Settings = components['schemas']['SettingsSummary']
export type Capability = components['schemas']['CapabilityState']

export type SmokeCheckKey = 'deepseek_chat' | 'model_studio_embedding' | 'model_studio_rerank'
export type SecretProvider = 'feishu_app' | 'deepseek' | 'dashscope'
export type CheckOutcome = 'none' | 'succeeded' | 'failed'
export type CheckResult = Partial<Record<SmokeCheckKey, { outcome: Exclude<CheckOutcome, 'none'>; configStamp: string }>>
export type CardBadgeKind =
  | 'unconfigured' | 'configured' | 'authorized' | 'verified' | 'failed' | 'reauth' | 'unreadable'
export type CardBadge = { kind: CardBadgeKind; label: string; hint: string }

export const capabilityLabels: Record<string, string> = {
  feishu_material_read: '读取已选择的飞书材料',
  feishu_calendar_read: '读取飞书日历',
  feishu_task_read: '读取飞书任务',
  feishu_task_write: '创建或更改飞书任务',
  llm: '整理与问答模型',
  embedding: '知识索引向量化',
  rerank: '检索结果排序',
}

/**
 * `settings.capabilities[*].disabled_reason` 的技术码到业务语言的映射。
 *
 * 只列 `provider_settings_payload()` 实际会产出的码：`offline_default` /
 * `provider_not_configured` / `acceptance_plan_required` / `result_proof_unavailable`。
 * `stage_c_authorization_required` 在源码里被计算但随后被覆盖、当前不可达，保留为
 * 防御性映射。每项都包含「现在能不能用」与「下一步做什么」；未知技术码回落到带下一步
 * 动作的通用说明，既不误读成可用，也不静默显示空白。
 */
export const disabledReasons: Record<string, { text: string; next: string }> = {
  offline_default: {
    text: '当前使用离线 Fake；此路径不会访问真实 provider。',
    next: '切换到 Real 并保存真实模型与本机密钥后，真实调用仍需每次预览并独立确认范围。',
  },
  provider_not_configured: {
    text: '已选 provider；真实模式与本机密钥尚未完成配置。',
    next: '在本卡填入对应密钥并保存；保存设置不会联网，也不会自动发起检查。',
  },
  acceptance_plan_required: {
    text: '每次使用前需预览并确认本次范围。',
    next: '在对应操作中先查看本次范围预览，再由你独立确认执行。',
  },
  result_proof_unavailable: {
    text: '缺少可独立核实写入结果的方式，飞书任务写回保持关闭。',
    next: '写回继续禁用；普通任务对象不能当作写入成功的证据。',
  },
  stage_c_authorization_required: {
    text: '飞书真实读取属于单独的 Stage C 授权范围，当前未授权。',
    next: '需先单独授权真实范围并逐次预览确认，才会执行读取。',
  },
}

export const disabledReasonFallback = {
  text: '需要单独验证。',
  next: '先查看能力详情确认门禁原因，再决定下一步。',
}

export const smokeChecks: Record<SmokeCheckKey, { path: string; operation: string }> = {
  deepseek_chat: { path: 'deepseek-chat', operation: 'DeepSeek Chat' },
  model_studio_embedding: { path: 'model-studio-embedding', operation: 'Embedding' },
  model_studio_rerank: { path: 'model-studio-rerank', operation: 'Rerank' },
}

/** `GET /provider-smoke` 的本地计数摘要：次数上限跨运行不重置。 */
export type SmokeStatus = {
  counts: Record<string, number>
  limits: Record<string, number>
  remaining: Record<string, number>
}

/**
 * 合成连接检查按钮的统一门禁：钥匙串不可用、不是 Real、对应 provider 未启用、
 * 凭据未配置或额度用完时都保持禁用。设置页卡片与首次配置向导共用同一规则。
 */
export function smokeCheckDisabled(
  settings: Settings,
  smokeStatus: SmokeStatus | null,
  key: SmokeCheckKey,
  busy: boolean,
): boolean {
  if (busy || !settings.keychain_available) return true
  if (settings.mode !== 'real') return true
  if ((smokeStatus?.remaining?.[key] ?? 0) < 1) return true
  if (key === 'deepseek_chat') {
    return !settings.credential_status?.deepseek
      || settings.llm.provider !== 'deepseek'
      || !settings.llm.enabled
  }
  if (key === 'model_studio_embedding') {
    return !settings.credential_status?.dashscope
      || settings.embedding.provider !== 'dashscope'
      || !settings.embedding.enabled
  }
  return !settings.credential_status?.dashscope
    || settings.rerank.provider !== 'dashscope'
    || !settings.rerank.enabled
}

/**
 * `GET /integrations/feishu/status` 的本地只读摘要。该接口只读本机 vault，不联网，
 * 也不占用任何合成连接检查额度。`authorized` 只表示存在可用的 user token；
 * `user_identity_verified` 恒为 false（没有做过真实身份查询），界面不得声称身份已验证。
 */
export type FeishuStatusSummary = {
  mode: string
  authorized: boolean
  app_configured: boolean
  credential_error?: string | null
  user_identity_verified?: boolean
}

export type FeishuStatusRead =
  | { state: 'loading' }
  | { state: 'unreadable' }
  | { state: 'invalidated' }
  | { state: 'loaded'; status: FeishuStatusSummary; readAt?: string }
  | { state: 'stale'; status: FeishuStatusSummary; readAt?: string }

export function failedFeishuStatusRead(previous: FeishuStatusRead): FeishuStatusRead {
  if (previous.state === 'loaded' || previous.state === 'stale') return { ...previous, state: 'stale' }
  if (previous.state === 'invalidated') return previous
  return { state: 'unreadable' }
}

export function parseFeishuStatus(value: unknown): FeishuStatusSummary | null {
  if (!value || typeof value !== 'object') return null
  const candidate = value as Partial<FeishuStatusSummary>
  if (typeof candidate.mode !== 'string' || typeof candidate.authorized !== 'boolean') return null
  return {
    mode: candidate.mode,
    authorized: candidate.authorized,
    app_configured: candidate.app_configured === true,
    credential_error: typeof candidate.credential_error === 'string' ? candidate.credential_error : null,
    user_identity_verified: candidate.user_identity_verified === true,
  }
}

export function credentialAccountId(settings: Settings, provider: SecretProvider): string {
  if (provider === 'feishu_app') return settings.feishu.app_id || 'default'
  if (provider === 'deepseek') return settings.llm.account_id
  return settings.model_studio_account_id
}

/**
 * 本地 profile 设置是一个整体：卡片内提交时把界面上所有未落盘的本地设置一并写入，
 * 再保存密钥，避免「先保存账户标识才能存密钥」的顺序摩擦。PATCH 只在 /settings 落盘，
 * 不联系 provider，也不触发任何连接检查。
 */
export function settingsPatch(settings: Settings): Record<string, unknown> {
  return {
    mode: settings.mode,
    model_studio_account_id: settings.model_studio_account_id,
    feishu: {
      app_id: settings.feishu.app_id,
      redirect_uri: settings.feishu.redirect_uri,
      identity: settings.feishu.identity,
      calendar_id: settings.feishu.calendar_id,
    },
    llm: {
      provider: settings.llm.provider,
      model: settings.llm.model ?? null,
      account_id: settings.llm.account_id,
      enabled: settings.llm.enabled,
      max_output_tokens: settings.llm.max_output_tokens,
      reasoning_effort: settings.llm.reasoning_effort,
    },
    embedding: {
      provider: settings.embedding.provider,
      model: settings.embedding.model ?? null,
      base_url: settings.embedding.base_url,
      enabled: settings.embedding.enabled,
    },
    rerank: {
      provider: settings.rerank.provider,
      model: settings.rerank.model ?? null,
      base_url: settings.rerank.base_url,
      enabled: settings.rerank.enabled,
    },
  }
}

export function reasonText(reason: string | null | undefined): { text: string; next: string } {
  if (!reason) return disabledReasonFallback
  return disabledReasons[reason] ?? disabledReasonFallback
}

export function capabilityStatusLabel(capability: Capability | undefined): string {
  if (!capability) return '未启用'
  if (capability.available) return '可用'
  if (capability.disabled_reason === 'acceptance_plan_required') return '已配置，待本次确认'
  if (capability.configured) return '已配置，未启用'
  return '未启用'
}

export function smokeCheckConfigStamp(settings: Settings, key: SmokeCheckKey): string {
  const common = { mode: settings.mode, keychainAvailable: settings.keychain_available }
  if (key === 'deepseek_chat') {
    return JSON.stringify({ ...common, credential: settings.credential_status?.deepseek, ...settings.llm })
  }
  const model = key === 'model_studio_embedding' ? settings.embedding : settings.rerank
  return JSON.stringify({ ...common, credential: settings.credential_status?.dashscope, accountId: settings.model_studio_account_id, ...model })
}

export function checkedCapabilityStatusLabel(
  capability: Capability | undefined,
  outcome: CheckOutcome,
): string {
  if (outcome === 'succeeded') return '本次合成检查通过'
  if (outcome === 'failed') return '本次检查失败'
  return capabilityStatusLabel(capability)
}

/**
 * AI 模型卡的状态徽章：只描述「配置是否存在 / 最近一次检查结果」，不把保存
 * 当成联网验证。徽章文案与下一步动作分离，便于同一条映射被测试直接固定。
 */
export function modelCardBadge(input: {
  mode: Settings['mode']
  credentials: Record<string, boolean>
  capabilities: Settings['capabilities']
  checkOutcomes: Record<SmokeCheckKey, CheckOutcome>
}): CardBadge {
  const outcomes = Object.values(input.checkOutcomes)
  if (outcomes.every((outcome) => outcome === 'succeeded')) {
    return {
      kind: 'verified', label: '三项检查通过',
      hint: 'DeepSeek、Embedding 与 Rerank 三项的当前配置均通过本机合成检查。真实业务调用仍需每次预览并独立确认范围。',
    }
  }
  if (outcomes.some((outcome) => outcome === 'failed')) {
    return {
      kind: 'failed', label: '有检查失败',
      hint: '至少一项当前配置的合成连接检查未通过。逐项状态分别显示，失败同样计入额度，不会自动重发。',
    }
  }
  if (outcomes.some((outcome) => outcome === 'succeeded')) {
    return {
      kind: 'configured', label: '部分已检查',
      hint: '只有部分能力完成了当前配置的合成连接检查。逐项状态会显示已检查、未检查范围；未检查能力不代表可用。',
    }
  }
  const capabilities = input.capabilities ?? {}
  const configured = (['llm', 'embedding', 'rerank'] as const).some((key) => capabilities[key]?.configured)
    || Boolean(input.credentials?.deepseek)
    || Boolean(input.credentials?.dashscope)
  if (!configured) {
    return {
      kind: 'unconfigured', label: '未配置',
      hint: '还没有可用的真实模型配置与密钥。选择模型、填入密钥并保存后，再单独确认连接检查。',
    }
  }
  if (input.mode === 'real') {
    return {
      kind: 'configured', label: '已配置（尚未验证）',
      hint: '配置与密钥已保存在本机。点击“检查连接”并确认后才会联网；每次真实使用前仍需预览并确认本次范围。',
    }
  }
  return {
    kind: 'configured', label: '已配置（尚未验证）',
    hint: '配置已保存在本机，但当前是离线 Fake 模式；切换到 Real 后才能进行连接检查与真实调用。',
  }
}

/**
 * 飞书卡的状态徽章，基于 `GET /integrations/feishu/status` 这个本地只读信号。
 *
 * 只有 `credential_error === 'credential_unreadable'`（凭据存在但读不出来）才可以说
 * 「需重新授权」。钥匙串不可用属于本机环境问题，不能当成授权失效。状态读取失败时
 * 显示「无法读取」，绝不默认成已授权；`authorized` 也不代表身份已验证或权限范围已核实。
 */
export function feishuCardBadge(input: {
  keychainAvailable: boolean
  read: FeishuStatusRead
}): CardBadge {
  if (input.read.state === 'loading') {
    return {
      kind: 'unreadable', label: '正在读取授权状态…',
      hint: '正在读取本机保存的授权状态。读取完成前不假设已授权。',
    }
  }
  if (!input.keychainAvailable) {
    return {
      kind: 'unreadable', label: '钥匙串不可用',
      hint: '当前运行环境无法访问 macOS 钥匙串，读不到本机凭据；这不等同于需要重新授权。密钥保存会失败关闭。',
    }
  }
  if (input.read.state === 'unreadable') {
    return {
      kind: 'unreadable', label: '授权状态暂时无法读取',
      hint: '无法读取本机授权状态，也不假设已授权。可在高级与自定义中重新读取；读取状态不联网，也不占用连接检查额度。',
    }
  }
  if (input.read.state === 'invalidated') {
    return {
      kind: 'unconfigured', label: '未配置',
      hint: '已确认删除本机飞书应用密钥，状态已标记为未连接。重新读取状态不会联网；如需连接，请重新保存应用配置并完成授权。',
    }
  }
  const status = input.read.status
  if (status.credential_error === 'credential_unreadable') {
    return {
      kind: 'reauth', label: '需重新授权',
      hint: '本机存在飞书凭据但已无法读取。请在「今日 / 飞书日常」重新完成授权。',
    }
  }
  if (status.mode !== 'real') {
    return {
      kind: 'unconfigured', label: '未配置',
      hint: '当前离线模式（Fake），不会访问飞书。切换到 Real、保存应用密钥并完成授权后才可能读取。',
    }
  }
  if (status.authorized) {
    return {
      kind: 'authorized', label: '已授权',
      hint: '本机存在可用的飞书用户授权。读取仍需在每次操作前预览并独立确认范围；此状态不表示身份已核实，也不表示权限范围已经验证。',
    }
  }
  if (status.app_configured) {
    return {
      kind: 'configured', label: '已配置，尚未授权',
      hint: '应用密钥已保存在本机，但还没有可用的用户授权。请在「今日 / 飞书日常」完成授权；授权前不会读取任何飞书数据。',
    }
  }
  return {
    kind: 'unconfigured', label: '未配置',
    hint: '还没有可用的飞书应用配置与授权。填入飞书应用 App ID 与应用密钥并保存，随后在「今日 / 飞书日常」完成授权。',
  }
}

export function badgeClass(kind: CardBadgeKind): string {
  if (kind === 'unconfigured') return 'conn-badge off'
  if (kind === 'verified') return 'conn-badge ok'
  if (kind === 'failed') return 'conn-badge failed'
  if (kind === 'reauth') return 'conn-badge reauth'
  if (kind === 'unreadable') return 'conn-badge unreadable'
  return 'conn-badge configured'
}
