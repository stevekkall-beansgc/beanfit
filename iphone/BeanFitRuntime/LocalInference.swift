import Foundation
import UIKit

private final class FootprintSampler {
    private let queue = DispatchQueue(label: "beanfit.memory")
    private let timer: DispatchSourceTimer
    private var peak: UInt64
    private var samples = 1
    let baseline: UInt64
    init() {
        baseline = bf_footprint(); peak = baseline
        timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: .milliseconds(20))
        timer.setEventHandler { [weak self] in
            guard let self = self else { return }
            self.peak = max(self.peak, bf_footprint()); self.samples += 1
        }
        timer.resume()
    }
    func stop() -> (UInt64, UInt64, Int) {
        timer.cancel()
        return queue.sync { let end = bf_footprint(); return (max(peak, end), end, samples) }
    }
}

/// One serial native engine per product host. No server, remote fallback or cross-app daemon.
final class EmbeddedInference: LocalInferenceClient, @unchecked Sendable {
    private let queue = DispatchQueue(label: "beanfit.inference", qos: .userInitiated)
    private let handle: UnsafeMutableRawPointer = bf_create()!
    private var loaded: LocalModel?
    deinit { bf_destroy(handle) }
    func cancel() { bf_cancel(handle) }
    func unload() async {
        cancel()
        await withCheckedContinuation { continuation in
            queue.async { bf_unload(self.handle); self.loaded = nil; continuation.resume() }
        }
    }
    private func measurement(stage: String, model: LocalModel, started: Date, timer: FootprintSampler,
                             before: Int, outcome: String, first: Double? = nil, tokens: Int = 0) -> Measurement {
        let (peak, end, samples) = timer.stop()
        #if targetEnvironment(simulator)
        let kind = "simulator"
        #else
        let kind = "physical-device-process-only"
        #endif
        var name = utsname(); uname(&name)
        let machineSize = MemoryLayout.size(ofValue: name.machine)
        let device = withUnsafePointer(to: &name.machine) { pointer in
            pointer.withMemoryRebound(to: CChar.self, capacity: machineSize) { String(cString: $0) }
        }
        return Measurement(id: UUID(), stage: stage, model: model.id, modelSHA256: model.sha256,
                           evidenceKind: kind, device: device, os: ProcessInfo.processInfo.operatingSystemVersionString,
                           contextTokens: 2048, startedAt: started, durationMs: Date().timeIntervalSince(started)*1000,
                           firstTokenMs: first, outputTokens: tokens, baselineProcessBytes: timer.baseline,
                           observedPeakProcessBytes: peak, endProcessBytes: end, memorySamples: samples, outcome: outcome,
                           thermalBefore: before, thermalAfter: ProcessInfo.processInfo.thermalState.rawValue)
    }
    func load(_ model: LocalModel) async throws -> Measurement {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                let started = Date(), timer = FootprintSampler(), before = ProcessInfo.processInfo.thermalState.rawValue
                do {
                    bf_unload(self.handle); self.loaded = nil
                    // Re-verify on every load, including developer-transferred files.
                    try ModelFiles.verify(ModelFiles.url(model), model: model)
                    let ok = bf_load(self.handle, ModelFiles.url(model).path)
                    guard ok == 1 else { self.loaded = nil; throw RuntimeFailure.message(String(cString: bf_error(self.handle))) }
                    self.loaded = model
                    continuation.resume(returning: self.measurement(stage: "verify-and-load", model: model, started: started,
                                                                   timer: timer, before: before, outcome: "completed"))
                } catch {
                    let metric = self.measurement(stage: "verify-and-load", model: model, started: started,
                                                  timer: timer, before: before, outcome: "failed-or-cancelled")
                    continuation.resume(throwing: MeasuredFailure(message: error.localizedDescription, measurement: metric))
                }
            }
        }
    }
    func generate(system: String, user: String, grammar: String? = nil, maxTokens: Int = 128) async throws -> InferenceResult {
        try await withCheckedThrowingContinuation { continuation in
            queue.async {
                guard let model = self.loaded else { continuation.resume(throwing: RuntimeFailure.message("Load a model first")); return }
                let started = Date(), timer = FootprintSampler(), before = ProcessInfo.processInfo.thermalState.rawValue
                let deadline = DispatchWorkItem { [weak self] in self?.cancel() }
                DispatchQueue.global().asyncAfter(deadline: .now()+90, execute: deadline)
                let output = bf_generate(self.handle, model.prompt(system: system, user: user), grammar ?? "", Int32(maxTokens))
                deadline.cancel()
                let metric = self.measurement(stage: "generate", model: model, started: started, timer: timer,
                                              before: before, outcome: output == nil ? "failed-or-cancelled" : "completed",
                                              first: bf_first_token_ms(self.handle) >= 0 ? bf_first_token_ms(self.handle) : nil,
                                              tokens: Int(bf_tokens(self.handle)))
                guard let output = output else { continuation.resume(throwing: MeasuredFailure(message: String(cString: bf_error(self.handle)), measurement: metric)); return }
                continuation.resume(returning: InferenceResult(text: String(cString: output), measurement: metric))
            }
        }
    }
}
