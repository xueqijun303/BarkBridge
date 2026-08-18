import CoreGraphics
import Foundation

if CommandLine.arguments.count != 3 && CommandLine.arguments.count != 4 {
    fputs("usage: mac-click x y [left|right]\n", stderr)
    exit(2)
}

guard let x = Double(CommandLine.arguments[1]), let y = Double(CommandLine.arguments[2]) else {
    fputs("invalid coordinates\n", stderr)
    exit(2)
}

let point = CGPoint(x: x, y: y)
let buttonName = CommandLine.arguments.count == 4 ? CommandLine.arguments[3].lowercased() : "left"
let button: CGMouseButton = buttonName == "right" ? .right : .left
let downType: CGEventType = buttonName == "right" ? .rightMouseDown : .leftMouseDown
let upType: CGEventType = buttonName == "right" ? .rightMouseUp : .leftMouseUp

CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: button)?.post(tap: .cghidEventTap)
usleep(80_000)
CGEvent(mouseEventSource: nil, mouseType: downType, mouseCursorPosition: point, mouseButton: button)?.post(tap: .cghidEventTap)
usleep(80_000)
CGEvent(mouseEventSource: nil, mouseType: upType, mouseCursorPosition: point, mouseButton: button)?.post(tap: .cghidEventTap)
usleep(250_000)
