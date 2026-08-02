import CoreGraphics
import Foundation

if CommandLine.arguments.count != 3 {
    fputs("usage: mac-click x y\n", stderr)
    exit(2)
}

guard let x = Double(CommandLine.arguments[1]), let y = Double(CommandLine.arguments[2]) else {
    fputs("invalid coordinates\n", stderr)
    exit(2)
}

let point = CGPoint(x: x, y: y)
CGEvent(mouseEventSource: nil, mouseType: .mouseMoved, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
usleep(80_000)
CGEvent(mouseEventSource: nil, mouseType: .leftMouseDown, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
usleep(80_000)
CGEvent(mouseEventSource: nil, mouseType: .leftMouseUp, mouseCursorPosition: point, mouseButton: .left)?.post(tap: .cghidEventTap)
usleep(250_000)
