import Foundation
import XCTest
@testable import NativeUploadPolicy

final class NativeUploadPolicyTests: XCTestCase {
    func testUploadRequiresTrustedMainFrameAndRejectsDirectoryPickerRequests() {
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
        XCTAssertFalse(
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

    func testSelectedFilesMatchTxtAndMarkdownAndSelectionCount() {
        let text = URL(fileURLWithPath: "/tmp/synthetic.txt")
        let markdown = URL(fileURLWithPath: "/tmp/synthetic.MD")
        let executable = URL(fileURLWithPath: "/tmp/synthetic.command")

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
