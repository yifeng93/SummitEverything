import Foundation
import UniformTypeIdentifiers

public struct DirectoryUploadSelection {
    public let files: [URL]
    public let skippedCount: Int
    public let failure: String?
}

public enum NativeUploadPolicy {
    private static let supportedExtensions: Set<String> = ["txt", "md"]

    public static var allowedContentTypes: [UTType] {
        ["txt", "md"].compactMap { UTType(filenameExtension: $0, conformingTo: .plainText) }
    }

    public static func permitsUpload(
        isMainFrame: Bool,
        allowsDirectories: Bool,
        originScheme: String,
        originHost: String,
        originPort: Int,
        frameURL: URL?,
        pageURL: URL?,
        expectedPort: Int
    ) -> Bool {
        guard isMainFrame,
              originScheme == "http", originHost == "127.0.0.1", originPort == expectedPort,
              isTrustedURL(frameURL, expectedPort: expectedPort),
              isTrustedURL(pageURL, expectedPort: expectedPort) else { return false }
        return true
    }

    public static func acceptedFiles(_ urls: [URL], allowsMultipleSelection: Bool) -> [URL]? {
        guard !urls.isEmpty,
              urls.count <= 100,
              allowsMultipleSelection || urls.count == 1,
              urls.allSatisfy({
                  guard $0.isFileURL,
                        supportedExtensions.contains($0.pathExtension.lowercased()),
                        let values = try? $0.resourceValues(forKeys: [.isRegularFileKey, .isSymbolicLinkKey, .fileSizeKey]),
                        values.isRegularFile == true,
                        values.isSymbolicLink != true,
                        let size = values.fileSize else { return false }
                  return size > 0 && size <= 20 * 1024 * 1024
              }),
              urls.compactMap({ try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize }).reduce(0, +) <= 100 * 1024 * 1024 else { return nil }
        return urls
    }

    public static func collectDirectoryFiles(at roots: [URL]) -> DirectoryUploadSelection {
        let fileManager = FileManager.default
        var accepted: [URL] = []
        var seenPaths: Set<String> = []
        var skipped = 0
        var visited = 0
        var totalBytes: Int64 = 0
        guard !roots.isEmpty else { return DirectoryUploadSelection(files: [], skippedCount: 0, failure: nil) }
        for root in roots {
            let standardizedRoot = root.standardizedFileURL
            guard standardizedRoot.isFileURL,
                  !standardizedRoot.lastPathComponent.hasPrefix("."),
                  !["app", "bundle", "framework", "pkg"].contains(standardizedRoot.pathExtension.lowercased()),
                  let rootValues = try? standardizedRoot.resourceValues(forKeys: [.isDirectoryKey, .isSymbolicLinkKey, .isHiddenKey, .isPackageKey]),
                  rootValues.isDirectory == true,
                  rootValues.isSymbolicLink != true,
                  rootValues.isHidden != true,
                  rootValues.isPackage != true else {
                return DirectoryUploadSelection(files: [], skippedCount: skipped, failure: "无法读取所选文件夹；未导入。")
            }
            let rootPath = standardizedRoot.path.hasSuffix("/") ? standardizedRoot.path : standardizedRoot.path + "/"
            var scanFailed = false
            guard let enumerator = fileManager.enumerator(
                at: standardizedRoot,
                includingPropertiesForKeys: [.isDirectoryKey, .isRegularFileKey, .isSymbolicLinkKey, .isPackageKey, .fileSizeKey],
                options: [.skipsHiddenFiles, .skipsPackageDescendants],
                errorHandler: { _, _ in scanFailed = true; return false }
            ) else {
                return DirectoryUploadSelection(files: [], skippedCount: skipped, failure: "无法读取所选文件夹；未导入。")
            }
            for case let url as URL in enumerator {
                visited += 1
                guard visited <= 2_000 else {
                    return DirectoryUploadSelection(files: [], skippedCount: skipped, failure: "目录内容超过 2,000 项；未导入。")
                }
                let path = url.standardizedFileURL.path
                guard path.hasPrefix(rootPath) else { skipped += 1; continue }
                guard seenPaths.insert(path).inserted else { continue }
                guard let values = try? url.resourceValues(forKeys: [.isDirectoryKey, .isRegularFileKey, .isSymbolicLinkKey, .isPackageKey, .fileSizeKey]) else {
                    skipped += 1
                    continue
                }
                if values.isSymbolicLink == true || values.isPackage == true {
                    if values.isDirectory == true { enumerator.skipDescendants() }
                    skipped += 1
                    continue
                }
                if values.isDirectory == true { continue }
                guard values.isRegularFile == true,
                      supportedExtensions.contains(url.pathExtension.lowercased()),
                      let size = values.fileSize, size > 0, size <= 20 * 1024 * 1024 else {
                    skipped += 1
                    continue
                }
                guard accepted.count < 100, totalBytes + Int64(size) <= 100 * 1024 * 1024 else {
                    return DirectoryUploadSelection(files: [], skippedCount: skipped, failure: "所选目录超过 100 个文件或 100 MB；未导入。")
                }
                accepted.append(url)
                totalBytes += Int64(size)
            }
            if scanFailed {
                return DirectoryUploadSelection(files: [], skippedCount: skipped, failure: "无法完整读取所选目录；未导入。")
            }
        }
        return DirectoryUploadSelection(files: accepted, skippedCount: skipped, failure: nil)
    }

    private static func isTrustedURL(_ url: URL?, expectedPort: Int) -> Bool {
        guard let url,
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return false }
        return components.scheme == "http" && components.host == "127.0.0.1"
            && components.port == expectedPort && components.user == nil && components.password == nil
    }
}
