import Foundation

struct CatalogArtifact: Decodable {
    let repository: String
    let revision: String
    let filename: String
    let bytes: Int64
    let sha256: String
    var url: URL { URL(string: "https://huggingface.co/\(repository)/resolve/\(revision)/\(filename)")! }
}

struct CatalogModel: Decodable, Identifiable {
    let id: String
    let name: String
    let capabilities: [String]
    let summary: String
    let runtime_status: String
    let template: String
    let license: String
    let artifacts: [CatalogArtifact]
    let failed_experiences: [String]
    var downloadBytes: Int64 { artifacts.reduce(0) { $0 + $1.bytes } }
}

struct CatalogExperience: Decodable, Identifiable {
    let id: String
    let name: String
    let trial_order: [String]
    let fallback: String
}

struct CatalogSnapshot: Decodable {
    let as_of: String
    let runtime_revision: String
    let minimum_ios: Int
    let native_context_tokens: Int
    let models: [CatalogModel]
    let experiences: [CatalogExperience]
    let devices: [CatalogDevice]
}

struct CatalogDevice: Decodable {
    let id: String
    let name: String
}

struct ModelSuggestion: Identifiable {
    let model: CatalogModel
    let status: String
    var id: String { model.id }
    var eligibleForTrial: Bool { status == "needs_device_evidence" }
    var explanation: String {
        switch status {
        case "known_task_failure": return "Failed the existing shopping tests; use reviewed manual filters."
        case "requires_runtime_integration": return "This capability needs additional app support."
        case "unsupported_or_unknown_device": return "This phone is outside the current evaluation list."
        case "unsupported_or_unknown_os": return "The current Pocket runtime requires iOS 26 or newer."
        case "weights_exceed_memory_budget": return "Weight file size reaches the test allowance; excluded conservatively."
        case "invalid_memory_budget": return "Enter a positive whole-number memory allowance."
        default: return "Candidate for testing. Task quality and complete memory use are unverified."
        }
    }
}

enum ModelSuggestions {
    static let catalog = try! JSONDecoder().decode(CatalogSnapshot.self, from: Data(GeneratedModelCatalog.json.utf8))

    static func targetDevice(_ device: String) -> Bool {
        catalog.devices.contains { $0.id == device }
    }

    static func suggestions(experience: String, device: String, osMajor: Int,
                            memoryBudgetBytes: Int64? = nil, smallestDownload: Bool = false) -> [ModelSuggestion] {
        guard let task = catalog.experiences.first(where: { $0.id == experience }) else { return [] }
        let priorities = Dictionary(uniqueKeysWithValues: task.trial_order.enumerated().map { ($1, $0) })
        return catalog.models.filter { $0.capabilities.contains(experience) }.map { model in
            let status: String
            if model.runtime_status != "native_text_candidate" { status = "requires_runtime_integration" }
            else if model.failed_experiences.contains(experience) { status = "known_task_failure" }
            else if !targetDevice(device) { status = "unsupported_or_unknown_device" }
            else if osMajor < catalog.minimum_ios { status = "unsupported_or_unknown_os" }
            else if let budget = memoryBudgetBytes, budget <= 0 { status = "invalid_memory_budget" }
            else if let budget = memoryBudgetBytes, model.downloadBytes >= budget { status = "weights_exceed_memory_budget" }
            else { status = "needs_device_evidence" }
            return ModelSuggestion(model: model, status: status)
        }.sorted {
            if smallestDownload { return ($0.model.downloadBytes, $0.id) < ($1.model.downloadBytes, $1.id) }
            return (priorities[$0.id]!, $0.id) < (priorities[$1.id]!, $1.id)
        }
    }
}
