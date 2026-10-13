import Foundation
import UniformTypeIdentifiers

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
        guard isMainFrame, !allowsDirectories,
              originScheme == "http", originHost == "127.0.0.1", originPort == expectedPort,
              isTrustedURL(frameURL, expectedPort: expectedPort),
              isTrustedURL(pageURL, expectedPort: expectedPort) else { return false }
        return true
    }

    public static func acceptedFiles(_ urls: [URL], allowsMultipleSelection: Bool) -> [URL]? {
        guard !urls.isEmpty,
              allowsMultipleSelection || urls.count == 1,
              urls.allSatisfy({
                  $0.isFileURL && supportedExtensions.contains($0.pathExtension.lowercased())
              }) else { return nil }
        return urls
    }

    private static func isTrustedURL(_ url: URL?, expectedPort: Int) -> Bool {
        guard let url,
              let components = URLComponents(url: url, resolvingAgainstBaseURL: false) else { return false }
        return components.scheme == "http" && components.host == "127.0.0.1"
            && components.port == expectedPort && components.user == nil && components.password == nil
    }
}
