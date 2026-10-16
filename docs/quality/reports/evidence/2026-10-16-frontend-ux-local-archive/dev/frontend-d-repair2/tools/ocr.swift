import AppKit
import Foundation
import Vision

// On-device OCR for the app window screenshots, so the native UI state can be
// asserted programmatically instead of being eyeballed.
guard CommandLine.arguments.count > 1 else { exit(2) }
let path = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: path),
      let tiff = image.tiffRepresentation,
      let bitmap = NSBitmapImageRep(data: tiff),
      let cgImage = bitmap.cgImage else {
    FileHandle.standardError.write(Data("cannot load image\n".utf8))
    exit(3)
}
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.recognitionLanguages = ["zh-Hans", "en-US"]
request.usesLanguageCorrection = true
let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
do {
    try handler.perform([request])
} catch {
    FileHandle.standardError.write(Data("ocr failed: \(error)\n".utf8))
    exit(4)
}
for observation in request.results ?? [] {
    if let candidate = observation.topCandidates(1).first {
        print(candidate.string)
    }
}
