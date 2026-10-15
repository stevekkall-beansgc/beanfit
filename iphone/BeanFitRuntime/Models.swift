import Foundation
import CryptoKit

struct LocalModel: Identifiable, Codable, Equatable, Hashable {
    let id: String
    let title: String
    let filename: String
    let sha256: String
    let bytes: Int64
    let template: String
    static let catalog: [LocalModel] = ModelSuggestions.catalog.models.compactMap { model in
        guard model.runtime_status == "native_text_candidate", let artifact = model.artifacts.first else { return nil }
        return LocalModel(id: model.id, title: "\(model.name) · \(artifact.bytes / 1_000_000) MB",
                          filename: artifact.filename, sha256: artifact.sha256,
                          bytes: artifact.bytes, template: model.template)
    }
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
    static func verify(_ url: URL, model: LocalModel, shouldCancel: () -> Bool = { false }) throws {
        let size = try FileManager.default.attributesOfItem(atPath: url.path)[.size] as? NSNumber
        guard size?.int64Value == model.bytes else { throw RuntimeFailure.message("Model size does not match the selected version") }
        let handle = try FileHandle(forReadingFrom: url); defer { try? handle.close() }
        var hash = SHA256()
        // Drain Foundation's temporary buffers between chunks, before loading weights.
        while try autoreleasepool(invoking: { () throws -> Bool in
            if shouldCancel() { throw CancellationError() }
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
