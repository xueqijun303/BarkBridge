import Foundation
import Vision

if CommandLine.arguments.count != 2 {
    fputs("usage: mac-ocr image-path\n", stderr)
    exit(2)
}

let imageURL = URL(fileURLWithPath: CommandLine.arguments[1])
let request = VNRecognizeTextRequest()
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
request.recognitionLanguages = ["zh-Hans", "zh-Hant", "en-US"]

let handler = VNImageRequestHandler(url: imageURL, options: [:])
do {
    try handler.perform([request])
    let texts = (request.results ?? [])
        .compactMap { $0.topCandidates(1).first?.string.trimmingCharacters(in: .whitespacesAndNewlines) }
        .filter { !$0.isEmpty }
    print(texts.joined(separator: "\n"))
} catch {
    fputs("ocr failed: \(error)\n", stderr)
    exit(1)
}
