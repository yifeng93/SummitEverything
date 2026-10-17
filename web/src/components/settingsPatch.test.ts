import { describe, expect, it } from 'vitest'
import { settingsPatch, type Settings } from './settingsBadges'

describe('settingsPatch', () => {
  it('carries the Feishu identity and calendar ID into every settings save', () => {
    const settings = {
      mode: 'real',
      model_studio_account_id: 'default',
      feishu: {
        app_id: 'cli_synthetic',
        redirect_uri: 'http://127.0.0.1:18793/api/v1/integrations/feishu/callback',
        identity: 'user',
        calendar_id: 'cal_synthetic',
        material_content: 'transcript',
        real_data_enabled: false,
      },
      llm: { provider: 'deepseek', model: 'deepseek-flash', account_id: 'default', enabled: true, max_output_tokens: 2048, reasoning_effort: 'low' },
      embedding: { provider: 'dashscope', model: 'qwen3.7-text-embedding', base_url: null, enabled: true },
      rerank: { provider: 'dashscope', model: 'qwen3.7-text-rerank', base_url: null, enabled: true },
      capabilities: {},
      credential_status: {},
      keychain_available: true,
      embedding_fingerprint: '',
    } as unknown as Settings
    expect(settingsPatch(settings).feishu).toEqual({
      app_id: 'cli_synthetic',
      redirect_uri: 'http://127.0.0.1:18793/api/v1/integrations/feishu/callback',
      identity: 'user',
      calendar_id: 'cal_synthetic',
    })
  })
})
