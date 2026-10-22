import SwiftUI
import UIKit
import UniformTypeIdentifiers

@MainActor final class TextDraftModel: ObservableObject {
    @Published var task = TextDraftTask.summarize { didSet { if oldValue != task { retireDraft() } } }
    @Published var input = "The community picnic is on Tuesday. Bring a red blanket."
        { didSet { if oldValue != input { retireDraft() } } }
    @Published private(set) var output = ""
    @Published private(set) var status = "Import the model once, then load it to write on this iPhone."
    @Published private(set) var loaded = false
    @Published private(set) var busy = false
    let model = LocalModel.catalog.first { $0.id == "liquid12" }!
    private let runtime = EmbeddedInference()
    private var work: Task<Void, Never>?
    private var revision = 0
    private var measurements: [Measurement] = []
    private var warnings = 0
    var syntheticTest: Bool { ProcessInfo.processInfo.arguments.contains("--text-smoke") }
    var canGenerate: Bool { loaded && !busy && (try? TextDraftRequest(task: task, text: input)) != nil }
    func retireDraft() {
        output = ""; revision += 1
        if busy { stop() }
    }
    func stop() {
        revision += 1; let fence = revision
        work?.cancel(); runtime.cancel(); output = ""; busy = true
        work = Task {
            await runtime.unload()
            guard revision == fence else { return }
            loaded = false; busy = false; work = nil; status = "Stopped. Model memory released."
        }
    }
    func memoryWarning() { warnings += 1; stop() }
    private func perform(_ message: String, operation: @escaping () async throws -> Void) {
        guard !busy else { return }
        busy = true; status = message; revision += 1; let fence = revision
        work = Task {
            defer { if revision == fence { busy = false; work = nil } }
            do {
                try await operation(); try Task.checkCancellation()
                if revision == fence { status = "Ready. Review the draft before using it." }
            } catch {
                if revision == fence {
                    if let failure = error as? MeasuredFailure { measurements.append(failure.measurement) }
                    status = error.localizedDescription
                }
            }
        }
    }
    func load() {
        let thermal = ProcessInfo.processInfo.thermalState
        guard thermal != .serious && thermal != .critical else { status = "Let the iPhone cool before loading."; return }
        perform("Checking and loading the local model…") {
            self.loaded = false
            self.measurements.append(try await self.runtime.load(self.model))
            try Task.checkCancellation(); self.loaded = true
        }
    }
    func importModel(_ url: URL) {
        perform("Importing and verifying the model…") {
            await self.runtime.unload(); self.loaded = false
            let model = self.model
            try await Task.detached { try ModelFiles.importFile(url, model: model) }.value
        }
    }
    func generate() {
        guard canGenerate else { return }
        let task = task, input = input
        output = ""
        perform("Writing on this iPhone…") {
            let request = try TextDraftRequest(task: task, text: input)
            let result = try await TextDraftAdapter(runtime: self.runtime).draft(request)
            try Task.checkCancellation()
            guard self.input == input, self.task == task else { return }
            self.measurements.append(result.measurement); self.output = result.text
        }
    }
    func copyReviewedDraft() {
        guard !busy, !output.isEmpty else { return }
        UIPasteboard.general.string = output
        status = "Draft copied. Nothing was sent or saved by the model."
    }
    func smoke() async {
        guard syntheticTest else { return }
        let priorIdleSetting = UIApplication.shared.isIdleTimerDisabled
        UIApplication.shared.isIdleTimerDisabled = true
        defer { UIApplication.shared.isIdleTimerDisabled = priorIdleSetting }
        let started = Date(); var records: [[String: Any]] = []
        let runID = ProcessInfo.processInfo.arguments.first { $0.hasPrefix("--run-id=") }.map { String($0.dropFirst(9)) } ?? UUID().uuidString
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        func checkpoint(_ complete: Bool, error: String? = nil) {
            #if targetEnvironment(simulator)
            let evidence = "simulator"
            #else
            let evidence = "physical-device-process-only"
            #endif
            var report: [String: Any] = ["schema":"beanfit.text.integration.v1", "run_id":runID,
                "bundle":Bundle.main.bundleIdentifier ?? "unknown", "model":model.id, "model_sha256":model.sha256,
                "runtime_revision":ModelSuggestions.catalog.runtime_revision, "evidence_kind":evidence,
                "completed":complete, "qualified":false, "started_at":ISO8601DateFormatter().string(from: started),
                "application_state":UIApplication.shared.applicationState.rawValue,
                "records":records, "memory_warnings":warnings, "model_unloaded":!loaded,
                "limits":["Synthetic lexical functional checks, not broad writing-quality acceptance.", "Process footprint is sampled and excludes whole-stack allocations; no memory-fit claim."]]
            if let error { report["error"] = error }
            try? JSONSerialization.data(withJSONObject: report, options: [.prettyPrinted,.sortedKeys]).write(to: documents.appendingPathComponent("text-smoke.json"), options: .atomic)
            let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601; encoder.outputFormatting = [.prettyPrinted,.sortedKeys]
            try? encoder.encode(measurements).write(to: documents.appendingPathComponent("text-measurements.json"), options: .atomic)
        }
        checkpoint(false)
        do {
            // Exercise the same actions and state transitions as the visible buttons.
            load(); await work?.value
            guard loaded, !busy else { throw RuntimeFailure.message(status) }
            for repeatIndex in 0..<2 {
                for probe in TextDraftProbe.cases {
                    try Task.checkCancellation()
                    task = probe.task; input = probe.input
                    generate(); await work?.value
                    guard !busy, !output.isEmpty, let measurement = measurements.last, measurement.stage == "generate" else {
                        throw RuntimeFailure.message(status)
                    }
                    records.append(["id":probe.id,"repeat":repeatIndex,"input":probe.input,"output":output,
                                    "passed":probe.passes(output),"duration_ms":measurement.durationMs])
                    checkpoint(false)
                }
            }
            let lastDraft = output
            task = .rewrite
            input = String(repeating: "The garden has red flowers and a green gate. ", count: 40)
            generate()
            try await Task.sleep(nanoseconds: 100_000_000)
            let wasWriting = busy
            stop(); await work?.value
            records.append(["id":"stop-request","passed":wasWriting && !busy && !loaded && output.isEmpty])
            // Restore only synthetic display data after verifying Stop retired the draft.
            task = .reply; input = TextDraftProbe.cases.last!.input; output = lastDraft
            status = "Text checks finished. Model memory released."
            busy = false
            await Task.yield()
            // Synthetic test UI only. Never capture the surrounding product or personal data.
            if let window = UIApplication.shared.connectedScenes.compactMap({ $0 as? UIWindowScene }).flatMap(\.windows).first(where: \.isKeyWindow) {
                try? UIGraphicsImageRenderer(bounds: window.bounds).image { _ in window.drawHierarchy(in: window.bounds, afterScreenUpdates: true) }.pngData()?.write(to: documents.appendingPathComponent("text-smoke.png"), options: .atomic)
            }
            checkpoint(true)
        } catch {
            if let failure = error as? MeasuredFailure { measurements.append(failure.measurement) }
            await runtime.unload(); loaded = false; busy = false
            status = error.localizedDescription; checkpoint(false, error: error.localizedDescription)
        }
    }
}

struct LocalTextDraftView: View {
    @StateObject private var model = TextDraftModel()
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) private var dismiss
    @State private var importer = false
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Summarize, rewrite, or draft a reply on this iPhone.")
                    Text("AI runs on this device. Text is not sent to an AI service. Review every draft; details can be wrong.").font(.caption)
                }
                Section("Your text") {
                    Picker("Help with", selection: model.syntheticTest ? .constant(model.task) : $model.task) { ForEach(TextDraftTask.allCases) { Text($0.title).tag($0) } }.disabled(model.busy)
                    TextEditor(text: model.syntheticTest ? .constant(model.input) : $model.input).frame(minHeight: 130).disabled(model.busy).accessibilityIdentifier("textDraftInput")
                    Button("Write draft") { model.generate() }.disabled(!model.canGenerate).accessibilityIdentifier("writeTextDraft")
                }
                Section("Draft to review") {
                    if model.output.isEmpty { Text("Your draft will appear here.").foregroundStyle(.secondary) }
                    else {
                        Text(model.output).textSelection(.enabled).accessibilityIdentifier("textDraftOutput")
                        Button("Copy reviewed draft") { model.copyReviewedDraft() }.disabled(model.busy)
                    }
                }
                Section("On-device model") {
                    Text("LFM2.5 1.2B · 731 MB download").font(.caption)
                    Text(model.status).accessibilityIdentifier("textDraftStatus")
                    if model.busy { ProgressView() }
                    Button("Import model from Files") { importer = true }.disabled(model.busy)
                    Button("Load model") { model.load() }.disabled(model.busy || model.loaded)
                    Button(model.busy ? "Stop" : "Unload model") { model.stop() }.disabled(!model.busy && !model.loaded)
                    Text("Short passages only. No chat history, automatic sending or remote AI. Complete memory fit is still being tested.").font(.caption)
                }
            }.navigationTitle("Write with local AI")
                .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Done") { model.stop(); dismiss() } } }
        }
        .fileImporter(isPresented: $importer, allowedContentTypes: [.data], allowsMultipleSelection: false) { result in
            if case .success(let urls) = result, let url = urls.first { model.importModel(url) }
        }
        .task { await model.smoke() }
        .onDisappear { model.stop() }
        .onChange(of: scenePhase) { _, phase in if phase == .background { model.stop() } }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.didReceiveMemoryWarningNotification)) { _ in model.memoryWarning() }
    }
}
