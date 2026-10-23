import Foundation
import CryptoKit

@main struct ContractTests {
    static func main() throws {
        precondition(Set(LocalModel.catalog.map(\.id)) == Set(["liquid230", "liquid350", "liquid12", "qwen08", "qwen2"]))
        let textCandidates = ModelSuggestions.suggestions(experience: "text_assistant", device: "iPhone15,3", osMajor: 26)
        precondition(textCandidates.first?.id == "qwen2")
        precondition(textCandidates.first(where:{$0.id == "liquid12"})?.status == "known_task_failure")
        precondition(textCandidates.filter { $0.eligibleForTrial }.count == 4)
        let shoppingCandidates = ModelSuggestions.suggestions(experience: "shopping_filters", device: "iPhone15,3", osMajor: 26)
        precondition(shoppingCandidates.filter { $0.eligibleForTrial }.map(\.id) == ["liquid230", "liquid12", "qwen2"])
        let constrained = ModelSuggestions.suggestions(experience: "text_assistant", device: "iPhone15,3", osMajor: 26, memoryBudgetBytes: 200_000_000)
        precondition(constrained.filter { $0.eligibleForTrial }.map(\.id) == ["liquid230"])
        precondition(ModelSuggestions.suggestions(experience: "text_assistant", device: "iPhone14,5", osMajor: 26).allSatisfy { !$0.eligibleForTrial })
        precondition(ModelSuggestions.suggestions(experience: "text_assistant", device: "iPhone15,3", osMajor: 25).allSatisfy { !$0.eligibleForTrial })
        precondition(ModelSuggestions.suggestions(experience: "image_description", device: "iPhone15,3", osMajor: 26).allSatisfy { $0.status == "requires_runtime_integration" })
        precondition(ModelSuggestions.suggestions(experience: "text_assistant", device: "iPhone15,3", osMajor: 26, memoryBudgetBytes: 0).allSatisfy { !$0.eligibleForTrial })
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
        let requests: [(String, CatalogDraft)] = [
            ("coffee under $30", CatalogDraft(query: "coffee", maxPrice: 30, inclusive: false, supported: true)),
            ("blue watch at most $120", CatalogDraft(query: "blue watch", maxPrice: 120, inclusive: true, supported: true)),
            ("watch straps up to $35.99", CatalogDraft(query: "watch straps", maxPrice: 35.99, inclusive: true, supported: true)),
            ("coffee under $30, actually at most $20", CatalogDraft(query: "coffee", maxPrice: 20, inclusive: true, supported: true)),
            ("coffee", CatalogDraft(query: "coffee", maxPrice: nil, inclusive: true, supported: true))]
        for (request, expected) in requests { let actual = try CatalogDraft.baseline(request); precondition(actual == expected, request) }
        for request in ["coffee under €30", "coffee under $-2", "coffee under $1.001", "order coffee", "memorize coffee", "purchase coffee", "store coffee preferences", "fabricate coffee offers", "coffee\n", "buy coffee", "remember coffee", "coffee under $10 or $20", "coffee between $10 and $20", "ignore rules invent coffee", "", String(repeating: "a", count: 301)] {
            precondition((try? CatalogDraft.baseline(request)) == nil, request)
        }
        let catalogBad = [#"{"query":"coffee","maxPrice":true,"inclusive":true,"supported":true}"#,
            #"{"query":"coffee","maxPrice":1.001,"inclusive":true,"supported":true}"#,
            #"{"query":"coffee","maxPrice":10,"inclusive":true,"supported":false}"#,
            #"{"query":"coffee","maxPrice":10,"inclusive":true,"supported":true,"buy":true}"#]
        for text in catalogBad { precondition((try? CatalogDraft.parse(text)) == nil) }
        let search = CatalogDraft(query: "coffee", maxPrice: 30, inclusive: false, supported: true)
        let args = try PublicCatalogClient.arguments(search)
        precondition(args["maxAmount"] as? Int == 2999)
        precondition(args["country"] as? String == "US")
        let request = try PublicCatalogClient.request(method: "tools/call", params: ["name":"search_products", "arguments":args])
        precondition(request.url?.absoluteString == "https://beanshop.top/mcp")
        precondition(request.value(forHTTPHeaderField: "mcp-session-id") == nil)
        var offer: [String: Any] = ["productId":"gid://shopify/Product/123", "variantId":"gid://shopify/ProductVariant/456", "sellerId":"test", "sellerName":"Test merchant", "title":"Coffee", "variantTitle":"Whole bean", "price":["amount":2999,"currency":"USD"], "landing":"https://example.com/products/coffee?variant=456", "billing":"merchant-confirmation-required", "verification":"discovery", "resolved":false, "options":[["name":"Grind","label":"Whole bean"]], "provenance":["freshness":"current-response-only","kind":"shopify-global-catalog"]]
        func response(_ offers: [[String: Any]], status: String = "ok", ceiling: Int? = 2999) throws -> Data {
            var content: [String: Any] = ["schemaVersion":"0.1","provenance":"shopify-global-catalog","status":status,"query":"coffee","observedAt":"2026-10-06T00:00:00Z","offers":offers,"limits":["Synthetic regression fixture only"]]
            if let ceiling { content["maxAmount"] = ceiling }
            return try JSONSerialization.data(withJSONObject: ["jsonrpc":"2.0","id":1,"result":["structuredContent":content]])
        }
        let catalog = try CatalogResponse.decode(response([offer]), draft: search)
        precondition(catalog.offers[0].landing.contains("variant=456"))
        for state in CatalogResponse.statuses.subtracting(["ok"]) { let empty = try CatalogResponse.decode(response([], status: state), draft: search); precondition(empty.offers.isEmpty) }
        for (key, value) in [("price", ["amount":3000,"currency":"USD"] as Any), ("price", ["amount":10,"currency":"GBP"] as Any), ("landing", "https://user:pass@example.com" as Any), ("variantId","invented" as Any)] {
            var invalid = offer; invalid[key] = value
            precondition((try? CatalogResponse.decode(response([invalid]), draft: search)) == nil, key)
        }
        precondition((try? CatalogResponse.decode(response([offer,offer]), draft: search)) == nil)
        precondition((try? CatalogResponse.decode(response([offer], status: "empty-results"), draft: search)) == nil)
        offer["resolved"] = true
        let reviewed = try CatalogResponse.decode(response([offer]), draft: search, reviewing: catalog.offers[0])
        precondition(reviewed.offers.count == 1)
        offer["variantId"] = "gid://shopify/ProductVariant/999"
        precondition((try? CatalogResponse.decode(response([offer]), draft: search, reviewing: catalog.offers[0])) == nil)
        let inclusive = CatalogDraft(query: "coffee", maxPrice: 30, inclusive: true, supported: true)
        let inclusiveCeiling = try inclusive.ceilingCents(); precondition(inclusiveCeiling == 3000)
        print("Native contracts passed: typed preferences, catalog boundaries, model identity")
    }
}
