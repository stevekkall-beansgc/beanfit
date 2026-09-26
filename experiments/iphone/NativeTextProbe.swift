// Research component, not an installable app or a voice benchmark.
// Call only from an explicitly authorized native test harness. No downloads,
// URLSession, tools, private context, or cloud model routing are configured.
import Foundation
import FoundationModels
import UIKit
import Darwin

struct TextProbeReceipt: Encodable {
    let schema = "beanfit.iphone.text.v1"
    let scope = "text_only"
    let inference_location = "on_device"
    // Selecting a local model is not a network-isolation experiment.
    let offline_verified = false
    let case_id = "synthetic-bluebird-v1"
    let evidence_kind: String
    let device: String
    let os_build: String
    let runtime = "Apple FoundationModels / SystemLanguageModel.default"
    let model: String
    let recorded_at: String
    let availability: String
    let context_tokens: Int
    var outcome = "not_run"
    var first_text_ms: Double?
    var total_ms: Double?
    var response_characters = 0
    var contains_expected_word = false // Diagnostic only, not a quality verdict.
    var error_type: String?
    let thermal_before: String
    var thermal_after: String

    func json() throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(self)
    }
}

@available(iOS 26.0, *)
@MainActor
enum NativeTextProbe {
    static func run(infer: Bool = false) async -> TextProbeReceipt {
        let model = SystemLanguageModel.default
        let process = ProcessInfo.processInfo
        var system = utsname()
        uname(&system)
        let machine = withUnsafeBytes(of: &system.machine) { bytes in
            String(decoding: bytes.prefix(while: { $0 != 0 }), as: UTF8.self)
        }
        #if targetEnvironment(simulator)
        let kind = "simulator"
        #elseif targetEnvironment(macCatalyst)
        let kind = "unsupported_device"
        #else
        // This file is iOS-only; do not classify iPad/Mac compatibility as iPhone.
        let kind = UIDevice.current.userInterfaceIdiom == .phone && !process.isiOSAppOnMac
            ? "physical_device" : "unsupported_device"
        #endif
        let variant: String
        if #available(iOS 27.0, *) {
            variant = model.variant.displayName
        } else {
            variant = "system-managed; exact weights not exposed"
        }
        var receipt = TextProbeReceipt(
            evidence_kind: kind, device: machine,
            os_build: process.operatingSystemVersionString, model: variant,
            recorded_at: ISO8601DateFormatter().string(from: Date()),
            availability: String(describing: model.availability),
            context_tokens: model.contextSize,
            thermal_before: String(describing: process.thermalState),
            thermal_after: String(describing: process.thermalState)
        )
        guard model.availability == .available else {
            receipt.outcome = "unavailable"
            return receipt
        }
        guard infer, kind != "unsupported_device" else { return receipt }
        // A fresh session for every trial. System model cache state is unknown.
        let session = LanguageModelSession(model: model, instructions:
            "Answer briefly using only the supplied fictional fact. Do not call tools.")
        let start = ContinuousClock.now
        func elapsedMS() -> Double {
            let value = start.duration(to: .now).components
            return Double(value.seconds) * 1000 + Double(value.attoseconds) / 1e15
        }
        do {
            let stream = session.streamResponse(
                to: "Fictional fact: Bluebird's badge is amber. What color is Bluebird's badge?",
                options: GenerationOptions(temperature: 0, maximumResponseTokens: 64)
            )
            var finalText = ""
            for try await snapshot in stream {
                try Task.checkCancellation()
                if !snapshot.content.isEmpty && receipt.first_text_ms == nil {
                    receipt.first_text_ms = elapsedMS()
                }
                // Streaming snapshots contain cumulative text, not token deltas.
                finalText = snapshot.content
            }
            receipt.total_ms = elapsedMS()
            receipt.response_characters = finalText.count
            receipt.contains_expected_word = finalText.lowercased().contains("amber")
            receipt.outcome = finalText.isEmpty ? "failed" : "completed"
        } catch is CancellationError {
            receipt.outcome = "cancelled"
            receipt.total_ms = elapsedMS()
        } catch {
            receipt.outcome = "failed"
            receipt.total_ms = elapsedMS()
            // Avoid logging prompt/transcript content through localized errors.
            receipt.error_type = String(reflecting: type(of: error))
        }
        receipt.thermal_after = String(describing: process.thermalState)
        return receipt
    }
}
