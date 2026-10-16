import { api } from '../api/client'
import type { components } from '../api/generated'

type Authorization = components['schemas']['AuthorizationStart']
export type FeishuAuthorizationStatus = components['schemas']['FeishuStatus']

/** Starts the existing local Fake callback or returns the validated official Real URL. */
export async function startFeishuAuthorization(mode: 'fake' | 'real') {
  const result = await api.post<Authorization>('/integrations/feishu/authorizations', {})
  if (mode === 'real') {
    const url = new URL(result.authorization_url)
    if (url.origin !== 'https://accounts.feishu.cn' || url.pathname !== '/open-apis/authen/v1/authorize'
      || url.username || url.password || url.hash || !url.searchParams.get('state')) {
      throw new Error('飞书授权入口无效，请检查本机配置。')
    }
    return { mode: 'real' as const, authorizationUrl: result.authorization_url }
  }
  const status = await api.oauthCallback<FeishuAuthorizationStatus>(result.authorization_url)
  return { mode: 'fake' as const, status }
}
