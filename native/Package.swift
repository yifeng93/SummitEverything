// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "SummitEverything",
    platforms: [.macOS(.v13)],
    products: [.executable(name: "SummitEverything", targets: ["SummitEverythingApp"])],
    targets: [
        .target(name: "NativeUploadPolicy"),
        .executableTarget(name: "SummitEverythingApp", dependencies: ["NativeUploadPolicy"]),
        .testTarget(name: "NativeUploadPolicyTests", dependencies: ["NativeUploadPolicy"]),
    ]
)
