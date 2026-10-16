import CoreGraphics
import Foundation

// Print "<windowID>\t<owner>\t<title>\t<w>x<h>" for on-screen windows whose
// owner or title matches the argument. Used to capture only the app window
// instead of the whole desktop.
let needle = CommandLine.arguments.count > 1 ? CommandLine.arguments[1] : "SummitEverything"
let options = CGWindowListOption(arrayLiteral: .optionOnScreenOnly, .excludeDesktopElements)
guard let windows = CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]] else {
    exit(2)
}
for window in windows {
    let owner = window[kCGWindowOwnerName as String] as? String ?? ""
    let title = window[kCGWindowName as String] as? String ?? ""
    guard owner.contains(needle) || title.contains(needle) else { continue }
    let id = window[kCGWindowNumber as String] as? Int ?? 0
    let bounds = window[kCGWindowBounds as String] as? [String: Any] ?? [:]
    let width = bounds["Width"] as? Double ?? 0
    let height = bounds["Height"] as? Double ?? 0
    print("\(id)\t\(owner)\t\(title)\t\(Int(width))x\(Int(height))")
}
