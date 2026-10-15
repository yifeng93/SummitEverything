/**
 * 外壳的首屏状态屏（逐页规格 §0「三态」、FRONTEND-GUIDE §5.3）。
 *
 * 规格要求三态**分离**：
 * - 加载：显示「正在连接本机服务…」，**不显示**工作库向导；
 * - 本机服务不可达（或报错）：专门的提示块 —— 一句白话 + 「重试」+ L2 的日志目录路径，
 *   **不得**当成「还没有工作库」而弹出首次配置；
 * - 真的没有工作库（后端回 `workspace_not_open`）：才进首次配置向导（WorkspaceGate）。
 *
 * 日志目录：本机服务不响应时前端拿不到 profile 目录，所以优先用最近一次成功连接时记住的
 * 真实路径；从未连上过就给出 macOS 默认位置并注明是默认值（§9：路径只进 L2）。
 */
const DEFAULT_PROFILE_DIR = '~/Library/Application Support/SummitEverything'

function ShellBrand() {
  return (
    <div className="brand setup-brand">
      <span className="brand-mark" aria-hidden="true">S</span>
      <div><strong>SummitEverything</strong><span>个人知识工作台</span></div>
    </div>
  )
}

export function ConnectingScreen() {
  return (
    <main className="status-screen" aria-busy="true">
      <div className="status-card">
        <ShellBrand />
        <p className="status-line" role="status">正在连接本机服务…</p>
        <p className="status-hint">这台 Mac 上的知识工作台服务正在启动；连上之前不会让你选工作库。</p>
      </div>
    </main>
  )
}

export function ServiceUnreachableScreen({ onRetry, profileDir }: { onRetry: () => void; profileDir?: string }) {
  return (
    <main className="status-screen">
      <div className="status-card">
        <ShellBrand />
        <p className="eyebrow">本机服务</p>
        <h1>没有连上本机服务</h1>
        <p className="lede">资料和知识库都还在这台 Mac 上，没有丢。应用只是暂时连不上负责读写的本机服务。</p>
        <p className="status-hint">它可能还在启动、已经被关掉，或者启动时出了错。点「重试」再连一次；一直连不上就打开下面的日志目录看原因。</p>
        <div className="button-row">
          <button type="button" className="button primary" onClick={onRetry}>重试</button>
        </div>
        <details className="status-details">
          <summary>查看日志目录</summary>
          <p>
            诊断日志写在 <code>{profileDir ?? DEFAULT_PROFILE_DIR}</code>
            {profileDir ? '。' : '（默认位置；如果启动时换过资料目录，以实际设置为准）。'}
            文件名是 diagnostics.log，排查问题时把它一并提供给协助排查的人。
          </p>
        </details>
      </div>
    </main>
  )
}
