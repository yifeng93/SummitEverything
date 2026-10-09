import AppKit
import SwiftUI
import WebKit

private let webURL = URL(string: "http://127.0.0.1:5173")!
private let healthURL = URL(string: "http://127.0.0.1:8793/api/v1/health")!

@main
struct SummitEverythingApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            LocalWebView()
                .frame(minWidth: 960, minHeight: 680)
        }
        .windowResizability(.contentSize)
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var server: Process?

    func applicationDidFinishLaunching(_ notification: Notification) {
        let root = URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
            .deletingLastPathComponent()
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = ["uv", "run", "python", "scripts/run_dev.py"]
        process.currentDirectoryURL = root
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        do {
            try process.run()
            server = process
        } catch {
            showStartupError("无法启动本地服务：\(error.localizedDescription)")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        guard let server, server.isRunning else { return }
        server.terminate()
        server.waitUntilExit()
    }

    private func showStartupError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "SummitEverything 无法启动"
        alert.informativeText = message
        alert.runModal()
        NSApp.terminate(nil)
    }
}

struct LocalWebView: NSViewRepresentable {
    func makeCoordinator() -> Coordinator { Coordinator() }

    func makeNSView(context: Context) -> WKWebView {
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "selectWorkspaceFolder")
        let configuration = WKWebViewConfiguration()
        configuration.userContentController = controller
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        context.coordinator.webView = view
        context.coordinator.waitForReadiness()
        return view
    }

    func updateNSView(_ view: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKScriptMessageHandler {
        weak var webView: WKWebView?
        private var readinessTimer: Timer?
        private var attempts = 0

        func waitForReadiness() {
            readinessTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
                guard let self else { timer.invalidate(); return }
                self.attempts += 1
                var request = URLRequest(url: healthURL, timeoutInterval: 1)
                request.httpMethod = "GET"
                URLSession.shared.dataTask(with: request) { [weak self] _, response, _ in
                    guard let self, (response as? HTTPURLResponse)?.statusCode == 200 else { return }
                    DispatchQueue.main.async {
                        timer.invalidate()
                        self.readinessTimer = nil
                        self.webView?.load(URLRequest(url: webURL))
                    }
                }.resume()
                if self.attempts >= 60 {
                    timer.invalidate()
                    DispatchQueue.main.async { self.showReadinessError() }
                }
            }
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "selectWorkspaceFolder" else { return }
            let panel = NSOpenPanel()
            panel.canChooseFiles = false
            panel.canChooseDirectories = true
            panel.allowsMultipleSelection = false
            panel.prompt = "选择此文件夹"
            guard panel.runModal() == .OK, let path = panel.url?.path else { return }
            let escaped = String(data: try! JSONSerialization.data(withJSONObject: [path]), encoding: .utf8)!
            let script = "window.dispatchEvent(new CustomEvent('workspace-folder-selected', { detail: \(escaped.dropFirst().dropLast()) }));"
            webView?.evaluateJavaScript(script)
        }

        private func showReadinessError() {
            let alert = NSAlert()
            alert.messageText = "本地服务未就绪"
            alert.informativeText = "请确认已安装 uv、Node.js，并在仓库中执行过 cd web && npm ci。"
            alert.runModal()
            NSApp.terminate(nil)
        }
    }
}
