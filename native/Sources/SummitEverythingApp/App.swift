import AppKit
import CoreFoundation
import Darwin
import Foundation
import Security
import SwiftUI
import WebKit
import NativeUploadPolicy

private let apiPort = 18793
private let localOrigin = "http://127.0.0.1:\(apiPort)"
private let healthURL = URL(string: "\(localOrigin)/api/v1/health")!

struct BuildIdentity: Decodable {
    let source_sha: String
    let dirty: Bool
    let build_id: String
    let app_version: String
    let frontend_sha256: String
    let dependencies_sha256: String
}

@main
struct SummitEverythingApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var appDelegate

    var body: some Scene {
        WindowGroup {
            InternalWindow(appDelegate: appDelegate).frame(minWidth: 960, minHeight: 680)
        }
        .windowResizability(.contentSize)
    }
}

private struct InternalWindow: View {
    @ObservedObject var appDelegate: AppDelegate

    var body: some View {
        Group {
            if let identity = appDelegate.identity, let token = appDelegate.sessionToken {
                LocalWebView(identity: identity, runID: appDelegate.runID, token: token)
            } else {
                ProgressView("正在启动 SummitEverything Internal…")
                    .frame(minWidth: 600, minHeight: 360)
            }
        }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate, ObservableObject {
    @Published private(set) var identity: BuildIdentity?
    @Published private(set) var sessionToken: String?
    let runID = UUID().uuidString
    private var server: Process?
    private var parentPipe: Pipe?
    private var profileLock: Int32 = -1

    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }

    func applicationDidFinishLaunching(_ notification: Notification) {
        do {
            let resources = Bundle.main.resourceURL!
            identity = try JSONDecoder().decode(BuildIdentity.self, from: Data(contentsOf: resources.appendingPathComponent("build-info.json")))
            try startBackend(resources: resources)
        } catch {
            showStartupError("内部应用无法启动。请保留这个候选包并联系维护者。")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        parentPipe?.fileHandleForWriting.closeFile()
        if let server, server.isRunning {
            server.terminate()
            let deadline = Date().addingTimeInterval(3)
            while server.isRunning && Date() < deadline { Thread.sleep(forTimeInterval: 0.05) }
            if server.isRunning { kill(server.processIdentifier, SIGKILL) }
            server.waitUntilExit()
        }
        if profileLock >= 0 { flock(profileLock, LOCK_UN); close(profileLock) }
    }

    private func startBackend(resources: URL) throws {
        let support: URL
        if let testRoot = ProcessInfo.processInfo.environment["SUMMIT_INTERNAL_TEST_PROFILE_ROOT"] {
            let temporaryRoot = URL(fileURLWithPath: NSTemporaryDirectory(), isDirectory: true)
                .resolvingSymlinksInPath().standardizedFileURL
            let requestedRoot = URL(fileURLWithPath: testRoot, isDirectory: true)
                .resolvingSymlinksInPath().standardizedFileURL
            let prefix = temporaryRoot.path.hasSuffix("/") ? temporaryRoot.path : temporaryRoot.path + "/"
            guard requestedRoot.path.hasPrefix(prefix), requestedRoot.path != temporaryRoot.path else {
                throw NSError(domain: "SummitEverything.Internal", code: 3)
            }
            support = requestedRoot
        } else {
            support = try FileManager.default.url(for: .applicationSupportDirectory, in: .userDomainMask, appropriateFor: nil, create: true)
                .appendingPathComponent("SummitEverything Internal", isDirectory: true)
        }
        try FileManager.default.createDirectory(at: support, withIntermediateDirectories: true)
        let lockURL = support.appendingPathComponent("instance.lock")
        profileLock = open(lockURL.path, O_CREAT | O_RDWR, S_IRUSR | S_IWUSR)
        guard profileLock >= 0, flock(profileLock, LOCK_EX | LOCK_NB) == 0 else {
            throw NSError(domain: "SummitEverything.Internal", code: 1)
        }

        var random = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, random.count, &random) == errSecSuccess else {
            throw NSError(domain: "SummitEverything.Internal", code: 2)
        }
        sessionToken = Data(random).base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")

        let executable = resources.appendingPathComponent("backend/summit-backend/summit-backend")
        let process = Process()
        process.executableURL = executable
        var environment = [
            "PATH": "/usr/bin:/bin:/usr/sbin:/sbin",
            "HOME": FileManager.default.homeDirectoryForCurrentUser.path,
            "SUMMIT_PROFILE_ROOT": support.path,
            "SUMMIT_API_PORT": String(apiPort),
            "SUMMIT_WEB_PORT": String(apiPort),
            "SUMMIT_RUN_ID": runID,
            "SUMMIT_SESSION_TOKEN": sessionToken!,
            "SUMMIT_BUILD_INFO": resources.appendingPathComponent("build-info.json").path,
            "SUMMIT_WEB_DIST": resources.appendingPathComponent("web").path,
        ]
        if let temp = ProcessInfo.processInfo.environment["TMPDIR"] { environment["TMPDIR"] = temp }
        // Candidate verification may disable Keychain access explicitly. Forward
        // only this opt-in deny flag; never inherit the caller's general environment.
        if ProcessInfo.processInfo.environment["SUMMIT_OFFLINE_GUARD_ACTIVE"] == "1" {
            environment["SUMMIT_OFFLINE_GUARD_ACTIVE"] = "1"
        }
        process.environment = environment
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.nullDevice
        let pipe = Pipe()
        process.standardInput = pipe.fileHandleForReading
        try process.run()
        parentPipe = pipe
        server = process
    }

    private func showStartupError(_ message: String) {
        let alert = NSAlert()
        alert.messageText = "SummitEverything Internal 无法启动"
        alert.informativeText = message
        alert.runModal()
        NSApp.terminate(nil)
    }
}

private struct LocalWebView: NSViewRepresentable {
    let identity: BuildIdentity
    let runID: String
    let token: String

    func makeCoordinator() -> Coordinator { Coordinator(identity: identity, runID: runID, token: token) }

    func makeNSView(context: Context) -> WKWebView {
        let controller = WKUserContentController()
        controller.add(context.coordinator, name: "selectWorkspaceFolder")
        let configuration = WKWebViewConfiguration()
        configuration.websiteDataStore = .nonPersistent()
        configuration.userContentController = controller
        let view = WKWebView(frame: .zero, configuration: configuration)
        view.navigationDelegate = context.coordinator
        view.uiDelegate = context.coordinator
        context.coordinator.webView = view
        context.coordinator.waitForReadiness()
        return view
    }

    func updateNSView(_ view: WKWebView, context: Context) {}

    final class Coordinator: NSObject, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler, URLSessionTaskDelegate {
        private let identity: BuildIdentity
        private let runID: String
        private let token: String
        weak var webView: WKWebView?
        private var readinessTimer: Timer?
        private var attempts = 0
        private var checkingReadiness = false
        private lazy var session = URLSession(configuration: .ephemeral, delegate: self, delegateQueue: nil)

        init(identity: BuildIdentity, runID: String, token: String) {
            self.identity = identity
            self.runID = runID
            self.token = token
        }

        func waitForReadiness() {
            readinessTimer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
                guard let self else { timer.invalidate(); return }
                self.attempts += 1
                if self.attempts >= 60 {
                    timer.invalidate()
                    self.showReadinessError()
                    return
                }
                guard !self.checkingReadiness else { return }
                self.checkingReadiness = true
                self.checkHealth(timer: timer)
            }
        }

        private func checkHealth(timer: Timer) {
            var request = URLRequest(url: healthURL, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 1)
            request.httpMethod = "GET"
            session.dataTask(with: request) { [weak self] data, response, _ in
                guard let self else { return }
                let payload = data.flatMap { try? JSONSerialization.jsonObject(with: $0) as? [String: Any] }
                let matches = (response as? HTTPURLResponse)?.statusCode == 200
                    && response?.url == healthURL
                    && payload.map { health in
                        self.healthIdentity.allSatisfy { key, value in
                            guard let actual = health[key] else { return false }
                            if let expected = value as? String { return actual as? String == expected }
                            if let expected = value as? Bool, let actual = actual as? NSNumber {
                                return CFGetTypeID(actual) == CFBooleanGetTypeID()
                                    && actual.boolValue == expected
                            }
                            return false
                        }
                    } == true
                guard matches else {
                    DispatchQueue.main.async { self.checkingReadiness = false }
                    return
                }
                self.session.dataTask(with: URLRequest(url: URL(string: localOrigin + "/")!, cachePolicy: .reloadIgnoringLocalCacheData, timeoutInterval: 1)) { [weak self] _, webResponse, _ in
                    DispatchQueue.main.async {
                        guard let self else { return }
                        self.checkingReadiness = false
                        guard timer.isValid, (webResponse as? HTTPURLResponse)?.statusCode == 200,
                              webResponse?.url?.absoluteString == localOrigin + "/" else { return }
                        timer.invalidate()
                        self.readinessTimer = nil
                        guard let tokenData = try? JSONSerialization.data(withJSONObject: self.token, options: .fragmentsAllowed),
                              let tokenLiteral = String(data: tokenData, encoding: .utf8) else { return }
                        let script = WKUserScript(source: "Object.defineProperty(window, '__SUMMIT_SESSION_TOKEN__', { value: \(tokenLiteral), writable: false, configurable: false });", injectionTime: .atDocumentStart, forMainFrameOnly: true)
                        self.webView?.configuration.userContentController.addUserScript(script)
                        self.webView?.load(URLRequest(url: URL(string: localOrigin + "/")!, cachePolicy: .reloadIgnoringLocalCacheData))
                    }
                }.resume()
            }.resume()
        }

        private var healthIdentity: [String: Any] {
            ["service": "ready", "run_id": runID, "source_sha": identity.source_sha,
             "dirty": identity.dirty, "build_id": identity.build_id, "app_version": identity.app_version,
             "frontend_sha256": identity.frontend_sha256, "dependencies_sha256": identity.dependencies_sha256]
        }

        func urlSession(_ session: URLSession, task: URLSessionTask, willPerformHTTPRedirection response: HTTPURLResponse,
                        newRequest request: URLRequest, completionHandler: @escaping (URLRequest?) -> Void) {
            completionHandler(nil)
        }

        private func trustedMainFrame(_ candidate: WKWebView, _ frame: WKFrameInfo,
                                     allowsDirectories: Bool) -> Bool {
            guard let trustedWebView = webView, trustedWebView === candidate else { return false }
            return NativeUploadPolicy.permitsUpload(
                isMainFrame: frame.isMainFrame,
                allowsDirectories: allowsDirectories,
                originScheme: frame.securityOrigin.protocol,
                originHost: frame.securityOrigin.host,
                originPort: frame.securityOrigin.port,
                frameURL: frame.request.url,
                pageURL: candidate.url,
                expectedPort: apiPort
            )
        }

        // macOS disables WKWebView file uploads unless this optional delegate method is implemented.
        // Source: https://developer.apple.com/documentation/webkit/wkuidelegate/webview(_:runopenpanelwith:initiatedbyframe:completionhandler:)
        @MainActor
        func webView(_ webView: WKWebView, runOpenPanelWith parameters: WKOpenPanelParameters,
                     initiatedByFrame frame: WKFrameInfo,
                     completionHandler: @escaping ([URL]?) -> Void) {
            var selectedFiles: [URL]?
            if trustedMainFrame(webView, frame, allowsDirectories: parameters.allowsDirectories) {
                let panel = NSOpenPanel()
                panel.canChooseFiles = !parameters.allowsDirectories
                panel.canChooseDirectories = parameters.allowsDirectories
                panel.allowsMultipleSelection = parameters.allowsMultipleSelection
                if !parameters.allowsDirectories { panel.allowedContentTypes = NativeUploadPolicy.allowedContentTypes }
                panel.prompt = parameters.allowsDirectories ? "选择文件夹" : "选择文件"
                if panel.runModal() == .OK {
                    if parameters.allowsDirectories {
                        let result = NativeUploadPolicy.collectDirectoryFiles(at: panel.urls)
                        if let failure = result.failure {
                            let alert = NSAlert()
                            alert.messageText = "目录未导入"
                            alert.informativeText = failure
                            alert.runModal()
                        } else {
                            selectedFiles = result.files
                            if result.skippedCount > 0 {
                                let alert = NSAlert()
                                alert.messageText = "部分目录内容已跳过"
                                alert.informativeText = "导入列表仅包含支持的 TXT / Markdown 文件；已跳过 \(result.skippedCount) 项链接、不支持或超出单文件限制的内容。隐藏文件与应用包内容默认排除。"
                                alert.runModal()
                            }
                        }
                    } else {
                        switch NativeUploadPolicy.validateFileSelection(
                            panel.urls,
                            allowsMultipleSelection: parameters.allowsMultipleSelection
                        ) {
                        case .success(let files):
                            selectedFiles = files
                        case .failure:
                            let alert = NSAlert()
                            alert.messageText = "文件未导入"
                            alert.informativeText = NativeUploadPolicy.fileSelectionErrorMessage
                            alert.runModal()
                        }
                    }
                }
            }
            completionHandler(selectedFiles)
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationAction: WKNavigationAction,
                     decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
            guard let url = navigationAction.request.url else { decisionHandler(.cancel); return }
            if url.absoluteString == localOrigin + "/" ||
                (url.scheme == "http" && url.host == "127.0.0.1" && url.port == apiPort) {
                decisionHandler(.allow)
            } else if navigationAction.navigationType == .linkActivated, allowedOAuth(url), navigationAction.targetFrame == nil {
                NSWorkspace.shared.open(url)
                decisionHandler(.cancel)
            } else {
                decisionHandler(.cancel)
            }
        }

        func webView(_ webView: WKWebView, decidePolicyFor navigationResponse: WKNavigationResponse,
                     decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
            if let url = navigationResponse.response.url, url.scheme == "http", url.host == "127.0.0.1", url.port == apiPort {
                decisionHandler(.allow)
            } else {
                decisionHandler(.cancel)
            }
        }

        private func allowedOAuth(_ url: URL) -> Bool {
            let parts = URLComponents(url: url, resolvingAgainstBaseURL: false)
            return parts?.scheme == "https" && parts?.host == "accounts.feishu.cn"
                && (parts?.port == nil || parts?.port == 443) && parts?.user == nil && parts?.password == nil
                && parts?.fragment == nil && parts?.path == "/open-apis/authen/v1/authorize"
        }

        func userContentController(_ userContentController: WKUserContentController, didReceive message: WKScriptMessage) {
            guard message.name == "selectWorkspaceFolder", let webView,
                  trustedMainFrame(webView, message.frameInfo, allowsDirectories: true) else { return }
            let panel = NSOpenPanel()
            panel.canChooseFiles = false
            panel.canChooseDirectories = true
            panel.allowsMultipleSelection = false
            panel.prompt = "选择此文件夹"
            guard panel.runModal() == .OK, let path = panel.url?.path,
                  let data = try? JSONSerialization.data(withJSONObject: [path]),
                  let escaped = String(data: data, encoding: .utf8) else { return }
            let value = String(escaped.dropFirst().dropLast())
            webView.evaluateJavaScript("window.dispatchEvent(new CustomEvent('workspace-folder-selected', { detail: \(value) }));")
        }

        private func showReadinessError() {
            let alert = NSAlert()
            alert.messageText = "本地应用服务未就绪"
            alert.informativeText = "请保留此错误状态并联系维护者。候选包身份或本机端口可能不匹配。"
            alert.runModal()
            NSApp.terminate(nil)
        }
    }
}
