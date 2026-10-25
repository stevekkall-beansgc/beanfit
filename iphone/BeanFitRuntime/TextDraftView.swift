import SwiftUI
import UIKit
import UniformTypeIdentifiers
import CryptoKit

@MainActor final class TextDraftModel: ObservableObject {
    @Published var task = TextDraftTask.summarize { didSet { if oldValue != task { retireDraft() } } }
    @Published var input = "The community picnic is on Tuesday. Bring a red blanket."
        { didSet { if oldValue != input { retireDraft() } } }
    @Published var replyFacts = "" { didSet { if oldValue != replyFacts { retireDraft() } } }
    @Published private(set) var output = ""
    @Published private(set) var draftNote = ""
    @Published private(set) var status = "Import the model once, then load it to write on this iPhone."
    @Published private(set) var loaded = false
    @Published private(set) var busy = false
    let model = LocalModel.catalog.first { $0.id == "qwen2" }!
    private let runtime = EmbeddedInference()
    private var work: Task<Void, Never>?
    private var revision = 0
    private var measurements: [Measurement] = []
    private var warnings = 0
    private var thermalObservation = TextThermalObservation(initial: ProcessInfo.processInfo.thermalState.rawValue)
    private var injectedWarnings = 0
    private var idle: Task<Void, Never>?
    private var lastDraftAt = Date.distantPast
    private var uiEvents: [[String: Any]] = []
    private var completedDrafts = 0
    private var lastDraftDurationMs: Double = 0
    private var lastDraftUsedModel = false
    private var lastRawModelText: String?
    private var lastRemovedAnnotations = 0
    private var lastNormalizedCausalLinks = 0
    private var lastPreservedDraftStatus = false
    @Published private var backgrounded = false
    private var flowEvents: [[String:Any]] = []
    var syntheticTest: Bool { ProcessInfo.processInfo.arguments.contains("--text-smoke") || ProcessInfo.processInfo.arguments.contains("--text-qualify") }
    private func trace(_ event: String) {
        guard syntheticTest else { return }
        flowEvents.append(["event":event,"seconds":ProcessInfo.processInfo.systemUptime,
                           "revision":revision,"busy":busy,"loaded":loaded,"task":task.rawValue])
    }
    var canGenerate: Bool { !backgrounded && (loaded || task == .reply) && !busy && (try? TextDraftRequest(task: task, text: input, replyFacts: replyFacts)) != nil }
    func becameActive() { backgrounded = false }
    func enteredBackground() {
        guard !backgrounded else { return }
        backgrounded = true
        stop(message:"Paused in background. Model memory released.")
    }
    func chooseTask(_ value: TextDraftTask) {
        task = value
        if value == .reply { stop(message:"Reply drafts use your facts. No model is needed.") }
    }
    func retireDraft() {
        trace("input-or-task-edited")
        output = ""; draftNote = ""; lastRawModelText = nil; revision += 1
        if busy { stop() }
    }
    func stop(message: String = "Stopped. Model memory released.") {
        trace("stop: " + message)
        let started = ProcessInfo.processInfo.systemUptime
        revision += 1; let fence = revision
        idle?.cancel(); idle = nil; work?.cancel(); runtime.cancel(); output = ""; draftNote = ""; lastRawModelText = nil; busy = true
        status = message
        work = Task {
            await runtime.unload()
            guard revision == fence else { return }
            loaded = false; busy = false; work = nil; status = message
            if ProcessInfo.processInfo.arguments.contains("--text-ui-test") {
                uiEvents.append(["reason":message,"duration_ms":(ProcessInfo.processInfo.systemUptime-started)*1000,
                                 "model_unloaded":true,"resident_bytes":currentResources().resident,
                                 "app_version":Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "unknown",
                                 "app_build":Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "unknown"])
                let url = FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("text-ui-lifecycle.json")
                try? JSONSerialization.data(withJSONObject:uiEvents,options:[.prettyPrinted,.sortedKeys]).write(to:url,options:.atomic)
            }
        }
    }
    func memoryWarning(injected: Bool = false) {
        if injected && syntheticTest { injectedWarnings += 1 } else { warnings += 1 }
        stop()
    }
    func thermalChanged(injected: Int? = nil) {
        let state = syntheticTest ? (injected ?? ProcessInfo.processInfo.thermalState.rawValue) : ProcessInfo.processInfo.thermalState.rawValue
        thermalObservation.observe(state, injected: syntheticTest && injected != nil)
        if state >= 2 { stop(message: "Let the iPhone cool. Model memory released.") }
    }
    private func releaseWhenIdle() {
        idle?.cancel()
        guard loaded else { return }
        idle = Task {
            do { try await Task.sleep(nanoseconds: 30_000_000_000) } catch { return }
            guard !busy else { return }
            stop(message: "Model released after 30 seconds idle. Load it again when needed.")
        }
    }
    private func waitForCooldown() async throws {
        let remaining = 15.05 - Date().timeIntervalSince(lastDraftAt)
        if remaining > 0 { try await Task.sleep(nanoseconds: UInt64(remaining * 1_000_000_000)) }
    }
    private func perform(_ message: String, operation: @escaping () async throws -> Void) {
        guard !busy else { return }
        idle?.cancel(); busy = true; status = message; revision += 1; let fence = revision
        trace("operation-start: " + message)
        work = Task {
            defer { if revision == fence { busy = false; work = nil; releaseWhenIdle() } }
            do {
                try await operation(); try Task.checkCancellation(); trace("operation-completed")
                if revision == fence { status = "Ready. Review the draft before using it." }
            } catch {
                trace("operation-error: " + error.localizedDescription)
                if revision == fence {
                    if let failure = error as? MeasuredFailure { measurements.append(failure.measurement) }
                    status = error.localizedDescription
                }
            }
        }
    }
    func load() {
        guard !backgrounded else { status = "Paused in background. Model memory released."; return }
        let thermal = ProcessInfo.processInfo.thermalState
        guard thermal != .serious && thermal != .critical else { status = "Let the iPhone cool before loading."; return }
        #if targetEnvironment(simulator)
        // The simulator does not provide iOS process-memory headroom. Explicit
        // synthetic runs exercise flow only and remain labelled unqualified.
        let simulatorFlowTest = syntheticTest || ProcessInfo.processInfo.arguments.contains("--text-ui-test")
        #else
        let simulatorFlowTest = false
        #endif
        guard simulatorFlowTest || TextResourcePolicy.permits(thermal: thermal.rawValue, available: currentResources().available, modelBytes: model.bytes) else {
            status = "Not enough memory headroom for this model. Try again later."; return
        }
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
        guard canGenerate else { trace("draft-skipped-not-ready"); return }
        if task != .reply {
            if ProcessInfo.processInfo.thermalState.rawValue >= 2 { thermalChanged(); return }
            guard Date().timeIntervalSince(lastDraftAt) >= 15 else { status = "Let the iPhone rest briefly between drafts."; return }
        }
        let task = task, input = input, facts = replyFacts
        trace("draft-requested")
        output = ""
        let started = Date()
        if task != .reply { lastDraftAt = started }
        perform("Writing on this iPhone…") {
            if task == .reply { await self.runtime.unload(); self.loaded = false }
            let request = try TextDraftRequest(task: task, text: input, replyFacts: facts)
            let result = try await TextDraftAdapter(runtime: self.runtime).draft(request)
            try Task.checkCancellation()
            guard self.input == input, self.task == task, self.replyFacts == facts else { return }
            if let measurement = result.measurement { self.measurements.append(measurement) }
            self.output = result.text; self.completedDrafts += 1
            self.lastRawModelText = result.rawModelText; self.lastRemovedAnnotations = result.removedAnnotations
            self.lastNormalizedCausalLinks = result.normalizedCausalLinks
            self.lastPreservedDraftStatus = result.preservedDraftStatus
            self.draftNote = result.preservedDraftStatus ? "Kept the original draft status. Review before copying." :
                (result.removedAnnotations + result.normalizedCausalLinks > 0 ? "Cleaned up drafting notes or added linking words. Compare with the original before copying." : "")
            self.lastDraftDurationMs = Date().timeIntervalSince(started)*1000; self.lastDraftUsedModel = result.usedModel
        }
    }
    private func setFixture(task: TextDraftTask, text: String) {
        self.task = task
        // Unpack the frozen synthetic fixture only. Ordinary requests receive a
        // separate typed facts field and never parse authority from a message.
        if task == .reply, let marker = text.range(of:"Reply facts:") {
            input = String(text[..<marker.lowerBound]); replyFacts = String(text[marker.upperBound...])
        } else { input = text; replyFacts = "" }
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
                "bundle":Bundle.main.bundleIdentifier ?? "unknown",
                "app_version":Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "unknown",
                "app_build":Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "unknown", "model":model.id, "model_sha256":model.sha256,
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
                    if probe.task != .reply { try await waitForCooldown() }
                    setFixture(task:probe.task,text:probe.input)
                    if probe.task != .reply && !loaded { load(); await work?.value }
                    let priorCount = completedDrafts
                    generate(); await work?.value
                    guard !busy, !output.isEmpty, completedDrafts > priorCount else {
                        throw RuntimeFailure.message(status)
                    }
                    records.append(["id":probe.id,"repeat":repeatIndex,"input":probe.input,"output":output,
                                    "passed":probe.passes(output),"duration_ms":lastDraftDurationMs,"used_model":lastDraftUsedModel])
                    checkpoint(false)
                }
            }
            let lastDraft = output
            try await waitForCooldown()
            task = .rewrite
            input = String(repeating: "The garden has red flowers and a green gate. ", count: 40)
            if !loaded { load(); await work?.value }
            generate()
            try await Task.sleep(nanoseconds: 100_000_000)
            let wasWriting = busy
            stop(); await work?.value
            records.append(["id":"stop-request","passed":wasWriting && !busy && !loaded && output.isEmpty])
            // Restore only synthetic display data after verifying Stop retired the draft.
            setFixture(task:.reply,text:TextDraftProbe.cases.last!.input); output = lastDraft
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

private struct QualityPacket: Decodable { let schema: String; let cases: [QualityCase] }
private struct QualityCase: Decodable {
    let id: String, task: TextDraftTask, text: String, expectation: String
    let required: [String], forbidden: [String]
    func screens(_ output: String) -> Bool {
        required.allSatisfy { output.range(of: $0, options: [.regularExpression, .caseInsensitive]) != nil }
        && forbidden.allSatisfy { output.range(of: $0, options: [.regularExpression, .caseInsensitive]) == nil }
    }
}

extension TextDraftModel {
    // Explicit developer-only packet. It exports synthetic data, never ordinary drafts.
    func qualify() async {
        let args = ProcessInfo.processInfo.arguments
        guard args.contains("--text-qualify") else { return }
        let phase = args.first { $0.hasPrefix("--phase=") }.map { String($0.dropFirst(8)) } ?? "quality"
        let runID = args.first { $0.hasPrefix("--run-id=") }.map { String($0.dropFirst(9)) } ?? UUID().uuidString
        let documents = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let priorIdle = UIApplication.shared.isIdleTimerDisabled
        UIApplication.shared.isIdleTimerDisabled = true
        defer { UIApplication.shared.isIdleTimerDisabled = priorIdle }
        let started = ProcessInfo.processInfo.systemUptime
        var records: [[String: Any]] = [], thermal: [[String: Any]] = []
        var packetHash = "", completed = false, failure: String?
        thermalObservation = TextThermalObservation(initial: ProcessInfo.processInfo.thermalState.rawValue)
        let sampler = Task {
            while !Task.isCancelled {
                let state = ProcessInfo.processInfo.thermalState.rawValue
                thermalObservation.observe(state)
                thermal.append(["seconds":ProcessInfo.processInfo.systemUptime-started,"state":state])
                do { try await Task.sleep(nanoseconds: 1_000_000_000) } catch { break }
            }
        }
        let encoder = JSONEncoder(); encoder.dateEncodingStrategy = .iso8601
        func encoded<T: Encodable>(_ value: T) -> Any { (try? JSONSerialization.jsonObject(with: encoder.encode(value))) ?? NSNull() }
        func save() {
            let cap: UInt64 = 1536 * 1_048_576
            let kernelPeak = measurements.compactMap { $0.resources?.end.kernelPeakResident }.max() ?? 0
            let peakResident = max(measurements.compactMap { $0.resources?.peakResident }.max() ?? 0,kernelPeak)
            let conservativePeak = (measurements.map(\.observedPeakProcessBytes).max() ?? 0) + UInt64(model.bytes)
            thermalObservation.observe(ProcessInfo.processInfo.thermalState.rawValue)
            let thermalOK = thermalObservation.permitsAcceptance && !thermal.contains { ($0["state"] as? Int ?? 3) >= 2 }
            let screensOK = !records.isEmpty && records.allSatisfy { $0["passed"] as? Bool == true }
            var report: [String:Any] = ["schema":"beanfit.text.qualification.v1","run_id":runID,"phase":phase,
                "bundle":Bundle.main.bundleIdentifier ?? "unknown",
                "app_version":Bundle.main.object(forInfoDictionaryKey:"CFBundleShortVersionString") as? String ?? "unknown",
                "app_build":Bundle.main.object(forInfoDictionaryKey:"CFBundleVersion") as? String ?? "unknown","model":model.id,"model_sha256":model.sha256,
                "runtime_revision":ModelSuggestions.catalog.runtime_revision,"packet_sha256":packetHash,
                "completed":completed,"qualified":false,"records":records,"measurements":encoded(measurements),"flow_events":flowEvents,
                "thermal_samples":thermal,"real_memory_warnings":warnings,"injected_warning_handler_calls":injectedWarnings,
                "model_unloaded":!loaded,"peak_resident_bytes":peakResident,"conservative_peak_bytes":conservativePeak,
                "kernel_peak_resident_bytes":kernelPeak,"target_start_cadence_seconds":15,
                "resource_budget_bytes":cap,"thermal_gate":thermalOK,"highest_real_thermal_state":thermalObservation.highestState,"elapsed_seconds":ProcessInfo.processInfo.systemUptime-started,
                "automatic_pass":completed && screensOK && warnings == 0 && thermalOK && kernelPeak > 0 && peakResident < cap && conservativePeak < cap,
                "limits":["Synthetic packet; authored factual/style review required.","Whole app process RSS includes resident mappings. Unrelated OS memory is not measured as zero.","Injected handlers are not real OS pressure or sensor events.","No all-iPhone or battery-endurance qualification."]]
            #if targetEnvironment(simulator)
            report["evidence_kind"] = "simulator"
            #else
            report["evidence_kind"] = "physical-device-resident-and-footprint"
            #endif
            if let failure { report["error"] = failure }
            try? JSONSerialization.data(withJSONObject: report, options: [.sortedKeys,.prettyPrinted]).write(to: documents.appendingPathComponent("text-qualification.json"), options: .atomic)
        }
        func ensureLoaded() async throws {
            if !loaded { load(); await work?.value }
            guard loaded, !busy else { throw RuntimeFailure.message(status) }
        }
        func draft(_ item: QualityCase) async throws {
            if item.task != .reply { try await waitForCooldown(); try await ensureLoaded() }
            setFixture(task:item.task,text:item.text)
            let before = completedDrafts
            generate(); await work?.value
            guard !busy, !output.isEmpty, completedDrafts > before else { throw RuntimeFailure.message(status) }
            var record: [String:Any] = ["id":item.id,"task":item.task.rawValue,"input":item.text,"expectation":item.expectation,
                "output":output,"passed":item.screens(output),"duration_ms":lastDraftDurationMs,"used_model":lastDraftUsedModel,
                "removed_annotations":lastRemovedAnnotations,"normalized_causal_links":lastNormalizedCausalLinks,
                "preserved_draft_status":lastPreservedDraftStatus]
            if let raw = lastRawModelText { record["raw_model_output"] = raw; record["raw_model_phrase_pass"] = item.screens(raw) }
            records.append(record)
            save()
        }
        save()
        do {
            let data = try Data(contentsOf: documents.appendingPathComponent("text-quality-packet.json"))
            packetHash = SHA256.hash(data: data).map { String(format:"%02x", $0) }.joined()
            guard packetHash == "47f1797303c82d58180f913e697d30c590a69097afed98141d164862bd0d70c5" else { throw RuntimeFailure.message("Frozen packet does not match") }
            let packet = try JSONDecoder().decode(QualityPacket.self, from: data)
            guard packet.schema == "beanfit.text.acceptance.v1", packet.cases.count == 36 else { throw RuntimeFailure.message("Invalid frozen packet") }
            if phase == "quality" {
                for item in packet.cases { try await draft(item) }
            } else if phase == "thermal" {
                for index in 0..<20 {
                    let tick = ProcessInfo.processInfo.systemUptime
                    try await draft(packet.cases[12 + index % 3])
                    let remainder = 15 - (ProcessInfo.processInfo.systemUptime-tick)
                    if remainder > 0 { try await Task.sleep(nanoseconds: UInt64(remainder*1_000_000_000)) }
                }
            } else if phase == "resource" {
                var unloaded: [UInt64] = []
                for index in 0..<5 {
                    try await draft(packet.cases[12])
                    stop(); await work?.value
                    try await Task.sleep(nanoseconds: 1_000_000_000)
                    let snapshot = currentResources(); unloaded.append(snapshot.resident)
                    records.append(["id":"unload-cycle-\(index)","passed":!loaded && !busy && output.isEmpty,"snapshot":encoded(snapshot)])
                }
                let growth = (unloaded.max() ?? 0) - min(unloaded.first ?? 0, unloaded.max() ?? 0)
                records.append(["id":"unloaded-growth","passed":growth <= 64*1_048_576,"bytes":growth])
                try await draft(packet.cases[12]); input += " Edited."
                records.append(["id":"edit-retires-draft","passed":output.isEmpty])
                memoryWarning(injected:true); await work?.value
                records.append(["id":"injected-warning-handler","passed":!loaded && !busy && output.isEmpty])
                try await ensureLoaded(); thermalChanged(injected:2); await work?.value
                records.append(["id":"injected-hot-state-handler","passed":!loaded && !busy && output.isEmpty])
                try await ensureLoaded(); try await Task.sleep(nanoseconds: 31_000_000_000)
                await work?.value
                records.append(["id":"idle-unload","passed":!loaded && !busy && output.isEmpty])
                try await ensureLoaded(); input = "A valid short passage."
                records.append(["id":"valid-input-enabled","passed":canGenerate])
                input = ""; records.append(["id":"blank-blocked","passed":!canGenerate])
                input = String(repeating:"x", count:2401); records.append(["id":"oversize-blocked","passed":!canGenerate])
                try await ensureLoaded(); try await waitForCooldown()
                input = String(repeating:"There are red flowers in the garden. ",count:40)
                generate(); try await Task.sleep(nanoseconds:100_000_000)
                let writing = busy, stopped = ProcessInfo.processInfo.systemUptime
                stop(); await work?.value
                let duration = ProcessInfo.processInfo.systemUptime-stopped
                records.append(["id":"stop-unload","passed":writing && !loaded && !busy && output.isEmpty && duration <= 2,"duration_seconds":duration])
            } else { throw RuntimeFailure.message("Unknown qualification phase") }
            completed = true
        } catch { failure = error.localizedDescription }
        sampler.cancel(); await sampler.value
        stop(); await work?.value
        status = failure ?? "Qualification packet finished. Model released."
        save()
    }
}

struct LocalTextDraftView: View {
    @StateObject private var model = TextDraftModel()
    @Environment(\.scenePhase) private var scenePhase
    @Environment(\.dismiss) private var dismiss
    @State private var importer = false
    private enum Editor: Hashable { case source, facts }
    @FocusState private var focusedEditor: Editor?
    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Summarize and rewrite with on-device AI. Reply drafts arrange your own facts locally.")
                    Text("AI runs on this device. Text is not sent to an AI service. Review every draft; details can be wrong.").font(.caption)
                    if !model.loaded && model.task != .reply { Button("Load model") { model.load() }.disabled(model.busy).accessibilityIdentifier("loadTextModel") }
                    Text(model.status).font(.caption)
                }
                Section("Your text") {
                    Picker("Help with", selection: model.syntheticTest ? .constant(model.task) : Binding(get:{model.task},set:{model.chooseTask($0)})) { ForEach(TextDraftTask.allCases) { Text($0.title).tag($0) } }.disabled(model.busy)
                    TextEditor(text: model.syntheticTest ? .constant(model.input) : $model.input).frame(minHeight: 130).disabled(model.busy).focused($focusedEditor,equals:.source).accessibilityIdentifier("textDraftInput")
                    if model.task == .reply {
                        Text("Your facts for the reply").font(.caption)
                        TextEditor(text:model.syntheticTest ? .constant(model.replyFacts) : $model.replyFacts).frame(minHeight:80).disabled(model.busy).focused($focusedEditor,equals:.facts).accessibilityIdentifier("textReplyFacts")
                        Text("Use complete facts in your own voice. Add questions directly, or use Ask about, Ask if, Ask how, or Ask for. No model is needed.").font(.caption)
                    }
                    Button("Write draft") { focusedEditor = nil; model.generate() }.disabled(!model.canGenerate).accessibilityIdentifier("writeTextDraft")
                }
                Section("Draft to review") {
                    if model.output.isEmpty { Text("Your draft will appear here.").foregroundStyle(.secondary) }
                    else {
                        Text(model.output).textSelection(.enabled).accessibilityIdentifier("textDraftOutput")
                        if !model.draftNote.isEmpty { Text(model.draftNote).font(.caption) }
                        Button("Copy reviewed draft") { model.copyReviewedDraft() }.disabled(model.busy)
                    }
                }
                Section("On-device model") {
                    Text(model.task == .reply ? "Reply drafts use a local formatter, without a model." : model.model.title).font(.caption)
                    Text(model.status).accessibilityIdentifier("textDraftStatus")
                    if model.busy { ProgressView() }
                    if model.task != .reply {
                        Button("Import model from Files") { importer = true }.disabled(model.busy)
                    }
                    Button(model.busy ? "Stop" : "Unload model") { model.stop() }.disabled(!model.busy && !model.loaded)
                    Text("Short English passages. Leave 15 seconds between drafts. The model releases after 30 seconds idle. Review every draft; details can be wrong.").font(.caption)
                }
            }.scrollDismissesKeyboard(.interactively).navigationTitle("Write with local AI")
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) { Button("Done") { focusedEditor = nil; model.stop(); dismiss() } }
                    ToolbarItemGroup(placement:.keyboard) { Spacer(); Button("Done typing") { focusedEditor = nil }.accessibilityIdentifier("finishTextEditing") }
                }
        }
        .fileImporter(isPresented: $importer, allowedContentTypes: [.data], allowsMultipleSelection: false) { result in
            if case .success(let urls) = result, let url = urls.first { model.importModel(url) }
        }
        .task {
            if ProcessInfo.processInfo.arguments.contains("--text-qualify") { await model.qualify() }
            else { await model.smoke() }
        }
        .onDisappear { model.stop() }
        .onChange(of: scenePhase) { _, phase in
            if phase != .active { focusedEditor = nil }
            if phase == .active { model.becameActive() }
            if phase == .background { model.enteredBackground() }
        }
        // UIKit-hosted SwiftUI views do not inherit an App scenePhase. Observe
        // the containing application's lifecycle as well; handlers are idempotent.
        .onReceive(NotificationCenter.default.publisher(for:UIApplication.willResignActiveNotification)) { _ in focusedEditor = nil }
        .onReceive(NotificationCenter.default.publisher(for:UIApplication.didEnterBackgroundNotification)) { _ in model.enteredBackground() }
        .onReceive(NotificationCenter.default.publisher(for:UIApplication.didBecomeActiveNotification)) { _ in model.becameActive() }
        .onReceive(NotificationCenter.default.publisher(for: UIApplication.didReceiveMemoryWarningNotification)) { _ in model.memoryWarning() }
        .onReceive(NotificationCenter.default.publisher(for: ProcessInfo.thermalStateDidChangeNotification)) { _ in model.thermalChanged() }
    }
}
