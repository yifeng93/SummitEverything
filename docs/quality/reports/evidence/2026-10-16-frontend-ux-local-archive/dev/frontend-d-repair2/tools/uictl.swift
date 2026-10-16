import CoreGraphics
import Foundation

// Minimal UI control probe: can this process deliver synthetic mouse events?
// `move x y` posts a mouse-moved event and reports where the cursor ended up.
func currentLocation() -> CGPoint {
    CGEvent(source: nil)?.location ?? .zero
}

let args = CommandLine.arguments
guard args.count >= 2 else { exit(2) }
switch args[1] {
case "where":
    let point = currentLocation()
    print("\(Int(point.x))\t\(Int(point.y))")
case "move":
    guard args.count >= 4, let x = Double(args[2]), let y = Double(args[3]) else { exit(2) }
    let before = currentLocation()
    let target = CGPoint(x: x, y: y)
    let event = CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: target, mouseButton: .left)
    event?.post(tap: .cghidEventTap)
    usleep(250_000)
    let after = currentLocation()
    print("before=\(Int(before.x)),\(Int(before.y)) requested=\(Int(x)),\(Int(y)) after=\(Int(after.x)),\(Int(after.y))")
    print("delivered=\(abs(after.x - x) < 3 && abs(after.y - y) < 3)")
case "click":
    guard args.count >= 4, let x = Double(args[2]), let y = Double(args[3]) else { exit(2) }
    let point = CGPoint(x: x, y: y)
    CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(120_000)
    CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(60_000)
    CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
    usleep(250_000)
    let after = currentLocation()
    print("clicked=\(Int(x)),\(Int(y)) cursor=\(Int(after.x)),\(Int(after.y))")
default:
    exit(2)
}
