import Foundation
let url = URL(string: CommandLine.arguments[1])!
let semaphore = DispatchSemaphore(value: 0)
URLSession.shared.dataTask(with: url) { _, response, error in
    let actual = response?.url
    print("configured=\(url.absoluteString)")
    print("response=\(actual?.absoluteString ?? "nil")")
    print("equal=\(actual == url)")
    print("status=\((response as? HTTPURLResponse)?.statusCode ?? 0)")
    print("error=\(error?.localizedDescription ?? "none")")
    semaphore.signal()
}.resume()
if semaphore.wait(timeout: .now() + 5) == .timedOut { exit(2) }
