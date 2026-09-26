import Foundation
import CryptoKit

struct LocalModel: Identifiable, Codable, Equatable, Hashable {
    let id: String
    let title: String
    let filename: String
    let sha256: String
    let bytes: Int64
    let template: String
    static let catalog = [
        LocalModel(id: "qwen08", title: "Qwen3.5 0.8B · 533 MB", filename: "Qwen3.5-0.8B-Q4_K_M.gguf", sha256: "bd258782e35f7f458f8aced1adc053e6e92e89bc735ba3be89d38a06121dc517", bytes: 532517120, template: "qwen"),
        LocalModel(id: "qwen2", title: "Qwen3.5 2B · 1.28 GB", filename: "Qwen3.5-2B-Q4_K_M.gguf", sha256: "aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223", bytes: 1280835840, template: "qwen"),
        LocalModel(id: "liquid350", title: "Liquid 350M · 219 MB", filename: "LFM2.5-350M-QAD-Q4_0.gguf", sha256: "3d10b6ab8fc91a919534b9558e266255aca0bbc7f6d015963599aa9e74e05b1d", bytes: 219312832, template: "lfm2")
    ]
    func prompt(system: String, user: String) -> String {
        "<|im_start|>system\n\(system)<|im_end|>\n<|im_start|>user\n\(user)<|im_end|>\n<|im_start|>assistant\n" + (template == "qwen" ? "<think>\n\n</think>\n\n" : "")
    }
}

enum RuntimeFailure: LocalizedError {
    case message(String)
    var errorDescription: String? { if case .message(let text) = self { return text }; return nil }
}

enum ModelFiles {
    static var directory: URL {
        FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0].appendingPathComponent("Models", isDirectory: true)
    }
    static func url(_ model: LocalModel) -> URL { directory.appendingPathComponent(model.filename) }
    static func verify(_ url: URL, model: LocalModel) throws {
        let size = try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber
        guard size?.int64Value == model.bytes else { throw RuntimeFailure.message("Model size does not match the selected version") }
        let handle = try FileHandle(forReadingFrom: url); defer { try? handle.close() }
        var hash = SHA256()
        // Drain Foundation's temporary buffers between chunks, before loading weights.
        while try autoreleasepool(invoking: { () throws -> Bool in
            guard let data = try handle.read(upToCount: 4 * 1024 * 1024), !data.isEmpty else { return false }
            hash.update(data: data)
            return true
        }) {}
        let digest = hash.finalize().map { String(format: "%02x", $0) }.joined()
        guard digest == model.sha256 else { throw RuntimeFailure.message("Model verification failed. Choose the exact supported file.") }
    }
    static func importFile(_ source: URL, model: LocalModel) throws {
        let access = source.startAccessingSecurityScopedResource(); defer { if access { source.stopAccessingSecurityScopedResource() } }
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let temp = directory.appendingPathComponent(UUID().uuidString + ".partial")
        defer { try? FileManager.default.removeItem(at: temp) }
        try FileManager.default.copyItem(at: source, to: temp)
        try verify(temp, model: model)
        let destination = url(model)
        if FileManager.default.fileExists(atPath: destination.path) {
            _ = try FileManager.default.replaceItemAt(destination, withItemAt: temp)
        } else { try FileManager.default.moveItem(at: temp, to: destination) }
        var resource = destination
        var values = URLResourceValues(); values.isExcludedFromBackup = true
        try resource.setResourceValues(values)
    }
}
