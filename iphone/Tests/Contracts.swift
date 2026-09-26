import Foundation
import CryptoKit

@main struct ContractTests {
    static func main() throws {
        let draft = try ShoppingDraft.parse(#"{"maxPrice":150,"strap":"blue"}"#)
        precondition(draft == ShoppingDraft(maxPrice: 150, strap: "blue"))
        let invalid = [#"{"maxPrice":-1,"strap":null}"#, #"{"maxPrice":true,"strap":null}"#,
                       #"{"maxPrice":100001,"strap":null}"#, #"{"maxPrice":10,"strap":"red"}"#,
                       #"{"maxPrice":10,"strap":null,"buy":true}"#, #"{}"#, "not JSON"]
        for text in invalid { precondition((try? ShoppingDraft.parse(text)) == nil, text) }
        precondition(SampleOffer.matching(ShoppingDraft(maxPrice: 120, strap: "blue")).map(\.id) == ["W1"])
        precondition(SampleOffer.matching(ShoppingDraft(maxPrice: 119, strap: "blue")).isEmpty)
        precondition(SampleOffer.matching(ShoppingDraft(maxPrice: nil, strap: nil)).count == 3)
        let dir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: dir) }
        let url = dir.appendingPathComponent("test.gguf")
        let data = Data("verified-model".utf8)
        let sha = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        let model = LocalModel(id: "fixture", title: "fixture", filename: "test.gguf", sha256: sha, bytes: Int64(data.count), template: "qwen")
        try data.write(to: url); try ModelFiles.verify(url, model: model)
        try Data("tampered-model".utf8).write(to: url)
        do { try ModelFiles.verify(url, model: model); preconditionFailure("Accepted altered model") } catch {}
        try Data().write(to: url)
        do { try ModelFiles.verify(url, model: model); preconditionFailure("Accepted wrong size") } catch {}
        print("Native contracts passed: typed preferences, catalog boundaries, model identity")
    }
}
