import Foundation

struct Measurement: Codable, Identifiable {
    let id: UUID
    let stage: String
    let model: String
    let modelSHA256: String
    let evidenceKind: String
    let device: String
    let os: String
    let contextTokens: Int
    let startedAt: Date
    let durationMs: Double
    let firstTokenMs: Double?
    let outputTokens: Int
    let baselineProcessBytes: UInt64
    let observedPeakProcessBytes: UInt64
    let endProcessBytes: UInt64
    let memorySamples: Int
    let outcome: String
    let thermalBefore: Int
    let thermalAfter: Int
    let memoryAccounting: String = "Sampled task_vm_info.phys_footprint at 20ms; app process only, may miss peaks; excludes unaccounted system services. Not whole-stack qualification."
}

struct MeasuredFailure: LocalizedError {
    let message: String
    let measurement: Measurement
    var errorDescription: String? { message }
}

struct InferenceResult {
    let text: String
    let measurement: Measurement
}

protocol LocalInferenceClient: AnyObject {
    func load(_ model: LocalModel) async throws -> Measurement
    func generate(system: String, user: String, grammar: String?, maxTokens: Int) async throws -> InferenceResult
    func unload() async
    func cancel()
}
