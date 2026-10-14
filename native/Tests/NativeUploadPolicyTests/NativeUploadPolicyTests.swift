import Foundation
import XCTest
@testable import NativeUploadPolicy

final class NativeUploadPolicyTests: XCTestCase {
    func testUploadRequiresTrustedMainFrameAndAllowsTrustedDirectoryPickerRequests() {
        let trusted = URL(string: "http://127.0.0.1:18793/")!
        XCTAssertTrue(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: trusted,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: false,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: trusted,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "https",
                originHost: "evil.example",
                originPort: 443,
                frameURL: URL(string: "https://evil.example/")!,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18794,
                frameURL: URL(string: "http://127.0.0.1:18794/")!,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "localhost",
                originPort: 18793,
                frameURL: URL(string: "http://localhost:18793/")!,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: trusted,
                pageURL: URL(string: "https://evil.example/")!,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: URL(string: "http://user@127.0.0.1:18793/")!,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertFalse(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: false,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: URL(string: "https://evil.example/")!,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
        XCTAssertTrue(
            NativeUploadPolicy.permitsUpload(
                isMainFrame: true,
                allowsDirectories: true,
                originScheme: "http",
                originHost: "127.0.0.1",
                originPort: 18793,
                frameURL: trusted,
                pageURL: trusted,
                expectedPort: 18793
            )
        )
    }

    func testDirectoryCollectionKeepsOnlyBoundedVisibleTxtAndMarkdownFilesWithoutFollowingLinks() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        let nested = root.appendingPathComponent("nested", isDirectory: true)
        let hidden = root.appendingPathComponent(".private", isDirectory: true)
        let outside = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: nested, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: hidden, withIntermediateDirectories: true)
        try FileManager.default.createDirectory(at: outside, withIntermediateDirectories: true)
        defer {
            try? FileManager.default.removeItem(at: root)
            try? FileManager.default.removeItem(at: outside)
        }
        let markdown = nested.appendingPathComponent("notes.md")
        let text = root.appendingPathComponent("readme.TXT")
        try Data("合成内容".utf8).write(to: markdown)
        try Data("合成内容".utf8).write(to: text)
        try Data("hidden".utf8).write(to: hidden.appendingPathComponent("hidden.txt"))
        try Data("unsupported".utf8).write(to: root.appendingPathComponent("image.pdf"))
        try Data("outside".utf8).write(to: outside.appendingPathComponent("outside.txt"))
        try FileManager.default.createSymbolicLink(
            at: root.appendingPathComponent("linked"), withDestinationURL: outside
        )

        let result = NativeUploadPolicy.collectDirectoryFiles(at: [root, root])
        XCTAssertNil(result.failure)
        XCTAssertEqual(Set(result.files.map(\.lastPathComponent)), Set(["notes.md", "readme.TXT"]))
        XCTAssertEqual(result.files.count, 2)
        XCTAssertGreaterThanOrEqual(result.skippedCount, 1)

        let hiddenRoot = root.deletingLastPathComponent().appendingPathComponent(".hidden-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: hiddenRoot, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: hiddenRoot) }
        XCTAssertNotNil(NativeUploadPolicy.collectDirectoryFiles(at: [hiddenRoot]).failure)
        XCTAssertNotNil(NativeUploadPolicy.collectDirectoryFiles(at: [root.appendingPathComponent("linked")]).failure)
    }

    func testSelectedFilesMatchTxtAndMarkdownAndSelectionCount() throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let text = root.appendingPathComponent("synthetic.txt")
        let markdown = root.appendingPathComponent("synthetic.MD")
        let executable = root.appendingPathComponent("synthetic.command")
        try Data("text".utf8).write(to: text)
        try Data("markdown".utf8).write(to: markdown)
        try Data("command".utf8).write(to: executable)

        XCTAssertEqual(NativeUploadPolicy.acceptedFiles([text], allowsMultipleSelection: false), [text])
        XCTAssertEqual(NativeUploadPolicy.acceptedFiles([markdown], allowsMultipleSelection: false), [markdown])
        XCTAssertNil(NativeUploadPolicy.acceptedFiles([], allowsMultipleSelection: false))
        XCTAssertNil(NativeUploadPolicy.acceptedFiles([text, markdown], allowsMultipleSelection: false))
        XCTAssertEqual(
            NativeUploadPolicy.acceptedFiles([text, markdown], allowsMultipleSelection: true),
            [text, markdown]
        )
        XCTAssertNil(NativeUploadPolicy.acceptedFiles([text, executable], allowsMultipleSelection: true))
    }

    func testOpenPanelTypesAreLimitedToTxtAndMarkdown() {
        XCTAssertEqual(
            Set(NativeUploadPolicy.allowedContentTypes.compactMap(\.preferredFilenameExtension)),
            ["txt", "md"]
        )
    }
}
