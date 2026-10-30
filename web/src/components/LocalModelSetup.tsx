import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { Settings } from './settingsBadges'

type ModelStatus = Settings['local_model']

type Props = {
  status: ModelStatus
  onStatus: (status: ModelStatus) => void
}

const statusLabels: Record<ModelStatus['state'], string> = {
  not_prepared: '尚未准备',
  preparing: '正在下载并校验',
  ready: '已准备好',
  failed: '准备失败',
  incomplete: '文件不完整',
}

export function LocalModelSetup({ status, onStatus }: Props) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [pollPaused, setPollPaused] = useState(false)
  const [pollEpoch, setPollEpoch] = useState(0)
  const mounted = useRef(false)
  const onStatusRef = useRef(onStatus)

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false }
  }, [])

  useEffect(() => { onStatusRef.current = onStatus }, [onStatus])

  useEffect(() => {
    if (status.state !== 'preparing') return
    let stopped = false
    let failures = 0
    let timer: ReturnType<typeof setTimeout> | undefined
    const poll = async () => {
      try {
        const next = await api.get<ModelStatus>('/retrieval-model/status')
        if (stopped) return
        failures = 0
        setError('')
        setPollPaused(false)
        onStatusRef.current(next)
        if (next.state === 'preparing') timer = setTimeout(() => void poll(), 1000)
      } catch (cause) {
        if (stopped) return
        failures += 1
        setError(cause instanceof Error ? cause.message : '无法读取模型准备状态')
        if (failures < 3) timer = setTimeout(() => void poll(), 1500)
        else setPollPaused(true)
      }
    }
    timer = setTimeout(() => void poll(), 500)
    return () => { stopped = true; if (timer) clearTimeout(timer) }
  }, [status.state, pollEpoch])

  async function retryStatusRead() {
    setBusy(true)
    setError('')
    try {
      const next = await api.get<ModelStatus>('/retrieval-model/status')
      if (!mounted.current) return
      setPollPaused(false)
      onStatusRef.current(next)
      if (next.state === 'preparing') setPollEpoch((current) => current + 1)
    } catch (cause) {
      if (mounted.current) setError(cause instanceof Error ? cause.message : '无法读取模型准备状态')
    } finally {
      if (mounted.current) setBusy(false)
    }
  }

  async function prepare() {
    setBusy(true)
    setError('')
    try {
      const next = await api.post<ModelStatus>('/retrieval-model/prepare', {})
      if (!mounted.current) return
      onStatusRef.current(next)
    } catch (cause) {
      if (mounted.current) setError(cause instanceof Error ? cause.message : '无法开始准备本地检索模型')
    } finally {
      if (mounted.current) setBusy(false)
    }
  }

  return <section className="local-model-setup" aria-label="本地检索模型">
    <div className="settings-list">
      <div><span>本地检索模型</span><strong role="status">{statusLabels[status.state]}</strong></div>
      {status.state === 'preparing' && <div><span>准备进度</span><strong>{status.progress_percent}%</strong></div>}
    </div>
    <p className="settings-help">{status.state === 'ready' ? '检索与排序都在本机完成。' : '本机完成向量检索和排序。首次准备需下载约 95 MB；文件校验通过后才会用于检索。'}</p>
    {status.state === 'failed' && <p className="form-error" role="alert">上次准备没有完成。检查网络和本机存储后，可以重试。</p>}
    {status.state === 'incomplete' && <p className="form-error" role="alert">本机模型文件不完整或校验失败。重新准备可修复。</p>}
    {error && <p className="form-error" role="alert">{error}</p>}
    {status.state === 'preparing' && pollPaused && <button className="button secondary" type="button" disabled={busy} onClick={() => void retryStatusRead()}>{busy ? '正在读取…' : '重试读取准备状态'}</button>}
    {status.state !== 'ready' && <button className="button secondary" type="button" disabled={busy || status.state === 'preparing'} onClick={() => void prepare()}>{busy ? '正在开始…' : status.state === 'preparing' ? '正在准备…' : status.state === 'failed' || status.state === 'incomplete' ? '重试准备本地模型' : '准备本地模型'}</button>}
  </section>
}
