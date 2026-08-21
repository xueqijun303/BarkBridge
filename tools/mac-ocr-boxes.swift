import Foundation
import Vision
import ImageIO

if CommandLine.arguments.count != 2 {
    fputs("usage: mac-ocr-boxes image-path\n", stderr)
    exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
guard
    let source = CGImageSourceCreateWithURL(imageURL as CFURL, nil),
    let props = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
    let width = props[kCGImagePropertyPixelWidth] as? CGFloat,
    let height = props[kCGImagePropertyPixelHeight] as? CGFloat
else {
    fputs("failed to read image size\n", stderr)
    exit(1)
}

let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]

let handler = VNImageRequestHandler(url: imageURL, options: [:])
do {
    try handler.perform([request])
    let rows: [[String: Any]] = (request.results ?? []).compactMap { observation in
        guard let text = observation.topCandidates(1).first?.string.trimmingCharacters(in: .whitespacesAndNewlines), !text.isEmpty else {
            return nil
        }
        let box = observation.boundingBox
        return [
            "text": text,
            "x": box.minX * width,
            "y": (1.0 - box.maxY) * height,
            "width": box.width * width,
            "height": box.height * height
        ]
    }
    let data = try JSONSerialization.data(withJSONObject: rows, options: [])
    FileHandle.standardOutput.write(data)
    print("")
} catch {
    fputs("ocr boxes failed: \(error)\n", stderr)
    exit(1)
}
