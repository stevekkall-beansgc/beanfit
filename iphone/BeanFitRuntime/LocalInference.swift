import Foundation
import UIKit

func currentResources() -> ResourceSnapshot {
    let s = bf_resources()
    return ResourceSnapshot(footprint: s.footprint, resident: s.resident, virtualBytes: s.virtual_bytes,
                            internalBytes: s.internal_bytes, externalBytes: s.external_bytes,
                            compressed: s.compressed, available: s.available, kernelPeakResident: bf_peak_resident())
}

private final class CancellationState: @unchecked Sendable {
    private let lock = NSLock()
    private var value = false
    var cancelled: Bool { lock.lock(); defer { lock.unlock() }; return value }
    func cancel() { lock.lock(); value = true; lock.unlock() }
}

private final class FootprintSampler {
    private let queue = DispatchQueue(label: "beanfit.memory")
    private let timer: DispatchSourceTimer
    private var peak: UInt64
    private var peakResident: UInt64
    private var peakInternal: UInt64
    private var peakExternal: UInt64
    private var peakCompressed: UInt64
    private let baselineResources: ResourceSnapshot
    private var samples = 1
    let baseline: UInt64
    init() {
        baselineResources = currentResources()
        baseline = baselineResources.footprint; peak = baseline
        peakResident = baselineResources.resident; peakInternal = baselineResources.internalBytes
        peakExternal = baselineResources.externalBytes; peakCompressed = baselineResources.compressed
        timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: .milliseconds(20))
        timer.setEventHandler { [weak self] in
            guard let self = self else { return }
            self.sample(currentResources()); self.samples += 1
        }
        timer.resume()
    }
    private func sample(_ s: ResourceSnapshot) {
        peak = max(peak, s.footprint); peakResident = max(peakResident, s.resident)
        peakInternal = max(peakInternal, s.internalBytes); peakExternal = max(peakExternal, s.externalBytes)
        peakCompressed = max(peakCompressed, s.compressed)
    }
    func stop() -> (UInt64, UInt64, Int, ResourceMeasurement) {
        timer.cancel()
        return queue.sync {
            let end = currentResources(); sample(end)
            return (peak, end.footprint, samples, ResourceMeasurement(baseline: baselineResources, end: end,
                peakResident: peakResident, peakInternal: peakInternal, peakExternal: peakExternal, peakCompressed: peakCompressed))
        }
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
                             before: Int, outcome: String, first: Double? = nil, tokens: Int = 0, threads: Int? = nil) -> Measurement {
        let (peak, end, samples, resources) = timer.stop()
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
                           thermalBefore: before, thermalAfter: ProcessInfo.processInfo.thermalState.rawValue, resources: resources, cpuThreads: threads)
    }
    func load(_ model: LocalModel) async throws -> Measurement {
        let cancellation = CancellationState()
        return try await withTaskCancellationHandler(operation: {
          try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Measurement, Error>) in
            queue.async {
                let started = Date(), timer = FootprintSampler(), before = ProcessInfo.processInfo.thermalState.rawValue
                do {
                    if cancellation.cancelled { throw CancellationError() }
                    bf_unload(self.handle); self.loaded = nil
                    // Re-verify on every load, including developer-transferred files.
                    try ModelFiles.verify(ModelFiles.url(model), model: model, shouldCancel: { cancellation.cancelled })
                    if cancellation.cancelled { throw CancellationError() }
                    bf_prepare(self.handle)
                    if cancellation.cancelled { throw CancellationError() }
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
        }, onCancel: { cancellation.cancel(); self.cancel() })
    }
    func generate(system: String, user: String, grammar: String? = nil, maxTokens: Int = 128) async throws -> InferenceResult {
        let cancellation = CancellationState()
        return try await withTaskCancellationHandler(operation: {
          try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<InferenceResult, Error>) in
            queue.async {
                guard !cancellation.cancelled else { continuation.resume(throwing: CancellationError()); return }
                bf_prepare(self.handle)
                guard !cancellation.cancelled else { continuation.resume(throwing: CancellationError()); return }
                guard let model = self.loaded else { continuation.resume(throwing: RuntimeFailure.message("Load a model first")); return }
                bf_set_text_sampling(self.handle, 0)
                let started = Date(), timer = FootprintSampler(), before = ProcessInfo.processInfo.thermalState.rawValue
                // Bound sustained CPU heat on the6GB phone; do not increase on a cold start.
                let threads = 1
                bf_set_threads(self.handle, Int32(threads))
                let deadline = DispatchWorkItem { [weak self] in self?.cancel() }
                DispatchQueue.global().asyncAfter(deadline: .now()+90, execute: deadline)
                let output = bf_generate(self.handle, model.prompt(system: system, user: user), grammar ?? "", Int32(maxTokens))
                deadline.cancel()
                let metric = self.measurement(stage: "generate", model: model, started: started, timer: timer,
                                              before: before, outcome: output == nil ? "failed-or-cancelled" : "completed",
                                              first: bf_first_token_ms(self.handle) >= 0 ? bf_first_token_ms(self.handle) : nil,
                                              tokens: Int(bf_tokens(self.handle)), threads: threads)
                guard let output = output else { continuation.resume(throwing: MeasuredFailure(message: String(cString: bf_error(self.handle)), measurement: metric)); return }
                continuation.resume(returning: InferenceResult(text: String(cString: output), measurement: metric))
            }
          }
        }, onCancel: { cancellation.cancel(); self.cancel() })
    }
}
