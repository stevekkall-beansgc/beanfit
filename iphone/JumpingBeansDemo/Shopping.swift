import Foundation

struct ShoppingDraft: Codable, Equatable {
    var maxPrice: Double?
    var strap: String?
    static func parse(_ text: String) throws -> ShoppingDraft {
        guard let data = text.data(using: .utf8),
              let object = try JSONSerialization.jsonObject(with: data) as? [String: Any],
              Set(object.keys) == Set(["maxPrice", "strap"]) else { throw RuntimeFailure.message("The suggestion had invalid fields. Please edit the filters yourself.") }
        let draft = try JSONDecoder().decode(ShoppingDraft.self, from: data)
        guard draft.maxPrice == nil || (draft.maxPrice!.isFinite && draft.maxPrice! >= 0 && draft.maxPrice! <= 100000),
              draft.strap == nil || ["blue", "black", "steel"].contains(draft.strap!) else {
            throw RuntimeFailure.message("The suggested filters are outside this demo's supported range")
        }
        return draft
    }
}
struct SampleOffer: Identifiable {
    let id: String, name: String, strap: String
    let price: Double
    static let catalog = [SampleOffer(id: "W1", name: "Cedar", strap: "blue", price: 120),
                          SampleOffer(id: "W2", name: "Harbor", strap: "black", price: 180),
                          SampleOffer(id: "W3", name: "Summit", strap: "steel", price: 240)]
    static func matching(_ draft: ShoppingDraft) -> [SampleOffer] {
        catalog.filter { (draft.maxPrice == nil || $0.price <= draft.maxPrice!) && (draft.strap == nil || $0.strap == draft.strap!) }
    }
}
/// Reusable product adapter: model suggests filters; application owns catalog truth and user approval.
struct ShoppingAdapter {
    let runtime: LocalInferenceClient
    static let grammar = #"""
root ::= "{" ws "\"maxPrice\":" ws price "," ws "\"strap\":" ws strap ws "}"
price ::= "null" | [0-9]+ ("." [0-9]+)?
strap ::= "null" | "\"blue\"" | "\"black\"" | "\"steel\""
ws ::= [ \t\n\r]*
"""#
    func suggest(_ request: String) async throws -> (ShoppingDraft, InferenceResult) {
        let result = try await runtime.generate(system: "Extract watch preferences from the user's request. Return only JSON with maxPrice (number or null, USD) and strap (blue, black, steel, or null). Apply explicit corrections. Missing preferences are null. Never claim a purchase or saved preferences. These are editable suggestions for user review.", user: request, grammar: Self.grammar, maxTokens: 96)
        return (try ShoppingDraft.parse(result.text), result)
    }
}
